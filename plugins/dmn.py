from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import cloudscraper
from bs4 import BeautifulSoup
from collections import OrderedDict
import time

from utils import LOGGER

router = APIRouter(prefix="/dmn")

class WhoisChecker:
    def __init__(self):
        LOGGER.info("Initializing WhoisChecker...")
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'android',
                'mobile': True
            }
        )
        self.base_url = "https://www.whois.com"
        self.session_cookie = None
        LOGGER.info("WhoisChecker initialized successfully")
        
    def get_session(self):
        LOGGER.info("Getting new session...")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.192 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
        }
        
        try:
            response = self.scraper.get(f"{self.base_url}/whois/", headers=headers)
            if 'whoissid' in response.cookies:
                self.session_cookie = response.cookies['whoissid']
                LOGGER.info("Session cookie obtained successfully")
            return True
        except Exception as e:
            LOGGER.error(f"Session error: {e}")
            return False
    
    def check_domain(self, domain):
        LOGGER.info(f"Checking domain: {domain}")
        
        if not self.session_cookie:
            LOGGER.info("No session cookie found, creating new session...")
            self.get_session()
        
        url = f"{self.base_url}/whois/{domain}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.192 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Referer': f'{self.base_url}/whois/',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8'
        }
        
        try:
            LOGGER.info(f"Sending request to: {url}")
            response = self.scraper.get(url, headers=headers)
            LOGGER.info(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                result = self.parse_whois_data(response.text, domain)
                LOGGER.info(f"Successfully parsed data for {domain}")
                return result
            else:
                LOGGER.error(f"HTTP error {response.status_code} for {domain}")
                return {'error': f'HTTP {response.status_code}'}
                
        except Exception as e:
            LOGGER.error(f"Exception while checking {domain}: {str(e)}")
            return {'error': str(e)}
    
    def parse_whois_data(self, html, domain):
        LOGGER.info(f"Parsing HTML data for {domain}")
        soup = BeautifulSoup(html, 'html.parser')
        data = OrderedDict()
        data['domain'] = domain
        
        available_section = soup.find('div', class_='section-avail')
        if available_section and 'is available!' in available_section.get_text():
            data['status'] = 'available'
            data['available'] = True
            LOGGER.info(f"{domain} is available")
            return data
        
        data['available'] = False
        LOGGER.info(f"{domain} is registered")
        
        whois_data = soup.find('div', class_='whois-data')
        if not whois_data:
            LOGGER.warning(f"No whois data found for {domain}")
            return data
        
        df_blocks = whois_data.find_all('div', class_='df-block')
        LOGGER.info(f"Found {len(df_blocks)} data blocks for {domain}")
        
        for block in df_blocks:
            heading = block.find('div', class_='df-heading')
            if not heading:
                continue
                
            heading_text = heading.get_text(strip=True)
            rows = block.find_all('div', class_='df-row')
            
            for row in rows:
                label_div = row.find('div', class_='df-label')
                value_div = row.find('div', class_='df-value')
                
                if label_div and value_div:
                    label = label_div.get_text(strip=True).replace(':', '').lower().replace(' ', '_')
                    
                    br_tags = value_div.find_all('br')
                    if br_tags:
                        values = []
                        for item in value_div.stripped_strings:
                            values.append(item)
                        value = values
                    else:
                        value = value_div.get_text(strip=True)
                    
                    data[label] = value
        
        LOGGER.info(f"Parsing completed for {domain}, found {len(data)} fields")
        return data

checker = WhoisChecker()

@router.get("")
async def whois_domain(domain: str = Query(..., description="Domain name to lookup")):
    start_time = time.time()
    LOGGER.info("=" * 60)
    LOGGER.info(f"New domain lookup request for: {domain}")
    LOGGER.info("=" * 60)
    
    if not domain:
        LOGGER.error("Domain parameter is missing")
        raise HTTPException(status_code=400, detail="Domain parameter is required")
    
    domain = domain.strip().lower()
    LOGGER.info(f"Processing domain: {domain}")
    
    try:
        LOGGER.info("Calling WhoisChecker...")
        result = checker.check_domain(domain)
        
        time_taken = f"{time.time() - start_time:.2f}s"
        
        response = OrderedDict()
        response.update(result)
        response["time_taken"] = time_taken
        response["api_owner"] = "@ISmartCoder"
        response["api_dev"] = "@abirxdhackz"
        response["source"] = "whois.com"
        
        LOGGER.info(f"Request completed successfully in {time_taken}")
        LOGGER.info(f"Domain availability: {result.get('available', 'unknown')}")
        LOGGER.info("=" * 60)
        
        return JSONResponse(content=dict(response))
        
    except Exception as e:
        time_taken = f"{time.time() - start_time:.2f}s"
        
        LOGGER.error(f"Error processing request: {str(e)}")
        LOGGER.error(f"Request failed after {time_taken}")
        LOGGER.info("=" * 60)
        
        raise HTTPException(status_code=500, detail=f"Failed to fetch whois data: {str(e)}")