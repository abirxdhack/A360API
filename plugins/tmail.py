#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiohttp
import random
import string
import hashlib
import time
from bs4 import BeautifulSoup
from utils import LOGGER

router = APIRouter(prefix="/tmail")
BASE_URL = "https://api.mail.tm"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
MAX_MESSAGE_LENGTH = 4000

def generate_random_username(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

def short_id_generator(email):
    unique_string = email + str(time.time())
    return hashlib.md5(unique_string.encode()).hexdigest()[:10]

async def get_domain():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/domains", headers=HEADERS, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                if isinstance(data, list) and data:
                    return data[0]['domain']
                elif 'hydra:member' in data and data['hydra:member']:
                    return data['hydra:member'][0]['domain']
                return None
    except Exception as e:
        LOGGER.error(f"Error fetching domain: {str(e)}")
        return None

async def create_account(email, password):
    data = {
        "address": email,
        "password": password
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/accounts", headers=HEADERS, json=data, timeout=10) as response:
                if response.status in [200, 201]:
                    return await response.json()
                LOGGER.error(f"Error creating account: {response.status} - {await response.text()}")
                return None
    except Exception as e:
        LOGGER.error(f"Error in create_account: {str(e)}")
        return None

async def get_token(email, password):
    data = {
        "address": email,
        "password": password
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/token", headers=HEADERS, json=data, timeout=10) as response:
                if response.status == 200:
                    return (await response.json()).get('token')
                LOGGER.error(f"Error fetching token: {response.status} - {await response.text()}")
                return None
    except Exception as e:
        LOGGER.error(f"Error in get_token: {str(e)}")
        return None

async def list_messages(token):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/messages", headers=headers, timeout=10) as response:
                data = await response.json()
                if isinstance(data, list):
                    return data
                elif 'hydra:member' in data:
                    return data['hydra:member']
                return []
    except Exception as e:
        LOGGER.error(f"Error in list_messages: {str(e)}")
        return []

async def get_message_details(token, message_id):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/messages/{message_id}", headers=headers, timeout=10) as response:
                if response.status == 200:
                    return await response.json()
                LOGGER.error(f"Error fetching message details: {response.status} - {await response.text()}")
                return None
    except Exception as e:
        LOGGER.error(f"Error in get_message_details: {str(e)}")
        return None

def get_text_from_html(html_content_list):
    html_content = ''.join(html_content_list)
    soup = BeautifulSoup(html_content, 'html.parser')
    for a_tag in soup.find_all('a', href=True):
        url = a_tag['href']
        new_content = f"{a_tag.text} [{url}]"
        a_tag.string = new_content
    text_content = soup.get_text()
    cleaned_content = ' '.join(text_content.split())
    return cleaned_content[:MAX_MESSAGE_LENGTH - 100] + "... [message truncated]" if len(cleaned_content) > MAX_MESSAGE_LENGTH else cleaned_content

@router.get("/gen")
async def generate_temp_mail(username: str = None, password: str = None):
    try:
        domain = await get_domain()
        if not domain:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to retrieve domain from mail.tm API",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        email = f"{username}@{domain}" if username else f"{generate_random_username()}@{domain}"
        password = password if password else generate_random_password()
        
        account = await create_account(email, password)
        if not account:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Failed to create account. Username may already be taken.",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        token = await get_token(email, password)
        if not token:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Failed to retrieve token",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        short_id = short_id_generator(email)
        return JSONResponse(
            content={
                "success": True,
                "data": {
                    "email": email,
                    "password": password,
                    "token": token,
                    "short_id": short_id
                },
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error generating temp mail: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/cmail")
async def check_temp_mail(token: str = ""):
    if not token:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'token' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

    try:
        messages = await list_messages(token)
        if not messages:
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "data": [],
                    "message": "No messages found or invalid token",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        formatted_messages = []
        for msg in messages[:10]:
            details = await get_message_details(token, msg['id'])
            if details:
                message_text = get_text_from_html(details['html']) if 'html' in details else details.get('text', 'Content not available')
                formatted_messages.append({
                    "id": msg['id'],
                    "from": msg['from']['address'],
                    "subject": msg['subject'],
                    "content": message_text
                })

        return JSONResponse(
            content={
                "success": True,
                "data": formatted_messages,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error checking mail for token {token}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )