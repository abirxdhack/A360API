from fastapi import APIRouter
from fastapi.responses import JSONResponse
import cloudscraper

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
        scraper = cloudscraper.create_scraper(
            browser={"browser": "chrome", "platform": "android", "mobile": True},
            delay=15
        )

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://ytdownload.in",
            "Referer": "https://ytdownload.in/",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36",
            "sec-ch-ua": '"Chromium";v="141", "Not;A=Brand";v="99", "Google Chrome";v="141"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"'
        }

        scraper.get("https://ytdownload.in", headers=headers, timeout=30)

        payload = {
            "url": url.strip(),
            "format": "mp4",
            "quality": "1080p"
        }

        resp = scraper.post(
            "https://ytdownload.in/api/allinonedownload",
            json=payload,
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

        data = resp.json()
        if not data or "responseFinal" not in data:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Video not found or private",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )

        result = data["responseFinal"]
        links = []
        title = result.get("title") or "Facebook Video"
        thumbnail = result.get("thumbnails") or result.get("thumbnail")

        if result.get("videoUrl"):
            links.append({"quality": "HD", "url": result["videoUrl"]})

        if result.get("formats"):
            for fmt in result["formats"]:
                if fmt.get("url"):
                    q = fmt.get("resolution") or fmt.get("qualityLabel") or "Unknown"
                    links.append({"quality": q, "url": fmt["url"]})

        if result.get("downloadUrl"):
            links.append({"quality": "SD", "url": result["downloadUrl"]})

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