from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pyrogram import Client
from pyrogram.enums import ChatType, UserStatus
from pyrogram.errors import PeerIdInvalid, UsernameNotOccupied, ChannelInvalid
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from config import API_ID, API_HASH, BOT_TOKEN
from utils import LOGGER
import asyncio
import threading
import os

router = APIRouter(prefix="/user")
client = None
client_lock = threading.Lock()

def get_dc_locations():
    return {
        1: "MIA, Miami, USA, US",
        2: "AMS, Amsterdam, Netherlands, NL",
        3: "MBA, Mumbai, India, IN",
        4: "STO, Stockholm, Sweden, SE",
        5: "SIN, Singapore, SG",
        6: "LHR, London, United Kingdom, GB",
        7: "FRA, Frankfurt, Germany, DE",
        8: "JFK, New York, USA, US",
        9: "HKG, Hong Kong, HK",
        10: "TYO, Tokyo, Japan, JP",
        11: "SYD, Sydney, Australia, AU",
        12: "GRU, São Paulo, Brazil, BR",
        13: "DXB, Dubai, UAE, AE",
        14: "CDG, Paris, France, FR",
        15: "ICN, Seoul, South Korea, KR",
    }

def calculate_account_age(creation_date):
    today = datetime.now()
    delta = relativedelta(today, creation_date)
    years = delta.years
    months = delta.months
    days = delta.days
    return f"{years} years, {months} months, {days} days"

def estimate_account_creation_date(user_id):
    reference_points = [
        (100000000, datetime(2013, 8, 1)),
        (1273841502, datetime(2020, 8, 13)),
        (1500000000, datetime(2021, 5, 1)),
        (2000000000, datetime(2022, 12, 1)),
    ]
    closest_point = min(reference_points, key=lambda x: abs(x[0] - user_id))
    closest_user_id, closest_date = closest_point
    id_difference = user_id - closest_user_id
    days_difference = id_difference / 20000000
    creation_date = closest_date + timedelta(days=days_difference)
    return creation_date

def format_user_status(status):
    if not status:
        return "Unknown"
    status_map = {
        UserStatus.ONLINE: "Online",
        UserStatus.OFFLINE: "Offline",
        UserStatus.RECENTLY: "Recently online",
        UserStatus.LAST_WEEK: "Last seen within week",
        UserStatus.LAST_MONTH: "Last seen within month",
        UserStatus.LONG_AGO: "Last seen long ago"
    }
    return status_map.get(status, "Unknown")

def get_profile_photo_url(username, size=320):
    if username:
        username = username.strip('@')
        return f"https://t.me/i/userpic/{size}/{username}.jpg"
    return None

def format_usernames_list(usernames):
    if not usernames:
        return []
    formatted_usernames = []
    for username_obj in usernames:
        if hasattr(username_obj, 'username'):
            formatted_usernames.append(username_obj.username)
        else:
            formatted_usernames.append(str(username_obj))
    return formatted_usernames

async def ensure_client():
    global client
    with client_lock:
        if client is None:
            try:
                os.makedirs("/tmp", exist_ok=True)
                client = Client(
                    "A360APIUser",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN,
                    workdir="/tmp",
                    in_memory=True
                )
                await client.start()
                LOGGER.info("Pyrogram client started successfully")
                return True
            except Exception as e:
                LOGGER.error(f"Failed to start Pyrogram client: {str(e)}")
                client = None
                return False
        
        try:
            is_connected = getattr(client, 'is_connected', False)
            if callable(is_connected):
                connected = is_connected()
            else:
                connected = is_connected
            
            if not connected:
                await client.start()
                LOGGER.info("Pyrogram client reconnected successfully")
        except Exception as e:
            LOGGER.error(f"Failed to check/restart client: {str(e)}")
            try:
                os.makedirs("/tmp", exist_ok=True)
                client = Client(
                    "A360APIUser",
                    api_id=API_ID,
                    api_hash=API_HASH,
                    bot_token=BOT_TOKEN,
                    workdir="/tmp",
                    in_memory=True
                )
                await client.start()
                LOGGER.info("Pyrogram client recreated successfully")
            except Exception as e2:
                LOGGER.error(f"Failed to recreate client: {str(e2)}")
                client = None
                return False
        
        return True

async def get_user_info(username):
    try:
        if not await ensure_client():
            return {"success": False, "error": "Client initialization failed"}
        
        DC_LOCATIONS = get_dc_locations()
        user = await client.get_users(username)
        
        full_user = await client.get_chat(username)
        bio = getattr(full_user, 'bio', None)
        
        premium_status = getattr(user, 'is_premium', False)
        dc_location = DC_LOCATIONS.get(user.dc_id, "Unknown")
        account_created = estimate_account_creation_date(user.id)
        account_created_str = account_created.strftime("%B %d, %Y")
        account_age = calculate_account_age(account_created)
        verified_status = getattr(user, 'is_verified', False)
        status = format_user_status(getattr(user, 'status', None))
        flags = "Clean"
        if getattr(user, 'is_scam', False):
            flags = "Scam"
        elif getattr(user, 'is_fake', False):
            flags = "Fake"
        
        profile_photo_url = get_profile_photo_url(user.username) if user.username else None
        
        last_online_date = None
        next_offline_date = None
        if hasattr(user, 'last_online_date') and user.last_online_date:
            last_online_date = user.last_online_date.strftime("%B %d, %Y at %H:%M:%S")
        if hasattr(user, 'next_offline_date') and user.next_offline_date:
            next_offline_date = user.next_offline_date.strftime("%B %d, %Y at %H:%M:%S")
        
        usernames_list = format_usernames_list(getattr(user, 'usernames', []))
        
        user_data = {
            "success": True,
            "type": "bot" if user.is_bot else "user",
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "usernames": usernames_list,
            "bio": bio,
            "dc_id": user.dc_id,
            "dc_location": dc_location,
            "is_premium": premium_status,
            "is_verified": verified_status,
            "is_bot": user.is_bot,
            "is_scam": getattr(user, 'is_scam', False),
            "is_fake": getattr(user, 'is_fake', False),
            "is_frozen": getattr(user, 'is_frozen', False),
            "frozen_icon": getattr(user, 'frozen_icon', None),
            "flags": flags,
            "status": status,
            "last_online_date": last_online_date,
            "next_offline_date": next_offline_date,
            "account_created": account_created_str,
            "account_age": account_age,
            "profile_photo_url": profile_photo_url,
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz",
            "links": {
                "android": f"tg://openmessage?user_id={user.id}",
                "ios": f"tg://user?id={user.id}",
                "permanent": f"tg://user?id={user.id}"
            }
        }
        return user_data
    except (PeerIdInvalid, UsernameNotOccupied):
        return {"success": False, "error": "User not found"}
    except Exception as e:
        LOGGER.error(f"Error fetching user info: {str(e)}")
        return {"success": False, "error": f"Failed to fetch user information: {str(e)}"}

async def get_chat_info(username):
    try:
        if not await ensure_client():
            return {"success": False, "error": "Client initialization failed"}
        
        DC_LOCATIONS = get_dc_locations()
        chat = await client.get_chat(username)
        chat_type_map = {
            ChatType.SUPERGROUP: "supergroup",
            ChatType.GROUP: "group",
            ChatType.CHANNEL: "channel"
        }
        chat_type = chat_type_map.get(chat.type, "unknown")
        dc_location = DC_LOCATIONS.get(getattr(chat, 'dc_id', None), "Unknown")
        
        profile_photo_url = get_profile_photo_url(chat.username) if chat.username else None
        
        usernames_list = format_usernames_list(getattr(chat, 'usernames', []))
        
        if chat.username:
            join_link = f"t.me/{chat.username}"
            permanent_link = f"t.me/{chat.username}"
        elif chat.id < 0:
            chat_id_str = str(chat.id).replace('-100', '')
            join_link = f"t.me/c/{chat_id_str}/1"
            permanent_link = f"t.me/c/{chat_id_str}/1"
        else:
            join_link = f"tg://resolve?domain={chat.id}"
            permanent_link = f"tg://resolve?domain={chat.id}"
        
        flags = "Clean"
        if getattr(chat, 'is_scam', False):
            flags = "Scam"
        elif getattr(chat, 'is_fake', False):
            flags = "Fake"
        
        chat_data = {
            "success": True,
            "type": chat_type,
            "id": chat.id,
            "title": chat.title,
            "username": chat.username,
            "usernames": usernames_list,
            "description": getattr(chat, 'description', None),
            "dc_id": getattr(chat, 'dc_id', None),
            "dc_location": dc_location,
            "members_count": getattr(chat, 'members_count', None),
            "is_verified": getattr(chat, 'is_verified', False),
            "is_restricted": getattr(chat, 'is_restricted', False),
            "is_scam": getattr(chat, 'is_scam', False),
            "is_fake": getattr(chat, 'is_fake', False),
            "is_frozen": getattr(chat, 'is_frozen', False),
            "frozen_icon": getattr(chat, 'frozen_icon', None),
            "flags": flags,
            "profile_photo_url": profile_photo_url,
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz",
            "links": {
                "join": join_link,
                "permanent": permanent_link
            }
        }
        return chat_data
    except (ChannelInvalid, PeerIdInvalid):
        return {"success": False, "error": "Chat not found or access denied"}
    except Exception as e:
        LOGGER.error(f"Error fetching chat info: {str(e)}")
        return {"success": False, "error": f"Failed to fetch chat information: {str(e)}"}

async def get_telegram_info(username):
    username = username.strip('@').replace('https://', '').replace('http://', '').replace('t.me/', '').replace('/', '').replace(':', '')
    LOGGER.info(f"Fetching info for: {username}")
    
    user_info = await get_user_info(username)
    if user_info["success"]:
        return user_info
    
    chat_info = await get_chat_info(username)
    if chat_info["success"]:
        return chat_info
    
    return {"success": False, "error": "Entity not found in Telegram database", "api_owner": "@ISmartCoder", "api_updates": "t.me/abirxdhackz"}

@router.get("/info")
async def info_endpoint(username: str = "", size: int = 320):
    if not username:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'username' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        result = await get_telegram_info(username)
        if result["success"] and "profile_photo_url" in result and result["profile_photo_url"]:
            result["profile_photo_url"] = get_profile_photo_url(
                result.get("username"), size
            ) if result.get("username") else None
        
        return JSONResponse(
            content=result,
            status_code=200 if result["success"] else 404
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error fetching Telegram info for {username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Internal server error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )