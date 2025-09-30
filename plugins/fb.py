#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import cloudscraper
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import requests
from utils import LOGGER

router = APIRouter(prefix="/fb")

def get_experts_tool_links(fb_url):
    try:
        payload = {'url': fb_url}
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
        }
        response = requests.post('https://www.expertstool.com/converter.php', data=payload, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        downloads = {'links': [], 'thumbnail': None}
        video_divs = soup.find_all('div', class_='col-md-8 col-md-offset-2')
        for div in video_divs:
            video_link = div.find('a', href=True, class_='btn btn-primary btn-sm btn-block', style='background-color: green;')
            if video_link and 'Download VideO File' in video_link.text:
                quality = 'SD' if '[SD]' in video_link.text else 'HD' if '[HD]' in video_link.text else 'Unknown'
                downloads['links'].append({'quality': quality, 'url': video_link['href']})
        image_divs = soup.find_all('div', class_='col-md-4 col-md-offset-4')
        for div in image_divs:
            image_link = div.find('a', href=True, class_='btn btn-primary btn-sm btn-block')
            if image_link and 'Download image' in image_link.text:
                downloads['thumbnail'] = image_link['href']
        if not downloads['links'] and not downloads['thumbnail']:
            return {"error": "No downloadable content found from Experts Tool."}
        return downloads
    except Exception as e:
        LOGGER.error(f"Failed to fetch from Experts Tool: {str(e)}")
        return {"error": f"Failed to fetch from Experts Tool: {str(e)}"}

def get_savef_links(fb_url):
    api_url = "https://savef.app/api/ajaxSearch"
    payload = {
        "p": "home",
        "q": fb_url,
        "lang": "en",
        "web": "savef.app",
        "v": "v2",
        "w": ""
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://savef.app",
        "Referer": "https://savef.app/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    }
    try:
        response = requests.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        html_content = response.json().get("data", "")
        soup = BeautifulSoup(html_content, "html.parser")
        download_links = []
        for link in soup.select("a.download-link-fb"):
            quality = link.find_previous("td", class_="video-quality").text.strip()
            normalized_quality = "HD" if "720p" in quality else "SD"
            href = link["href"]
            download_links.append({'quality': normalized_quality, 'url': href})
        if not download_links:
            return {"error": "No downloadable video links found from savef.app."}
        return {
            "links": download_links,
            "title": "Unknown Title",
            "thumbnail": "Not available"
        }
    except Exception as e:
        LOGGER.error(f"Failed to fetch from savef.app: {str(e)}")
        return {"error": f"Failed to fetch from savef.app: {str(e)}"}

def get_fdown_links(fb_url):
    try:
        base_url = "https://fdown.net/"
        session = cloudscraper.create_scraper()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': base_url,
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'DNT': '1'
        }
        response = session.get(base_url, headers=headers, timeout=5)
        response.raise_for_status()
        form_data = {'URLz': fb_url}
        action_url = urljoin(base_url, "download.php")
        post_response = session.post(action_url, data=form_data, headers=headers, timeout=5)
        post_response.raise_for_status()
        soup = BeautifulSoup(post_response.text, 'html.parser')
        error_div = soup.find('div', class_='alert-danger')
        if error_div:
            return {"error": "Unknown error from FDown.net"}
        title = None
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        else:
            heading = soup.find(['h1', 'h2'])
            if heading:
                title = heading.get_text(strip=True)
        if title and "FDown" in title:
            title = title.replace(" - FDown", "").strip()
        if not title:
            title = "Unknown Title"
        download_links = []
        sd_link = soup.find('a', id='sdlink')
        hd_link = soup.find('a', id='hdlink')
        if sd_link and sd_link.get('href'):
            download_links.append({'quality': 'SD', 'url': sd_link['href']})
        if hd_link and hd_link.get('href'):
            download_links.append({'quality': 'HD', 'url': hd_link['href']})
        if not download_links:
            link_pattern = re.compile(r'(https?://[^\s\'"]+\.mp4[^\'"\s]*)')
            matches = link_pattern.findall(post_response.text)
            for i, link in enumerate(set(matches), 1):
                download_links.append({'quality': f'Quality_{i}', 'url': link})
        if not download_links:
            return {"error": "No downloadable video links found from FDown.net."}
        return {
            "links": download_links,
            "title": title,
            "thumbnail": "Not available"
        }
    except Exception as e:
        LOGGER.error(f"Failed to fetch from FDown.net: {str(e)}")
        return {"error": f"Failed to fetch from FDown.net: {str(e)}"}

def get_download_links(fb_url):
    results = []
    experts_result = get_experts_tool_links(fb_url)
    if not isinstance(experts_result, dict) or "error" not in experts_result:
        results.append(experts_result)
    fdown_result = get_fdown_links(fb_url)
    if not isinstance(fdown_result, dict) or "error" not in fdown_result:
        results.append(fdown_result)
    savef_result = get_savef_links(fb_url)
    if not isinstance(savef_result, dict) or "error" not in savef_result:
        results.append(savef_result)
    if not results:
        return {"error": "All sources failed to retrieve download links."}
    combined_links = []
    title = "Unknown Title"
    thumbnail = "Not available"
    for result in results:
        if result.get('links'):
            for link in result['links']:
                if not any(l['url'] == link['url'] for l in combined_links):
                    combined_links.append(link)
        if result.get('title') and result['title'] != "Unknown Title":
            title = result['title']
        if result.get('thumbnail') and result['thumbnail'] != "Not available":
            thumbnail = result['thumbnail']
    if not combined_links:
        return {"error": "No valid download links found from any source."}
    return {
        "links": combined_links,
        "title": title,
        "thumbnail": thumbnail,
        "api_owner": "@ISmartCoder",
        "api_updates": "t.me/abirxdhackz"
    }

@router.get("/dl")
async def download_links(url: str = ""):
    try:
        if not url:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing 'url' query parameter",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        result = get_download_links(url)
        if "error" in result:
            return JSONResponse(
                status_code=400,
                content={
                    "error": result["error"],
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(content=result)
    except Exception as e:
        LOGGER.error(f"Server error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Server error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )