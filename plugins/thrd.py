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

def extract_csrf_token(html):
    m = re.search(r'<meta name="csrf-token" content="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    if m:
        return m.group(1)
    m = re.search(r'_token["\']?\s*[:=]\s*["\']([^"\']+)', html)
    if m:
        return m.group(1)
    return ""

def get_twitter_info(url: str):
    try:
        session = requests.Session()
        main_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "sec-ch-ua-platform": '"Android"',
            "sec-ch-ua": '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        main_resp = session.get("https://savetwitter.net/en4", headers=main_headers, timeout=30)
        csrf_token = extract_csrf_token(main_resp.text)
        time.sleep(1)
        payload = {
            "q": url,
            "lang": "en",
            "cftoken": ""
        }
        if csrf_token:
            payload["_token"] = csrf_token
        api_headers = {
            "User-Agent": main_headers["User-Agent"],
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://savetwitter.net",
            "referer": "https://savetwitter.net/en4",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }
        if csrf_token:
            api_headers["X-CSRF-TOKEN"] = csrf_token
            api_headers["X-Requested-With"] = "XMLHttpRequest"
        resp = session.post("https://savetwitter.net/api/ajaxSearch", data=payload, headers=api_headers, timeout=30)
        data = resp.json()
        if data.get("status") != "ok":
            return {"error": "Invalid response from source"}
        html = data.get("data", "")
        title_m = re.search(r"<h3>(.*?)</h3>", html)
        duration_m = re.search(r"<p>(\d+:\d+)</p>", html)
        thumb_m = re.search(r'<img src="(https://pbs\.twimg\.com/[^"]+)"', html)
        videos = []
        for m in re.finditer(r'href="([^"]+)" rel="nofollow" class="tw-button-dl button dl-success"><i class="icon icon-download"></i> Download MP4 \((\d+p)\)', html):
            videos.append({
                "quality": m.group(2),
                "url": m.group(1),
                "type": "video/mp4"
            })
        photo_m = re.search(r'href="([^"]+)" rel="nofollow" class="tw-button-dl button dl-success"><i class="icon icon-download"></i> Download Photo', html)
        audio_m = re.search(r'data-audioUrl="([^"]+)"', html)
        media_m = re.search(r'data-mediaId="(\d+)"', html)
        twitter_m = re.search(r'id="TwitterId" value="(\d+)"', html)
        return {
            "tweet_url": url,
            "twitter_id": twitter_m.group(1) if twitter_m else None,
            "title": title_m.group(1).strip() if title_m else None,
            "duration": duration_m.group(1) if duration_m else None,
            "thumbnail": thumb_m.group(1) if thumb_m else None,
            "videos": videos,
            "photo": photo_m.group(1) if photo_m else None,
            "audio": audio_m.group(1) if audio_m else None,
            "media_id": media_m.group(1) if media_m else None,
            "csrf_token_used": csrf_token if csrf_token else "none",
            "timestamp": int(time.time())
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/thd")
async def threads_dl(url: str = Query(...)):
    start = time.time()
    data = get_threads_info(url)
    if not data or "error" in data:
        return JSONResponse(status_code=404, content={"error": "Failed to fetch Threads data"})
    res = OrderedDict()
    res["input_url"] = url
    res["time_taken"] = f"{time.time() - start:.2f}s"
    res["api_owner"] = "@abirxdhack"
    res["api_updates"] = "t.me/abirxdhackz"
    res["api"] = "abirxdhack Threads Scraper"
    res["results"] = data
    return JSONResponse(content=dict(res))

@router.get("/twit")
async def twitter_dl(url: str = Query(...)):
    start = time.time()
    data = get_twitter_info(url)
    if not data or "error" in data:
        return JSONResponse(status_code=404, content={"error": "Failed to fetch Twitter data"})
    res = OrderedDict()
    res["input_url"] = url
    res["time_taken"] = f"{time.time() - start:.2f}s"
    res["api_owner"] = "@abirxdhack"
    res["api_updates"] = "t.me/abirxdhackz"
    res["api"] = "abirxdhack Twitter Scraper"
    res["results"] = data
    return JSONResponse(content=dict(res))