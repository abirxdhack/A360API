#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, AuthKeyPermEmptyError, SessionPasswordNeededError, PersistentTimestampEmptyError
from telethon import functions, types
from uuid import uuid4
from typing import Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from config import TELE_ID, TELE_HASH
from utils import LOGGER

router = APIRouter(prefix="/tgusers")

class BotInfoModel(BaseModel):
    first_name: str
    id: int
    username: Optional[str] = None

class ChatModel(BaseModel):
    id: int
    members_count: Optional[int] = None
    title: str
    type: str
    username: Optional[str] = None

class UserModel(BaseModel):
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    is_premium: bool = False

class BotDataResponse(BaseModel):
    bot_info: BotInfoModel
    chats: List[ChatModel]
    users: List[UserModel]
    total_chats: int = Field(..., description="Total number of chats")
    total_users: int = Field(..., description="Total number of users")
    processing_time: float = Field(..., description="Processing time in seconds")

class ClientManager:
    def __init__(self):
        self.clients: Dict[str, TelegramClient] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.global_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2)

    async def get_client(self, bot_token: str) -> TelegramClient:
        async with self.global_lock:
            if bot_token not in self.locks:
                self.locks[bot_token] = asyncio.Lock()

        async with self.locks[bot_token]:
            if bot_token in self.clients:
                client = self.clients[bot_token]
                try:
                    if client.is_connected():
                        return client
                    else:
                        await client.disconnect()
                        del self.clients[bot_token]
                except Exception as e:
                    LOGGER.warning(f"Client connection issue: {e}")

            if bot_token in self.clients:
                del self.clients[bot_token]

            session_name = f"bot_{uuid4().hex[:8]}"
            client = TelegramClient(
                session=session_name,
                api_id=TELE_ID,
                api_hash=TELE_HASH
            )

            try:
                await asyncio.wait_for(client.start(bot_token=bot_token), timeout=30.0)
                async with self.global_lock:
                    self.clients[bot_token] = client
                LOGGER.info(f"Telethon client created successfully for token: {bot_token[:10]}...")
                return client
            except Exception as e:
                LOGGER.error(f"Failed to create telethon client: {e}")
                try:
                    await client.disconnect()
                except:
                    pass
                raise HTTPException(status_code=400, detail=f"Failed to connect to Telegram: {str(e)}")

    async def cleanup_client(self, bot_token: str):
        try:
            async with self.global_lock:
                if bot_token in self.clients:
                    client = self.clients[bot_token]
                    try:
                        if client.is_connected():
                            await asyncio.wait_for(client.disconnect(), timeout=10.0)
                    except Exception as e:
                        LOGGER.warning(f"Error stopping client: {e}")
                    finally:
                        del self.clients[bot_token]
                if bot_token in self.locks:
                    del self.locks[bot_token]
                LOGGER.info(f"Telethon client cleaned up for token: {bot_token[:10]}...")
        except Exception as e:
            LOGGER.error(f"Error cleaning up client {bot_token[:10]}...: {e}")

    async def shutdown(self):
        LOGGER.info("Shutting down telethon client manager...")
        try:
            async with self.global_lock:
                for bot_token in list(self.clients.keys()):
                    await self.cleanup_client(bot_token)
                self.executor.shutdown(wait=True)
            LOGGER.info("Telethon client manager shutdown complete")
        except Exception as e:
            LOGGER.error(f"Error during shutdown: {e}")

client_manager = ClientManager()

def normalize_chat_type(raw_type: str) -> str:
    type_map = {
        "chat": "group",
        "channel": "channel",
        "chatforbidden": "group",
        "channelforbidden": "channel",
        "user": "private"
    }
    return type_map.get(raw_type.lower(), raw_type.lower())

def merge_chat_data(existing: Optional[ChatModel], new: ChatModel) -> ChatModel:
    if not existing:
        return new
    return ChatModel(
        id=existing.id,
        members_count=new.members_count if new.members_count is not None else existing.members_count,
        title=new.title if new.title and new.title != "Unknown" else existing.title,
        type=new.type,
        username=new.username if new.username else existing.username
    )

async def fetch_chat_participants(client: TelegramClient, chat_id: int, chat_type: str, chat: ChatModel) -> List[UserModel]:
    users = []
    try:
        if chat_type in ["group", "channel"]:
            if chat.members_count is not None and chat.members_count > 5000:
                LOGGER.info(f"Skipping large chat {chat_id} with {chat.members_count} members to optimize performance")
                return []
            async for participant in client.iter_participants(chat_id, limit=5000):
                users.append(UserModel(
                    id=participant.id,
                    first_name=participant.first_name,
                    last_name=participant.last_name,
                    username=participant.username,
                    is_premium=getattr(participant, 'premium', False)
                ))
    except Exception as e:
        LOGGER.warning(f"Failed to fetch participants for chat {chat_id}: {str(e)}")
    return users

async def get_chats_and_users_fast(client: TelegramClient) -> Tuple[List[ChatModel], List[UserModel]]:
    chats: Dict[int, ChatModel] = {}
    users: Dict[int, UserModel] = {}
    inaccessible_chats = set()
    batch_count = 0

    try:
        state = await client.get_state()
        custom_pts = state.pts
        custom_date = state.date
        custom_qts = state.qts
        LOGGER.info(f"Initialized state: pts={custom_pts}, qts={custom_qts}, date={custom_date}")
    except Exception as e:
        LOGGER.warning(f"Failed to get initial state: {e}, using fallback values")
        custom_pts = 1
        custom_date = datetime.now()
        custom_qts = 1

    start_time = time.time()
    max_duration = 600
    max_batches = 1000
    no_data_count = 0
    max_no_data = 5

    try:
        while time.time() - start_time < max_duration and batch_count < max_batches:
            try:
                diff = await asyncio.wait_for(
                    client(functions.updates.GetDifferenceRequest(
                        pts=custom_pts,
                        date=custom_date,
                        qts=custom_qts,
                        pts_limit=10000,
                        qts_limit=10000
                    )),
                    timeout=60.0
                )

                if isinstance(diff, types.updates.DifferenceTooLong):
                    LOGGER.warning(f"Difference too long, updating pts to {diff.pts}")
                    custom_pts = diff.pts
                    continue

                if isinstance(diff, types.updates.DifferenceEmpty):
                    LOGGER.info("Difference empty, no new updates")
                    break

                batch_users = []
                batch_chats = []

                for user in getattr(diff, 'users', []):
                    if user.id not in users:
                        users[user.id] = UserModel(
                            id=user.id,
                            first_name=getattr(user, 'first_name', None),
                            last_name=getattr(user, 'last_name', None),
                            username=getattr(user, 'username', None),
                            is_premium=getattr(user, 'premium', False)
                        )
                        batch_users.append({
                            "id": user.id,
                            "first_name": getattr(user, 'first_name', None),
                            "username": getattr(user, 'username', None)
                        })

                for chat in getattr(diff, 'chats', []):
                    if chat.id not in chats and chat.id not in inaccessible_chats:
                        chat_class_name = chat.__class__.__name__.lower()
                        if chat_class_name in ["chatforbidden", "channelforbidden"]:
                            inaccessible_chats.add(chat.id)
                            continue

                        chat_type = normalize_chat_type(chat_class_name)
                        chat_data = ChatModel(
                            id=chat.id,
                            members_count=getattr(chat, 'participants_count', None),
                            title=getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown",
                            type=chat_type,
                            username=getattr(chat, 'username', None)
                        )
                        chats[chat.id] = merge_chat_data(chats.get(chat.id), chat_data)
                        batch_chats.append({
                            "id": chat_data.id,
                            "members_count": chat_data.members_count,
                            "title": chat_data.title,
                            "type": chat_data.type,
                            "username": chat_data.username
                        })

                for update in getattr(diff, 'new_messages', []):
                    if hasattr(update, 'message') and hasattr(update.message, 'peer_id'):
                        try:
                            chat = await client.get_entity(update.message.peer_id)
                            if chat.id not in chats and chat.id not in inaccessible_chats:
                                chat_class_name = chat.__class__.__name__.lower()
                                if chat_class_name in ["chatforbidden", "channelforbidden"]:
                                    inaccessible_chats.add(chat.id)
                                    continue

                                chat_type = normalize_chat_type(chat_class_name)
                                chat_data = ChatModel(
                                    id=chat.id,
                                    members_count=getattr(chat, 'participants_count', None),
                                    title=getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or "Unknown",
                                    type=chat_type,
                                    username=getattr(chat, 'username', None)
                                )
                                chats[chat.id] = merge_chat_data(chats.get(chat.id), chat_data)
                                batch_chats.append({
                                    "id": chat_data.id,
                                    "members_count": chat_data.members_count,
                                    "title": chat_data.title,
                                    "type": chat_data.type,
                                    "username": chat_data.username
                                })
                        except Exception as e:
                            LOGGER.warning(f"Failed to process message update: {str(e)}")

                if batch_users or batch_chats:
                    LOGGER.info(f"Batch {batch_count}: Users fetched: {len(batch_users)}, Chats fetched: {len(batch_chats)}")
                    no_data_count = 0
                else:
                    no_data_count += 1
                    if no_data_count >= max_no_data:
                        LOGGER.info("No new data for multiple batches, stopping iteration")
                        break

                batch_count += 1

                if isinstance(diff, types.updates.DifferenceSlice):
                    custom_pts = diff.intermediate_state.pts
                    custom_date = diff.intermediate_state.date
                    custom_qts = diff.intermediate_state.qts
                elif isinstance(diff, types.updates.Difference):
                    LOGGER.info("Reached final difference, stopping iteration")
                    break
                else:
                    LOGGER.warning(f"Unknown diff type: {type(diff)}")
                    break

                await asyncio.sleep(0.05)

            except PersistentTimestampEmptyError as e:
                LOGGER.error(f"Persistent timestamp empty error: {e}")
                try:
                    state = await client.get_state()
                    custom_pts = state.pts
                    custom_date = state.date
                    custom_qts = state.qts
                    LOGGER.info(f"Recovered state: pts={custom_pts}, qts={custom_qts}, date={custom_date}")
                    continue
                except Exception as state_e:
                    LOGGER.error(f"Failed to recover state: {state_e}")
                    break
            except asyncio.TimeoutError:
                LOGGER.warning("GetDifference timeout, continuing with collected data")
                break
            except FloodWaitError as fw:
                if fw.seconds > 30:
                    LOGGER.warning(f"FloodWait too long: {fw.seconds}s, breaking")
                    break
                LOGGER.info(f"FloodWait: {fw.seconds}s")
                await asyncio.sleep(fw.seconds)
            except Exception as e:
                LOGGER.error(f"Error in iteration {batch_count}: {str(e)}")
                if batch_count > max_batches:
                    LOGGER.warning("Reached max batches, stopping iteration")
                    break
                await asyncio.sleep(1)

        if time.time() - start_time >= max_duration:
            LOGGER.warning("Reached timeout, proceeding to fetch chat participants")

        LOGGER.info(f"Fetching participants from {len(chats)} chats to ensure all users are captured")
        tasks = []
        for chat_id, chat in chats.items():
            tasks.append(fetch_chat_participants(client, chat_id, chat.type, chat))

        for i in range(0, len(tasks), 10):
            batch_tasks = tasks[i:i+10]
            results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            for additional_users in results:
                if isinstance(additional_users, list):
                    for user in additional_users:
                        if user.id not in users:
                            users[user.id] = user

    except Exception as e:
        LOGGER.error(f"Major error fetching chats and users: {str(e)}")

    LOGGER.info(f"Collected {len(chats)} chats and {len(users)} users in {batch_count} batches")
    return list(chats.values()), list(users.values())

@router.get("")
async def get_bot_data_fast(
    background_tasks: BackgroundTasks,
    token: str = Query(..., description="Telegram Bot Token", min_length=10)
):
    start_time = time.time()
    
    if not token or len(token.strip()) < 10:
        raise HTTPException(status_code=400, detail="Invalid bot token format")

    try:
        LOGGER.info(f"Processing tgusers request for token: {token[:10]}...")
        client = await client_manager.get_client(bot_token=token.strip())

        try:
            bot_info_task = asyncio.create_task(
                asyncio.wait_for(client.get_me(), timeout=15.0)
            )
            chats_users_task = asyncio.create_task(
                asyncio.wait_for(get_chats_and_users_fast(client), timeout=600.0)
            )

            results = await asyncio.gather(
                bot_info_task,
                chats_users_task,
                return_exceptions=True
            )

            me = results[0]
            chats_users = results[1]

            if isinstance(me, Exception):
                LOGGER.error(f"Error getting bot info: {me}")
                raise me

            if isinstance(chats_users, Exception):
                LOGGER.warning(f"Error getting chats/users: {chats_users}")
                chats, users = [], []
            else:
                chats, users = chats_users

            if not isinstance(chats, list):
                chats = []
            if not isinstance(users, list):
                users = []

            bot_info = BotInfoModel(
                first_name=me.first_name or "Unknown",
                id=me.id,
                username=me.username
            )

            processing_time = time.time() - start_time
            
            response = BotDataResponse(
                bot_info=bot_info,
                chats=chats,
                users=users,
                total_chats=len(chats),
                total_users=len(users),
                processing_time=round(processing_time, 3)
            )

            LOGGER.info(f"TgUsers request completed in {processing_time:.3f}s - Chats: {len(chats)}, Users: {len(users)}")
            background_tasks.add_task(client_manager.cleanup_client, token.strip())
            
            return JSONResponse(content=response.dict(), status_code=200)

        except asyncio.TimeoutError:
            LOGGER.error("TgUsers request timeout")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=408, detail="Request timeout - try again")
        except (AuthKeyPermEmptyError, SessionPasswordNeededError) as e:
            LOGGER.error(f"Authentication error: {e}")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=401, detail="Invalid bot token or bot deactivated")
        except HTTPException:
            raise
        except RPCError as e:
            LOGGER.error(f"Telegram API error: {e}")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=400, detail=f"Telegram API error: {str(e)}")
        except Exception as e:
            LOGGER.error(f"Unexpected error: {e}")
            await client_manager.cleanup_client(token.strip())
            raise HTTPException(status_code=500, detail="Internal server error")

    except Exception as e:
        LOGGER.error(f"Unexpected error: {e}")
        await client_manager.cleanup_client(token.strip())
        raise HTTPException(status_code=500, detail="Internal server error")