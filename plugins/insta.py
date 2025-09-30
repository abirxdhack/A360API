from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup

router = APIRouter(prefix="/insta")

API_URL = "https://instsaves.pro/wp-json/visolix/api/download"
HEADERS = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

def fetch_html(insta_url: str):
    payload = {"url": insta_url, "format": "", "captcha_response": None}
    response = requests.post(API_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    json_data = response.json()
    if not json_data.get("status") or not json_data.get("data"):
        return None
    return json_data["data"]

def parse_media(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    media_boxes = soup.select(".visolix-media-box")
    results = []
    image_count = 1
    video_count = 1
    for box in media_boxes:
        img_tag = box.find("img", recursive=False)
        preview_img = img_tag["src"] if img_tag else None
        download_tag = box.find("a", class_="visolix-download-media", href=True)
        download_url = download_tag["href"] if download_tag else None
        download_text = download_tag.text.lower() if download_tag else ""
        if "video" in download_text:
            label = f"video{video_count}"
            video_count += 1
        elif "image" in download_text:
            label = f"image{image_count}"
            image_count += 1
        elif "story" in download_text:
            label = f"story_video{video_count}"
            video_count += 1
        else:
            label = "thumbnail"
        results.append({"label": label, "thumbnail": preview_img, "download": download_url})
    return results

@router.get("/dl")
async def download(url: str = ""):
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
    try:
        html = fetch_html(url)
        if not html:
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "error": "Media not found or unsupported",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        media_list = parse_media(html)
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
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
