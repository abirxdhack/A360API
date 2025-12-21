from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from urllib.parse import urlparse
import hashlib
import re
import time
from datetime import datetime
from collections import OrderedDict

from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL, BASE_URL
from utils import LOGGER

router = APIRouter(prefix="/shortner")

client = AsyncIOMotorClient(MONGO_URL)
db = client.url_shortener
collection = db.urls

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def is_valid_slug(slug: str) -> bool:
    return bool(re.fullmatch(r'[A-Za-z0-9_-]+', slug)) and 3 <= len(slug) <= 50

def generate_short_code(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:6].upper()

@router.get("/shorten")
async def shorten_url(url: str = Query(...), slug: str | None = None):
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    long_url = url

    start_time = time.time()

    if not is_valid_url(long_url):
        raise HTTPException(status_code=400, detail="Invalid URL provided.")

    if slug:
        short_code = slug.upper()
        if not is_valid_slug(short_code):
            raise HTTPException(status_code=400, detail="Slug must be 3-50 characters and contain only letters, numbers, hyphens, or underscores.")
    else:
        short_code = generate_short_code(long_url)

    existing = await collection.find_one({"short_code": short_code})
    if existing:
        if slug and existing["long_url"] != long_url:
            raise HTTPException(status_code=409, detail="Custom slug already in use.")
    else:
        await collection.insert_one({
            "short_code": short_code,
            "long_url": long_url,
            "clicks": 0,
            "created_at": datetime.utcnow(),
            "last_clicked": None
        })

    short_url = f"{BASE_URL}/shortner/{short_code}"
    time_taken = f"{time.time() - start_time:.2f}s"

    response = OrderedDict()
    response["success"] = True
    response["short_url"] = short_url
    response["original_url"] = long_url
    response["short_code"] = short_code
    response["custom_slug"] = bool(slug)
    response["time_taken"] = time_taken
    response["developer"] = "@ISmartCoder"
    response["updates_channel"] = "t.me/abirxdhackz"
    response["api"] = "A360 URL Shortener"

    return JSONResponse(content=dict(response))

@router.get("/{short_code}")
async def redirect(short_code: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', short_code):
        raise HTTPException(status_code=400, detail="Invalid short code.")

    short_code = short_code.upper()
    result = await collection.find_one_and_update(
        {"short_code": short_code},
        {"$inc": {"clicks": 1}, "$set": {"last_clicked": datetime.utcnow()}},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="Short URL not found.")

    return RedirectResponse(url=result["long_url"], status_code=301)

@router.get("/stats/{short_code}")
async def get_stats(short_code: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', short_code):
        raise HTTPException(status_code=400, detail="Invalid short code.")

    short_code = short_code.upper()
    doc = await collection.find_one({"short_code": short_code})

    if not doc:
        raise HTTPException(status_code=404, detail="Short URL not found.")

    last_clicked = doc["last_clicked"].strftime("%Y-%m-%d %H:%M:%S UTC") if doc["last_clicked"] else "Never"

    response = OrderedDict()
    response["short_code"] = doc["short_code"]
    response["short_url"] = f"{BASE_URL}/shortner/{doc['short_code']}"
    response["original_url"] = doc["long_url"]
    response["clicks"] = doc["clicks"]
    response["created_at"] = doc["created_at"].strftime("%Y-%m-%d %H:%M:%S UTC")
    response["last_clicked"] = last_clicked
    response["developer"] = "@ISmartCoder"
    response["updates_channel"] = "t.me/abirxdhackz"

    return JSONResponse(content=dict(response))

@router.get("/delete/{short_code}")
async def delete_short_url(short_code: str):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', short_code):
        raise HTTPException(status_code=400, detail="Invalid short code.")

    short_code = short_code.upper()
    result = await collection.delete_one({"short_code": short_code})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Short URL not found or already deleted.")

    return JSONResponse(content={
        "success": True,
        "message": "Short URL deleted successfully",
        "short_code": short_code,
        "developer": "@ISmartCoder",
        "updates_channel": "t.me/abirxdhackz"
    })