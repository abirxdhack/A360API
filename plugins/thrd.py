from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
import requests
import json
import re
import time
import traceback
from collections import OrderedDict
from io import BytesIO

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

try:
    import brotli
    HAS_BROTLI = True
except ImportError:
    HAS_BROTLI = False

router = APIRouter(prefix="/thrd")

def decompress_response(response):
    content_encoding = response.headers.get('Content-Encoding', '').lower()
    
    if content_encoding == 'zstd':
        if not HAS_ZSTD:
            return response.text
        try:
            raw_content = response.content
            dctx = zstd.ZstdDecompressor()
            decompressed = dctx.decompress(raw_content, max_output_size=100*1024*1024)
            return decompressed.decode('utf-8', errors='replace')
        except Exception as e:
            try:
                raw_content = response.content
                dctx = zstd.ZstdDecompressor()
                with dctx.stream_reader(BytesIO(raw_content)) as reader:
                    decompressed = reader.read()
                return decompressed.decode('utf-8', errors='replace')
            except:
                return response.text
    elif content_encoding == 'br':
        if not HAS_BROTLI:
            return response.text
        try:
            decompressed = brotli.decompress(response.content)
            return decompressed.decode('utf-8')
        except:
            return response.text
    else:
        return response.text

def get_fresh_session():
    session = requests.Session()
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'upgrade-insecure-requests': '1',
        'priority': 'u=0, i'
    }
    
    try:
        response = session.get('https://threadster.app/', headers=headers, timeout=30)
        
        csrf_token = None
        for cookie in session.cookies:
            if cookie.name == '_csrf':
                csrf_token = cookie.value
                break
        
        return session, csrf_token
        
    except Exception as e:
        return None, None

def send_analytics(session, csrf_token):
    analytics_headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Content-Type': 'application/json',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'origin': 'https://threadster.app',
        'x-requested-with': 'mark.via.gp',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'priority': 'u=1, i'
    }
    
    payload1 = {
        "type": "event",
        "payload": {
            "website": "38cfaa2c-9fcc-4dc6-8325-aa645f714572",
            "screen": "427x953",
            "language": "en-GB",
            "title": "Downloads Threads Videos | Threads Video Download | Threadster",
            "hostname": "threadster.app",
            "url": "https://threadster.app/",
            "referrer": ""
        }
    }
    
    try:
        session.post(
            'https://analytics.aculix.xyz/api/send',
            data=json.dumps(payload1),
            headers=analytics_headers,
            timeout=30
        )
    except:
        pass
    
    try:
        payload2 = '{"n":"pageview","u":"https://threadster.app/","d":"threadster.app","r":null,"w":426}'
        analytics_headers2 = analytics_headers.copy()
        analytics_headers2['Content-Type'] = 'text/plain'
        
        session.post(
            'https://analytics.aculix.online/api/event',
            data=payload2,
            headers=analytics_headers2,
            timeout=30
        )
    except:
        pass

def get_threads_info(threads_url):
    download_headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'cache-control': 'max-age=0',
        'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?1',
        'sec-ch-ua-platform': '"Android"',
        'origin': 'null',
        'upgrade-insecure-requests': '1',
        'x-requested-with': 'mark.via.gp',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'priority': 'u=0, i'
    }
    
    try:
        session, csrf_token = get_fresh_session()
        
        if not session:
            return {"error": "Failed to initialize session"}
        
        send_analytics(session, csrf_token)
        
        payload = {
            'url': threads_url
        }
        
        response = session.post(
            'https://threadster.app/download',
            data=payload,
            headers=download_headers,
            timeout=60,
            stream=False
        )
        
        decompressed_text = decompress_response(response)
        
        video_links = re.findall(r'href="(https://downloads\.acxcdn\.com/threadster/video\?token=[^"]+)"', decompressed_text)
        image_links = re.findall(r'href="(https://downloads\.acxcdn\.com/threadster/image\?token=[^"]+)"', decompressed_text)
        
        username_match = re.search(r'<span>@([^<]+)</span>', decompressed_text)
        username = username_match.group(1) if username_match else None
        
        caption_match = re.search(r'<div class="download__item__caption__text">([^<]+)</div>', decompressed_text)
        caption = caption_match.group(1).strip() if caption_match else None
        
        resolution_info = re.findall(r'<td>([^<]+)</td>.*?href="([^"]+)"', decompressed_text, re.DOTALL)
        
        media_items = []
        
        for i, link in enumerate(video_links, 1):
            media_items.append({
                'type': 'video',
                'url': link,
                'index': i
            })
        
        for i, link in enumerate(image_links, 1):
            media_items.append({
                'type': 'image',
                'url': link,
                'index': i
            })
        
        resolutions = []
        if resolution_info:
            for res, link in resolution_info:
                resolutions.append({
                    'quality': res.strip(),
                    'url': link
                })
        
        result = {
            'username': username,
            'caption': caption,
            'media_count': len(media_items),
            'video_count': len(video_links),
            'image_count': len(image_links),
            'media': media_items,
            'resolutions': resolutions
        }
        
        return result
            
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