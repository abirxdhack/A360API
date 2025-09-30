#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiohttp
import asyncio
from utils import LOGGER

router = APIRouter(prefix="/net")
IPINFO_URL = "https://ipinfo.io/{ip}/json?token=69ee063dfc785d"
HTTPBIN_IP_URL = "http://httpbin.org/ip"
HTTPBIN_HEADERS_URL = "http://httpbin.org/headers"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
PROXY_TIMEOUT = 10
GEOLOCATION_TIMEOUT = 3

async def get_ip_info(ip: str):
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(IPINFO_URL.format(ip=ip), timeout=GEOLOCATION_TIMEOUT) as response:
                response.raise_for_status()
                data = await response.json()
                return {
                    "ip": data.get("ip", "Unknown"),
                    "asn": data.get("org", "Unknown"),
                    "isp": data.get("org", "Unknown"),
                    "country": data.get("country", "Unknown"),
                    "city": data.get("city", "Unknown"),
                    "timezone": data.get("timezone", "Unknown"),
                    "fraud_score": 0,
                    "risk_level": "low"
                }
    except aiohttp.ClientError as e:
        LOGGER.error(f"Failed to fetch IP info for {ip}: {str(e)}")
        return None

async def check_anonymity(session, proxy_url):
    try:
        async with session.get(
            HTTPBIN_HEADERS_URL,
            proxy=proxy_url,
            timeout=PROXY_TIMEOUT,
            headers=HEADERS
        ) as response:
            if response.status == 200:
                headers_data = await response.json()
                client_headers = headers_data.get('headers', {})
                if 'X-Forwarded-For' in client_headers:
                    return 'Transparent'
                elif 'Via' in client_headers:
                    return 'Anonymous'
                return 'Elite'
            return 'Unknown'
    except Exception:
        return 'Unknown'

async def check_proxy(proxy: str, proxy_type: str = 'http', auth: dict = None):
    result = {
        'proxy': proxy,
        'status': 'Dead',
        'location': 'Not determined',
        'anonymity': 'Unknown'
    }
    ip = proxy.split(':')[0]
    try:
        proxy_url = f"{proxy_type}://{auth['username']}:{auth['password']}@{proxy}" if auth else f"{proxy_type}://{proxy}"
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(
                HTTPBIN_IP_URL,
                proxy=proxy_url,
                timeout=PROXY_TIMEOUT
            ) as response:
                if response.status == 200:
                    result.update({
                        'status': 'Live',
                        'ip': ip
                    })
                    result['anonymity'] = await check_anonymity(session, proxy_url)
            async with session.get(
                IPINFO_URL.format(ip=ip),
                timeout=GEOLOCATION_TIMEOUT
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    result['location'] = f"{data.get('region', 'Unknown')} ({data.get('country', 'Unknown')})"
                else:
                    result['location'] = f"HTTP {response.status}"
    except Exception as e:
        LOGGER.error(f"Error checking proxy {proxy}: {str(e)}")
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.get(IPINFO_URL.format(ip=ip), timeout=GEOLOCATION_TIMEOUT) as response:
                if response.status == 200:
                    data = await response.json()
                    result['location'] = f"{data.get('region', 'Unknown')} ({data.get('country', 'Unknown')})"
                else:
                    result['location'] = f"HTTP {response.status}"
    return result

@router.get("/chk")
async def check_ip(ip: str = ""):
    if not ip:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'ip' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        data = await get_ip_info(ip)
        if data is None:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Invalid IP address or API error",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(
            content={
                "success": True,
                "data": data,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error fetching IP info for {ip}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/px")
async def check_proxy_endpoint(proxy: str = ""):
    if not proxy:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'proxy' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        auth = None
        proxy_type = 'http'
        proxy_clean = proxy
        if proxy.count(':') == 3:
            ip_port, username, password = proxy.rsplit(':', 2)
            auth = {'username': username, 'password': password}
            proxy_clean = ip_port
        elif '://' in proxy:
            parts = proxy.split('://')
            if len(parts) == 2 and parts[0].lower() in ['http', 'https']:
                proxy_type = parts[0].lower()
                proxy_clean = parts[1]
        
        result = await check_proxy(proxy_clean, proxy_type, auth)
        return JSONResponse(
            content={
                "success": True,
                "data": result,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error checking proxy {proxy}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )