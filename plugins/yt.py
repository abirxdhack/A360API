from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
import re
import html
from collections import OrderedDict
from utils import LOGGER
from py_yt import VideosSearch, Search

router = APIRouter(prefix="/yt")

def extract_video_id(url):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&?\s]+)',
        r'(?:https?:\/\/)?youtu\.be\/([^&?\s]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^&?\s]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([^&?\s]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([^&?\s]+)'
    ]
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    query_match = re.search(r'v=([^&?\s]+)', url)
    if query_match:
        return query_match.group(1)
    return None

def parse_duration(duration_str):
    try:
        if not duration_str:
            return "N/A"
        parts = duration_str.split(':')
        hours = minutes = seconds = 0
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
        elif len(parts) == 1:
            seconds = int(parts[0])
        formatted = ""
        if hours > 0:
            formatted += f"{hours}h "
        if minutes > 0:
            formatted += f"{minutes}m "
        if seconds > 0:
            formatted += f"{seconds}s"
        return formatted.strip() or "0s"
    except Exception:
        return "N/A"

async def fetch_youtube_details(video_id):
    try:
        src = VideosSearch(video_id, limit=1)
        data = await src.next()
        if not data or not data.get('result'):
            LOGGER.error(f"No video found for ID {video_id}")
            return {"error": "No video found for the provided ID."}
        video = data['result'][0]
        return {
            "title": html.unescape(video.get('title', 'N/A')),
            "channel": html.unescape(video.get('channel', {}).get('name', 'N/A')),
            "description": html.unescape(video.get('description', 'N/A')),
            "tags": video.get('tags', []),
            "imageUrl": video.get('thumbnails', [{}])[-1].get('url', ''),
            "duration": parse_duration(video.get('duration', '')),
            "views": video.get('viewCount', {}).get('short', 'N/A'),
            "likes": video.get('accessibility', {}).get('likes', 'N/A') if video.get('accessibility') else 'N/A',
            "comments": 'N/A'
        }
    except Exception as e:
        LOGGER.error(f"Error fetching YouTube details for {video_id}: {str(e)}")
        return {"error": "Failed to fetch YouTube video details."}

async def fetch_youtube_search(query):
    try:
        src = Search(query, limit=10)
        data = await src.next()
        if not data or not data.get('result'):
            LOGGER.error(f"No videos found for query {query}")
            return {"error": "No videos found for the provided query."}
        result = []
        for item in data['result']:
            if item.get('type') != 'video':
                continue
            result.append({
                "title": html.unescape(item.get('title', 'N/A')),
                "channel": html.unescape(item.get('channel', {}).get('name', 'N/A')),
                "tags": [],
                "imageUrl": item.get('thumbnails', [{}])[-1].get('url', ''),
                "link": item.get('link', ''),
                "duration": parse_duration(item.get('duration', '')),
                "views": item.get('viewCount', {}).get('short', 'N/A'),
                "likes": item.get('accessibility', {}).get('likes', 'N/A') if item.get('accessibility') else 'N/A',
                "comments": 'N/A'
            })
        return result if result else {"error": "No videos found for the provided query."}
    except Exception as e:
        LOGGER.error(f"Error fetching YouTube search data for {query}: {str(e)}")
        return {"error": "Failed to fetch search data."}

@router.get("/dl")
async def download(url: str = ""):
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing 'url' parameter.",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackzs"
            }
        )
    video_id = extract_video_id(url)
    if not video_id:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid YouTube URL.",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackzs"
            }
        )
    standard_url = f"https://www.youtube.com/watch?v={video_id}"
    youtube_data = await fetch_youtube_details(video_id)
    if "error" in youtube_data:
        youtube_data = {
            "title": "Unavailable",
            "channel": "N/A",
            "description": "N/A",
            "tags": [],
            "imageUrl": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
            "duration": "N/A",
            "views": "N/A",
            "likes": "N/A",
            "comments": "N/A"
        }
    try:
        response = requests.post("https://www.clipto.com/api/youtube", json={"url": standard_url})
        ordered = OrderedDict()
        ordered["api_owner"] = "@ISmartCoder"
        ordered["api_updates"] = "t.me/abirxdhackzs"
        if response.status_code == 200:
            data = response.json()
            ordered["title"] = html.unescape(data.get("title", youtube_data["title"]))
            ordered["channel"] = youtube_data["channel"]
            ordered["description"] = youtube_data["description"]
            ordered["tags"] = youtube_data["tags"]
            ordered["thumbnail"] = data.get("thumbnail", youtube_data["imageUrl"])
            ordered["thumbnail_url"] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            ordered["url"] = data.get("url", standard_url)
            ordered["duration"] = youtube_data["duration"]
            ordered["views"] = youtube_data["views"]
            ordered["likes"] = youtube_data["likes"]
            ordered["comments"] = youtube_data["comments"]
            for key, value in data.items():
                if key not in ordered:
                    ordered[key] = value
        else:
            ordered["title"] = youtube_data["title"]
            ordered["channel"] = youtube_data["channel"]
            ordered["description"] = youtube_data["description"]
            ordered["tags"] = youtube_data["tags"]
            ordered["thumbnail"] = youtube_data["imageUrl"]
            ordered["thumbnail_url"] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
            ordered["url"] = standard_url
            ordered["duration"] = youtube_data["duration"]
            ordered["views"] = youtube_data["views"]
            ordered["likes"] = youtube_data["likes"]
            ordered["comments"] = youtube_data["comments"]
            ordered["error"] = "Failed to fetch download URL from Clipto API."
            return JSONResponse(content=dict(ordered), status_code=500)
        return JSONResponse(content=dict(ordered))
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching Clipto API for {video_id}: {str(e)}")
        ordered = OrderedDict()
        ordered["api_owner"] = "@ISmartCoder"
        ordered["api_updates"] = "t.me/abirxdhackzs"
        ordered["title"] = youtube_data["title"]
        ordered["channel"] = youtube_data["channel"]
        ordered["description"] = youtube_data["description"]
        ordered["tags"] = youtube_data["tags"]
        ordered["thumbnail"] = youtube_data["imageUrl"]
        ordered["thumbnail_url"] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        ordered["url"] = standard_url
        ordered["duration"] = youtube_data["duration"]
        ordered["views"] = youtube_data["views"]
        ordered["likes"] = youtube_data["likes"]
        ordered["comments"] = youtube_data["comments"]
        ordered["error"] = "Something went wrong. Please contact @ISmartCoder and report the bug."
        return JSONResponse(content=dict(ordered), status_code=500)

@router.get("/search")
async def search(query: str = ""):
    if not query:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing 'query' parameter.",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackzs"
            }
        )
    search_data = await fetch_youtube_search(query)
    if "error" in search_data:
        return JSONResponse(
            status_code=500,
            content={
                "error": search_data["error"],
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackzs"
            }
        )
    ordered = OrderedDict()
    ordered["api_owner"] = "@ISmartCoder"
    ordered["api_updates"] = "t.me/abirxdhackzs"
    ordered["result"] = search_data
    return JSONResponse(content=dict(ordered))