#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiohttp
import re
import base64
import json
from urllib.parse import parse_qs, urlparse
from utils import LOGGER

router = APIRouter(prefix="/tik")
API_URL = "https://tikdownloader.io/api/ajaxSearch"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://tikdownloader.io/",
    "Origin": "https://tikdownloader.io"
}

def sanitize_filename(filename):
    """Remove invalid characters and query parameters from filename, ensuring extension."""
    filename = filename.split('?')[0]
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    filename = re.sub(r'_+', '_', filename)
    filename = filename.strip('_')
    if not filename.lower().endswith(('.mp4', '.mp3')):
        filename += '.mp4'
    return filename

async def fetch_tiktok_data(url: str):
    payload = {"q": url, "lang": "en"}
    try:
        async with aiohttp.ClientSession(headers=HEADERS) as session:
            async with session.post(API_URL, data=payload, timeout=10) as response:
                response.raise_for_status()
                data = await response.json()
                if data.get("status") != "ok":
                    LOGGER.error("API returned invalid status")
                    return None, "API returned invalid status"
                html_content = data.get("data", "")
                if not html_content:
                    LOGGER.error("No data found in API response")
                    return None, "No data found in API response"
                return html_content, None
    except aiohttp.ClientConnectionError as e:
        LOGGER.error(f"Connection error: {str(e)}")
        return None, f"Connection error: {str(e)}"
    except aiohttp.ClientResponseError as e:
        LOGGER.error(f"API request failed: {str(e)}")
        return None, f"API request failed: {str(e)}"
    except asyncio.TimeoutError:
        LOGGER.error("Request timed out")
        return None, "Request timed out"
    except Exception as e:
        LOGGER.error(f"Unexpected error: {str(e)}")
        return None, f"Unexpected error: {str(e)}"

@router.get("/dl")
async def download_tiktok_links(url: str):
    if not url or not url.startswith("https://www.tiktok.com/"):
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid or missing TikTok URL",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        html_content, error = await fetch_tiktok_data(url)
        if error or html_content is None:
            return JSONResponse(
                status_code=500 if "timeout" not in error.lower() else 504,
                content={
                    "success": False,
                    "error": error,
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        # Extract only snapcdn.app links to avoid 403 errors
        download_links = []
        filenames = []
        links = re.findall(r'href="(https://dl\.snapcdn\.app/get\?token=[^"]+)"', html_content)
        for link in links:
            download_links.append(link)
            # Extract filename from token
            parsed_url = urlparse(link)
            query_params = parse_qs(parsed_url.query)
            token = query_params.get('token', [None])[0]
            if token:
                try:
                    payload_part = token.split('.')[1]
                    payload_part += '=' * (-len(payload_part) % 4)
                    decoded = json.loads(base64.b64decode(payload_part).decode('utf-8'))
                    filename = decoded.get('filename', '')
                    if filename:
                        filenames.append(sanitize_filename(filename))
                    else:
                        filenames.append(sanitize_filename(f"TikTok_{url.split('/')[-1]}"))
                except Exception:
                    filenames.append(sanitize_filename(f"TikTok_{url.split('/')[-1]}"))
            else:
                filenames.append(sanitize_filename(f"TikTok_{url.split('/')[-1]}"))
        
        if not download_links:
            return JSONResponse(
                status_code=404,
                content={
                    "success": False,
                    "error": "No downloadable links found",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        result = [
            {"url": link, "filename": filename}
            for link, filename in zip(download_links, filenames)
        ]
        return JSONResponse(
            content={
                "success": True,
                "links": result,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing TikTok URL {url}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )