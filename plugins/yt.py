#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
import re
import html
from collections import OrderedDict
from utils import LOGGER
from config import YOUTUBE_API_KEY

router = APIRouter(prefix="/yt")

YOUTUBE_SEARCH_API_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_API_URL = "https://www.googleapis.com/youtube/v3/videos"

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

def parse_duration(duration):
    try:
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match:
            return "N/A"
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
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

def fetch_youtube_details(video_id):
    try:
        api_url = f"{YOUTUBE_VIDEOS_API_URL}?part=snippet,statistics,contentDetails&id={video_id}&key={YOUTUBE_API_KEY}"
        response = requests.get(api_url)
        if response.status_code != 200:
            LOGGER.error(f"YouTube API returned status {response.status_code} for video {video_id}")
            return {"error": "Failed to fetch YouTube video details."}
        data = response.json()
        if not data.get('items'):
            LOGGER.error(f"No video found for ID {video_id}")
            return {"error": "No video found for the provided ID."}
        video = data['items'][0]
        snippet = video['snippet']
        stats = video['statistics']
        content_details = video['contentDetails']
        return {
            "title": html.unescape(snippet.get('title', 'N/A')),
            "channel": html.unescape(snippet.get('channelTitle', 'N/A')),
            "description": html.unescape(snippet.get('description', 'N/A')),
            "tags": snippet.get('tags', []),
            "imageUrl": snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            "duration": parse_duration(content_details.get('duration', '')),
            "views": stats.get('viewCount', 'N/A'),
            "likes": stats.get('likeCount', 'N/A'),
            "comments": stats.get('commentCount', 'N/A')
        }
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching YouTube details for {video_id}: {str(e)}")
        return {"error": "Failed to fetch YouTube video details."}

def fetch_youtube_search(query):
    try:
        search_api_url = f"{YOUTUBE_SEARCH_API_URL}?part=snippet&q={requests.utils.quote(query)}&type=video&maxResults=10&key={YOUTUBE_API_KEY}"
        search_response = requests.get(search_api_url)
        if search_response.status_code != 200:
            LOGGER.error(f"YouTube Search API returned status {search_response.status_code} for query {query}")
            return {"error": "Failed to fetch search data."}
        search_data = search_response.json()
        video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
        if not video_ids:
            LOGGER.error(f"No videos found for query {query}")
            return {"error": "No videos found for the provided query."}
        videos_api_url = f"{YOUTUBE_VIDEOS_API_URL}?part=snippet,statistics,contentDetails&id={','.join(video_ids)}&key={YOUTUBE_API_KEY}"
        videos_response = requests.get(videos_api_url)
        if videos_response.status_code != 200:
            LOGGER.error(f"YouTube Videos API returned status {videos_response.status_code} for query {query}")
            return {"error": "Failed to fetch video details."}
        videos_data = videos_response.json()
        videos_map = {video['id']: video for video in videos_data.get('items', [])}
        result = []
        for item in search_data.get('items', []):
            video_id = item['id']['videoId']
            snippet = item['snippet']
            video = videos_map.get(video_id, {})
            content_details = video.get('contentDetails', {})
            stats = video.get('statistics', {})
            result.append({
                "title": html.unescape(snippet.get('title', 'N/A')),
                "channel": html.unescape(snippet.get('channelTitle', 'N/A')),
                "tags": video.get('snippet', {}).get('tags', []),
                "imageUrl": snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                "link": f"https://youtube.com/watch?v={video_id}",
                "duration": parse_duration(content_details.get('duration', '')),
                "views": stats.get('viewCount', 'N/A'),
                "likes": stats.get('likeCount', 'N/A'),
                "comments": stats.get('commentCount', 'N/A')
            })
        return result
    except requests.RequestException as e:
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
    youtube_data = fetch_youtube_details(video_id)
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
    search_data = fetch_youtube_search(query)
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
