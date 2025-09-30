from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import time
import re
from collections import OrderedDict

router = APIRouter(prefix="/thrd")

def get_threads_info(url: str):
    api_url = "https://api.threadsphotodownloader.com/v2/media"
    params = {"url": url}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://sssthreads.pro/",
        "Origin": "https://sssthreads.pro",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(api_url, params=params, headers=headers, timeout=30)
        data = resp.content
        enc = resp.headers.get("content-encoding", "").lower().strip()
        try:
            if enc == "zstd":
                import zstandard
                dctx = zstandard.ZstdDecompressor()
                data = dctx.decompress(data, max_output_size=20000000)
            elif enc == "gzip":
                import gzip
                data = gzip.decompress(data)
            elif enc == "br":
                import brotli
                data = brotli.decompress(data)
            elif enc == "deflate":
                import zlib
                data = zlib.decompress(data)
        except Exception:
            data = resp.content
        import json
        return json.loads(data.decode("utf-8", "ignore"))
    except Exception as e:
        return {"error": str(e)}

def get_twitter_info(url: str):
    api_url = f"https://twitsave.com/info?url={url}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://twitsave.com/",
        "Origin": "https://twitsave.com",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        resp = requests.get(api_url, headers=headers, timeout=30)
        soup = BeautifulSoup(resp.text, "html.parser")
        result = {}

        video_section = soup.find_all("div", class_="origin-top-right")
        video_urls = []
        if video_section:
            video_links = video_section[0].find_all("a")
            video_urls = [a.get("href") for a in video_links if a.get("href")]
        result["video_urls"] = video_urls

        name_section = soup.find_all("div", class_="leading-tight")
        title = None
        if name_section:
            name_ps = name_section[0].find_all("p", class_="m-2")
            if name_ps:
                raw_name = name_ps[0].text
                title = re.sub(r"[^a-zA-Z0-9]+", " ", raw_name).strip()
        result["title"] = title

        thumb_section = soup.find_all("img", class_="rounded-lg")
        thumbnail_urls = [img.get("src") for img in thumb_section if img.get("src")]
        result["thumbnail_urls"] = thumbnail_urls

        return result
    except Exception as e:
        return {"error": str(e)}

@router.get("/thd")
async def threads_dl(url: str = Query(..., description="Threads url")):
    start_time = time.time()
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                'error': 'Please Provide A Valid URL For Threads ❌',
                'api_owner': '@abirxdhack',
                'api_updates': 't.me/abirxdhackz'
            }
        )
    data = get_threads_info(url)
    if not data or ("error" in data and data["error"]):
        return JSONResponse(
            status_code=404,
            content={
                'error': f'Error fetching Threads info: {data.get("error") if isinstance(data, dict) else "Unknown"}',
                'api_owner': '@abirxdhack',
                'api_updates': 't.me/abirxdhackz'
            }
        )
    time_taken = f"{time.time() - start_time:.2f} seconds"
    response = OrderedDict()
    response["input_url"] = url
    response["time_taken"] = time_taken
    response["api_owner"] = "@abirxdhack"
    response["api_updates"] = "t.me/abirxdhackz"
    response["api"] = "abirxdhack Threads Scraper"
    response["results"] = data
    return JSONResponse(content=dict(response))

@router.get("/twit")
async def twitter_dl(url: str = Query(..., description="Twitter/X url")):
    start_time = time.time()
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                'error': 'Please Provide A Valid URL For Twitter ❌',
                'api_owner': '@abirxdhack',
                'api_updates': 't.me/abirxdhackz'
            }
        )
    data = get_twitter_info(url)
    if not data or ("error" in data and data["error"]):
        return JSONResponse(
            status_code=404,
            content={
                'error': f'Error fetching Twitter info: {data.get("error") if isinstance(data, dict) else "Unknown"}',
                'api_owner': '@abirxdhack',
                'api_updates': 't.me/abirxdhackz'
            }
        )
    time_taken = f"{time.time() - start_time:.2f} seconds"
    response = OrderedDict()
    response["input_url"] = url
    response["time_taken"] = time_taken
    response["api_owner"] = "@abirxdhack"
    response["api_updates"] = "t.me/abirxdhackz"
    response["api"] = "abirxdhack Twitter Scraper"
    response["results"] = data
    return JSONResponse(content=dict(response))