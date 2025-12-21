from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiohttp
import re
from utils import LOGGER

router = APIRouter(prefix="/insta")

async def fetch_direct_regex_media(insta_url: str):
    try:
        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'dpr': '1.5',
            'priority': 'u=0, i',
            'sec-ch-prefers-color-scheme': 'dark',
            'sec-ch-ua': '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            'sec-ch-ua-full-version-list': '"Chromium";v="142.0.7444.176", "Google Chrome";v="142.0.7444.176", "Not_A Brand";v="99.0.0.0"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-model': '""',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'none',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36',
            'viewport-width': '399',
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(insta_url, headers=headers) as response:
                LOGGER.info(f"Direct regex scrape status: {response.status} for {insta_url}")
                if response.status != 200:
                    text = await response.text()
                    LOGGER.info(f"Direct regex response preview: {text[:500]}")
                    return None
                html = await response.text()
            video_urls = set()
            thumbnails = set()
            video_pattern = r'"url"\s*:\s*"(https?:\\?/\\?/[^"]*\.mp4[^"]*)"'
            for match in re.findall(video_pattern, html):
                clean_url = match.replace('\\/', '/').replace('\\u0026', '&')
                video_urls.add(clean_url)
            img_pattern = r'"candidates"\s*:\s*\[\s*\{\s*"url"\s*:\s*"([^"]+)"'
            for match in re.findall(img_pattern, html):
                clean_url = match.replace('\\/', '/').replace('\\u0026', '&')
                thumbnails.add(clean_url)
            if not thumbnails:
                display_pattern = r'"display_url"\s*:\s*"([^"]+)"'
                for match in re.findall(display_pattern, html):
                    clean_url = match.replace('\\/', '/').replace('\\u0026', '&')
                    thumbnails.add(clean_url)
            if not video_urls and not thumbnails:
                LOGGER.info("Direct regex: No media found")
                return None
            results = []
            image_count = 1
            video_count = 1
            thumb_list = list(thumbnails)
            thumbnail = thumb_list[0] if thumb_list else None
            for url in video_urls:
                results.append({
                    "label": f"video{video_count}",
                    "thumbnail": thumbnail,
                    "download": url
                })
                video_count += 1
            for url in thumbnails:
                if url not in video_urls:
                    results.append({
                        "label": f"image{image_count}",
                        "thumbnail": thumbnail,
                        "download": url
                    })
                    image_count += 1
            LOGGER.info(f"Direct regex success: {len(results)} media found")
            return results if results else None
    except Exception as e:
        LOGGER.error(f"Direct regex scrape failed: {str(e)}")
        return None

async def fetch_instasaves_media(insta_url: str):
    try:
        api_url = "https://instsaves.pro/wp-json/visolix/api/download"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        }
        payload = {
            "url": insta_url,
            "format": "",
            "captcha_response": None
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                resp_text = await response.text()
                LOGGER.info(f"instsaves.pro status: {response.status} | Preview: {resp_text[:500]}")
                if response.status != 200:
                    return None
                data = await response.json()
                if not data.get("status") or not data.get("data"):
                    return None
                html_content = data["data"]
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            media_boxes = soup.select(".visolix-media-box")
            if not media_boxes:
                return None
            results = []
            image_count = 1
            video_count = 1
            for box in media_boxes:
                img_tag = box.find("img", recursive=False)
                preview_img = img_tag["src"] if img_tag else None
                download_tag = box.find("a", class_="visolix-download-media", href=True)
                if not download_tag:
                    continue
                download_url = download_tag["href"]
                download_text = download_tag.get_text().strip().lower()
                if "video" in download_text or "igtv" in download_text or "reel" in download_text:
                    label = f"video{video_count}"
                    video_count += 1
                elif "image" in download_text or "photo" in download_text:
                    label = f"image{image_count}"
                    image_count += 1
                elif "story" in download_text:
                    label = f"story_video{video_count}"
                    video_count += 1
                else:
                    label = f"media{len(results)+1}"
                results.append({
                    "label": label,
                    "thumbnail": preview_img,
                    "download": download_url
                })
            LOGGER.info(f"instsaves.pro success: {len(results)} media found")
            return results if results else None
    except Exception as e:
        LOGGER.error(f"instsaves.pro failed: {str(e)}")
        return None

async def fetch_fastdl_media(insta_url: str):
    try:
        api_url = "https://fastdl.live/api/search"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
        }
        payload = {"url": insta_url}
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload, headers=headers) as response:
                resp_text = await response.text()
                LOGGER.info(f"fastdl.live status: {response.status} | Preview: {resp_text[:500]}")
                if response.status != 200:
                    return None
                data = await response.json()
                if not data.get("success") or not data.get("result"):
                    return None
                results = []
                image_count = 1
                video_count = 1
                for item in data["result"]:
                    media_type = item.get("type", "").lower()
                    if "video" in media_type or "reel" in media_type:
                        label = f"video{video_count}"
                        video_count += 1
                    else:
                        label = f"image{image_count}"
                        image_count += 1
                    results.append({
                        "label": label,
                        "thumbnail": item.get("thumbnail"),
                        "download": item.get("downloadLink")
                    })
                LOGGER.info(f"fastdl.live success: {len(results)} media found")
                return results if results else None
    except Exception as e:
        LOGGER.error(f"fastdl.live failed: {str(e)}")
        return None

async def fetch_insta_media(insta_url: str):
    LOGGER.info(f"Processing Instagram URL: {insta_url}")
    media = await fetch_direct_regex_media(insta_url)
    if media:
        LOGGER.info("Direct regex scrape succeeded")
        return media
    LOGGER.info("Direct regex scrape failed, trying instsaves.pro")
    media = await fetch_instasaves_media(insta_url)
    if media:
        LOGGER.info("instsaves.pro succeeded")
        return media
    LOGGER.info("instsaves.pro failed, trying fastdl.live")
    media = await fetch_fastdl_media(insta_url)
    if media:
        LOGGER.info("fastdl.live succeeded")
        return media
    LOGGER.info("All methods failed - no media found")
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
        media_list = await fetch_insta_media(url)
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