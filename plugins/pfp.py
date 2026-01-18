from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime
from urllib.parse import urlparse
from utils import LOGGER

router = APIRouter(prefix="/pfp")

ALLOWED_DOMAINS = ['www.facebook.com', 'm.facebook.com', 'facebook.com']
REQUEST_TIMEOUT = 30
MAX_RETRIES = 2

class FacebookProfileScraper:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'Dnt': '1'
        }
        
    def validate_url(self, url):
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ['http', 'https']:
                return False
            if parsed.netloc not in ALLOWED_DOMAINS:
                return False
            if any(char in url for char in ['<', '>', '"', "'"]):
                return False
            return True
        except Exception as e:
            LOGGER.error(f"URL validation error: {e}")
            return False
        
    def initialize_session(self):
        try:
            init_url = 'https://www.facebook.com/'
            response = self.session.get(
                init_url, 
                headers=self.headers, 
                timeout=REQUEST_TIMEOUT, 
                allow_redirects=True
            )
            return response.status_code == 200
        except Exception as e:
            LOGGER.error(f"Session initialization error: {e}")
            return False
    
    def normalize_profile_url(self, url):
        if not self.validate_url(url):
            return None
            
        if '/share/' in url:
            try:
                response = self.session.get(
                    url, 
                    headers=self.headers, 
                    timeout=REQUEST_TIMEOUT, 
                    allow_redirects=True
                )
                url = response.url
            except Exception as e:
                LOGGER.error(f"Failed to resolve share link: {e}")
                return None
        
        if 'm.facebook.com' in url:
            url = url.replace('m.facebook.com', 'www.facebook.com')
        elif 'facebook.com' in url and 'www.' not in url:
            url = url.replace('facebook.com', 'www.facebook.com')
        
        parsed = urlparse(url)
        if parsed.netloc not in ALLOWED_DOMAINS:
            return None
            
        return url
    
    def is_valid_image_url(self, url):
        if not url or not isinstance(url, str):
            return False
        
        if len(url) > 2000:
            return False
        
        invalid_extensions = ['.js', '.css', '.ico', '.json', '.xml', '.txt', '.html']
        for ext in invalid_extensions:
            if url.lower().endswith(ext):
                return False
        
        if '/rsrc.php/' in url and not any(x in url.lower() for x in ['.jpg', '.png', '.webp', '.jpeg', 'image']):
            return False
        
        image_indicators = [
            '.jpg', '.jpeg', '.png', '.webp', '.gif', 
            'photo', 'picture', 'image', '/t39.', '/t1.',
            'fbcdn.net', 'scontent'
        ]
        
        return any(indicator in url.lower() for indicator in image_indicators)
    
    def clean_url(self, url):
        url = url.replace('&amp;', '&')
        url = url.replace('&lt;', '<').replace('&gt;', '>')
        url = url.replace('&quot;', '"')
        url = url.replace('&#039;', "'")
        url = url.replace('\\/', '/')
        url = url.replace('\\"', '"')
        return url.strip()
    
    def sanitize_url(self, url):
        url = self.clean_url(url)
        url = url.split('"')[0].split("'")[0].split('>')[0].split('<')[0]
        url = url.split('\\')[0]
        url = url.strip()
        return url
    
    def get_profile_page(self, profile_url):
        try:
            normalized_url = self.normalize_profile_url(profile_url)
            if not normalized_url:
                return None
            
            self.headers['Referer'] = 'https://www.facebook.com/'
            
            for attempt in range(MAX_RETRIES):
                try:
                    response = self.session.get(
                        normalized_url, 
                        headers=self.headers, 
                        timeout=REQUEST_TIMEOUT, 
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        return response.text
                    elif response.status_code == 429:
                        LOGGER.warning(f"Rate limited on attempt {attempt + 1}")
                        time.sleep(2 ** attempt)
                    else:
                        LOGGER.error(f"HTTP {response.status_code} on attempt {attempt + 1}")
                        
                except requests.exceptions.Timeout:
                    LOGGER.error(f"Timeout on attempt {attempt + 1}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(1)
                        
            return None
                
        except Exception as e:
            LOGGER.error(f"Error fetching profile page: {e}")
            return None
    
    def get_image_size_score(self, url):
        size_patterns = [
            (r's(\d+)x(\d+)', 1),
            (r'p(\d+)x(\d+)', 1),
            (r'ctp=s(\d+)x(\d+)', 1)
        ]
        
        for pattern, group in size_patterns:
            match = re.search(pattern, url)
            if match:
                return int(match.group(group))
        
        if 's40x40' in url or 'cp0_dst' in url:
            return 40
        if 's160x160' in url:
            return 160
        if 's320x320' in url:
            return 320
        if 's480x480' in url:
            return 480
        if 's720x720' in url:
            return 720
        if 's960x960' in url:
            return 960
        
        if '?' not in url or 'stp=' not in url:
            return 9999
        
        return 500
    
    def extract_image_id(self, url):
        id_match = re.search(r'/(\d+)_(\d+)_(\d+)_[on]\.jpg', url)
        if id_match:
            return id_match.group(2)
        return None
    
    def extract_image_urls(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        
        images = {
            'profile_picture': None,
            'profile_picture_hd': None,
            'cover_photo': None,
            'cover_photo_hd': None,
            'photo_images': [],
            'all_images': set()
        }
        
        img_tags = soup.find_all('img', limit=500)
        
        for img in img_tags:
            src = img.get('src', '')
            if src and self.is_valid_image_url(src):
                src = self.sanitize_url(src)
                if src and len(src) < 2000:
                    images['all_images'].add(src)
        
        page_text = str(soup)
        
        url_patterns = [
            r'https://scontent[^"\'\\<>\s]+\.fbcdn\.net[^"\'\\<>\s]+\.(?:jpg|jpeg|png|webp)[^"\'\\<>\s]*',
            r'"(https://scontent[^"]+\.fbcdn\.net[^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        ]
        
        for pattern in url_patterns:
            found_urls = re.findall(pattern, page_text, re.IGNORECASE)
            for url in found_urls:
                if isinstance(url, tuple):
                    url = url[0] if url else ''
                
                url = self.sanitize_url(url)
                
                if url and self.is_valid_image_url(url) and len(url) < 2000 and 'fbcdn.net' in url:
                    images['all_images'].add(url)
        
        profile_variants = {}
        cover_variants = {}
        photo_candidates = []
        
        for img_url in images['all_images']:
            img_lower = img_url.lower()
            img_id = self.extract_image_id(img_url)
            
            is_profile_type = '/t39.30808-1/' in img_url or '3ab345' in img_url or '1d2534' in img_url
            is_cover_type = '/t39.30808-6/' in img_url
            
            size_score = self.get_image_size_score(img_url)
            
            if is_profile_type and img_id:
                if img_id not in profile_variants:
                    profile_variants[img_id] = []
                profile_variants[img_id].append((size_score, img_url))
            
            if is_cover_type and img_id:
                if img_id not in cover_variants:
                    cover_variants[img_id] = []
                cover_variants[img_id].append((size_score, img_url))
            
            if is_cover_type and size_score >= 320:
                photo_candidates.append((size_score, img_url))
        
        if profile_variants:
            largest_profile_id = max(profile_variants.keys(), 
                                    key=lambda k: max(v[0] for v in profile_variants[k]))
            profile_versions = sorted(profile_variants[largest_profile_id], 
                                     key=lambda x: x[0], reverse=True)
            
            images['profile_picture_hd'] = profile_versions[0][1]
            images['profile_picture'] = profile_versions[0][1]
        
        if cover_variants:
            largest_cover_id = max(cover_variants.keys(), 
                                  key=lambda k: max(v[0] for v in cover_variants[k]))
            cover_versions = sorted(cover_variants[largest_cover_id], 
                                   key=lambda x: x[0], reverse=True)
            
            images['cover_photo_hd'] = cover_versions[0][1]
            images['cover_photo'] = cover_versions[0][1]
        
        photo_candidates.sort(reverse=True, key=lambda x: x[0])
        seen_ids = set()
        unique_photos = []
        
        for score, url in photo_candidates:
            img_id = self.extract_image_id(url)
            if img_id and img_id not in seen_ids:
                seen_ids.add(img_id)
                unique_photos.append(url)
                if len(unique_photos) >= 10:
                    break
        
        images['photo_images'] = unique_photos
        images['all_images'] = list(images['all_images'])
        
        return images
    
    def scrape_profile(self, profile_url):
        if not self.validate_url(profile_url):
            LOGGER.error(f"Invalid URL provided: {profile_url}")
            return None
            
        if not self.initialize_session():
            return None
        
        html_content = self.get_profile_page(profile_url)
        
        if not html_content:
            return None
        
        images = self.extract_image_urls(html_content)
        
        return images

@router.get("/all")
async def get_all_images(url: str = None):
    request_start = time.time()
    
    if not url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "No URL provided",
                "message": "Please provide a Facebook profile URL using ?url=parameter",
                "example": "/pfp/all?url=https://www.facebook.com/username",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz",
                "time_taken": f"{time.time() - request_start:.2f}s"
            }
        )
    
    profile_url = url.strip()
    
    if 'facebook.com' not in profile_url:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid URL",
                "message": "Please provide a valid Facebook profile URL",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz",
                "time_taken": f"{time.time() - request_start:.2f}s"
            }
        )
    
    LOGGER.info(f"Processing all images request: {profile_url}")
    
    try:
        scraper = FacebookProfileScraper()
        result = scraper.scrape_profile(profile_url)
        
        if result:
            response_data = {
                "success": True,
                "profile_picture": {
                    "standard": result['profile_picture'],
                    "hd": result['profile_picture_hd']
                },
                "cover_photo": {
                    "standard": result['cover_photo'],
                    "hd": result['cover_photo_hd']
                },
                "photos": result['photo_images'],
                "all_images": result['all_images'],
                "total_count": len(result['all_images']),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz",
                "time_taken": f"{time.time() - request_start:.2f}s"
            }
            return JSONResponse(content=response_data)
        else:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Failed to scrape profile",
                    "message": "Could not extract data from the provided URL",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz",
                    "time_taken": f"{time.time() - request_start:.2f}s"
                }
            )
            
    except Exception as e:
        LOGGER.error(f"Error processing request: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Processing failed",
                "message": "Unable to process the request",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz",
                "time_taken": f"{time.time() - request_start:.2f}s"
            }
        )