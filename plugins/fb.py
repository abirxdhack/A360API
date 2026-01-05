from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import re

router = APIRouter(prefix="/fb", tags=["Facebook Downloader"])

@router.get("/dl")
async def fb_downloader(url: str = ""):
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing 'url' query parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

    if not any(x in url for x in ["facebook.com", "fb.watch", "fb.com"]):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Only Facebook URLs are supported!",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "cache-control": "max-age=0",
            "sec-ch-ua": '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand)";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "origin": "https://fdown.net",
            "upgrade-insecure-requests": "1",
            "x-requested-with": "mark.via.gp",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
            "referer": "https://fdown.net/",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "priority": "u=0, i"
        }

        payload = {
            "URLz": url.strip()
        }

        resp = requests.post(
            "https://fdown.net/download.php",
            data=payload,
            headers=headers,
            timeout=45
        )

        if resp.status_code != 200:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "Third-party service temporarily down",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        html = resp.text
        soup = BeautifulSoup(html, 'html.parser')

        title = "Facebook Video"
        title_elem = soup.find('div', class_='lib-row lib-header')
        if title_elem:
            title_text = title_elem.get_text(strip=True)
            if title_text and title_text != "No video title":
                title = title_text

        thumbnail = None
        img_elem = soup.find('img', class_='lib-img-show')
        if img_elem and img_elem.get('src'):
            thumb_src = img_elem['src']
            if 'no-thumbnail-fbdown.png' not in thumb_src:
                thumbnail = thumb_src

        links = []
        download_links = soup.find_all('a', href=True)
        
        for link in download_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            if 'download' in href.lower() or 'fbcdn.net' in href:
                quality = "Unknown"
                
                if 'hd' in text.lower() or 'high' in text.lower():
                    quality = "HD"
                elif 'sd' in text.lower() or 'normal' in text.lower() or 'low' in text.lower():
                    quality = "SD"
                elif text:
                    quality = text
                
                if href.startswith('http'):
                    links.append({"quality": quality, "url": href})

        seen = set()
        unique_links = []
        for item in links:
            if item["url"] not in seen:
                seen.add(item["url"])
                unique_links.append(item)

        if not unique_links:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No downloadable links found",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        return {
            "title": title,
            "thumbnail": thumbnail,
            "links": unique_links,
            "total_links": len(unique_links),
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Server error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )