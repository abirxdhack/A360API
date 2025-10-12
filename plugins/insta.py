from fastapi import APIRouter
from fastapi.responses import JSONResponse
import cloudscraper
from bs4 import BeautifulSoup
import aiohttp
from utils import LOGGER

router = APIRouter(prefix="/insta")

async def fetch_ytdownload_media(insta_url: str):
    try:
        scraper = cloudscraper.create_scraper()
        async with aiohttp.ClientSession() as session:
            headers = {
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'Accept-Language': 'en-US,en;q=0.9,bn;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/json',
                'Origin': 'https://ytdownload.in',
                'Referer': 'https://ytdownload.in/',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36 Edg/141.0.0.0',
                'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?1',
                'sec-ch-ua-platform': '"Android"',
                'x-client': 'web'
            }
            async with session.get('https://ytdownload.in', headers=headers) as response:
                response.raise_for_status()
                text = await response.text()
                cookies = {cookie.key: cookie.value for cookie in response.cookies}
            BeautifulSoup(text, 'html.parser')
            payload = {
                'url': insta_url,
                'format': 'mp4',
                'quality': '1080p'
            }
            async with session.post(
                'https://ytdownload.in/api/allinonedownload',
                json=payload,
                headers=headers,
                cookies=cookies
            ) as api_response:
                response_data = await api_response.json() if api_response.content else {}
                if not response_data or 'responseFinal' not in response_data:
                    return None
                results = []
                image_count = 1
                video_count = 1
                response_final = response_data['responseFinal']
                thumbnail = response_final.get('thumbnails') if response_final.get('thumbnails') else None
                if response_final.get('videoUrl'):
                    label = f"video{video_count}"
                    video_count += 1
                    results.append({
                        "label": label,
                        "thumbnail": thumbnail,
                        "download": response_final['videoUrl']
                    })
                if response_final.get('formats'):
                    for fmt in response_final['formats']:
                        if fmt.get('url'):
                            if 'mp4' in fmt['url'].lower():
                                label = f"video{video_count}"
                                video_count += 1
                            else:
                                label = f"image{image_count}"
                                image_count += 1
                            results.append({
                                "label": label,
                                "thumbnail": thumbnail,
                                "download": fmt['url']
                            })
                if not results:
                    return None
                return results
    except Exception as e:
        LOGGER.error(f"Failed to fetch from ytdownload.in: {str(e)}")
        return None

@router.get("/dl")
async def download(url: str = ""):
    try:
        if not url:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error": "Missing 'url' parameter",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        media_list = await fetch_ytdownload_media(url)
        if not media_list:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "error": "Media not found or unsupported",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(
            content={
                "status": "success",
                "media_count": len(media_list),
                "results": media_list,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Server error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": f"Server error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )