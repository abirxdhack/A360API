from fastapi import APIRouter
from fastapi.responses import JSONResponse
import cloudscraper
from bs4 import BeautifulSoup
import aiohttp
from utils import LOGGER

router = APIRouter(prefix="/fb")

async def get_ytdownload_links(fb_url):
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
                text = await response.text()
                cookies = {cookie.key: cookie.value for cookie in response.cookies}
            BeautifulSoup(text, 'html.parser')
            payload = {
                'url': fb_url,
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
                if not response_data or 'data' not in response_data:
                    return {"error": "No downloadable content found from ytdownload.in."}
                downloads = {'links': [], 'thumbnail': None, 'title': "Unknown Title"}
                if 'data' in response_data and 'links' in response_data['data']:
                    for link in response_data['data']['links']:
                        quality = link.get('quality', 'Unknown')
                        url = link.get('url')
                        if url:
                            downloads['links'].append({'quality': quality, 'url': url})
                    if response_data['data'].get('thumbnail'):
                        downloads['thumbnail'] = response_data['data']['thumbnail']
                    if response_data['data'].get('title'):
                        downloads['title'] = response_data['data']['title']
                if not downloads['links']:
                    return {"error": "No downloadable video links found from ytdownload.in."}
                return downloads
    except Exception as e:
        LOGGER.error(f"Failed to fetch from ytdownload.in: {str(e)}")
        return {"error": f"Failed to fetch from ytdownload.in: {str(e)}"}

async def get_download_links(fb_url):
    results = []
    ytdownload_result = await get_ytdownload_links(fb_url)
    if not isinstance(ytdownload_result, dict) or "error" not in ytdownload_result:
        results.append(ytdownload_result)
    if not results:
        return {"error": "All sources failed to retrieve download links."}
    combined_links = []
    title = "Unknown Title"
    thumbnail = "Not available"
    for result in results:
        if result.get('links'):
            for link in result['links']:
                if not any(l['url'] == link['url'] for l in combined_links):
                    combined_links.append(link)
        if result.get('title') and result['title'] != "Unknown Title":
            title = result['title']
        if result.get('thumbnail') and result['thumbnail'] != "Not available":
            thumbnail = result['thumbnail']
    if not combined_links:
        return {"error": "No valid download links found from any source."}
    return {
        "links": combined_links,
        "title": title,
        "thumbnail": thumbnail,
        "api_owner": "@ISmartCoder",
        "api_updates": "t.me/abirxdhackz"
    }

@router.get("/dl")
async def download_links(url: str = ""):
    try:
        if not url:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing 'url' query parameter",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        result = await get_download_links(url)
        if "error" in result:
            return JSONResponse(
                status_code=400,
                content={
                    "error": result["error"],
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(content=result)
    except Exception as e:
        LOGGER.error(f"Server error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Server error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )