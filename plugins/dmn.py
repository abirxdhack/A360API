from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import aiohttp
import time
from collections import OrderedDict

from utils import LOGGER

router = APIRouter(prefix="/dmn")

HEADERS = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 15; V2434 Build/AP3A.240905.015.A2_NN_V000L1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36",
    'Accept-Encoding': "gzip, deflate, br, zstd",
    'sec-ch-ua-platform': "\"Android\"",
    'sec-ch-ua': "\"Android WebView\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
    'sec-ch-ua-mobile': "?1",
    'origin': "https://client.rdap.org",
    'x-requested-with': "mark.via.gp",
    'sec-fetch-site': "cross-site",
    'sec-fetch-mode': "cors",
    'sec-fetch-dest': "empty",
    'referer': "https://client.rdap.org/",
    'accept-language': "en-GB,en-US;q=0.9,en;q=0.8",
    'priority': "u=1, i"
}

def get_rdap_url(domain: str) -> str:
    domain_upper = domain.upper()
    tld = domain.split('.')[-1].lower()
    
    rdap_servers = {
        'com': f"https://rdap.verisign.com/com/v1/domain/{domain}?jscard=1",
        'net': f"https://rdap.verisign.com/net/v1/domain/{domain}?jscard=1",
        'org': f"https://rdap.publicinterestregistry.org/rdap/domain/{domain}",
        'info': f"https://rdap.afilias-srs.net/rdap/afilias-info/domain/{domain}",
        'biz': f"https://rdap.afilias-srs.net/rdap/afilias-biz/domain/{domain}",
        'us': f"https://rdap.nic.us/domain/{domain}",
        'co': f"https://rdap.nic.co/domain/{domain}",
        'me': f"https://rdap.nic.me/domain/{domain}",
        'io': f"https://rdap.nic.io/domain/{domain}",
        'app': f"https://rdap.nic.google/rdap/domain/{domain}",
        'dev': f"https://rdap.nic.google/rdap/domain/{domain}",
        'page': f"https://rdap.nic.google/rdap/domain/{domain}",
    }
    
    return rdap_servers.get(tld, f"https://rdap.markmonitor.com/rdap/domain/{domain_upper}")

def parse_rdap_data(rdap_data: dict) -> dict:
    structured = {}
    
    structured['domain'] = rdap_data.get('ldhName') or rdap_data.get('name', '')
    
    events = rdap_data.get('events', [])
    for event in events:
        event_action = event.get('eventAction', '')
        event_date = event.get('eventDate', '')
        if event_action == 'registration':
            structured['registered_on'] = event_date
        elif event_action == 'expiration':
            structured['expires_on'] = event_date
        elif event_action == 'last changed':
            structured['updated_on'] = event_date
    
    structured['status'] = rdap_data.get('status', [])
    
    nameservers = rdap_data.get('nameservers', [])
    ns_list = []
    for ns in nameservers:
        ns_name = ns.get('ldhName', '')
        if ns_name:
            ns_list.append(ns_name.strip('.'))
    structured['name_servers'] = ns_list
    
    entities = rdap_data.get('entities', [])
    for entity in entities:
        roles = entity.get('roles', [])
        if 'registrar' in roles:
            vcards = entity.get('vcardArray', [])
            if len(vcards) > 1:
                for vcard in vcards[1]:
                    if isinstance(vcard, list) and len(vcard) > 0:
                        vcard_type = vcard[0]
                        if vcard_type == 'fn' and len(vcard) > 3:
                            structured['registrar'] = vcard[3]
                        elif vcard_type == 'email' and len(vcard) > 3:
                            if not structured.get('registrar_email'):
                                structured['registrar_email'] = vcard[3]
            
            public_ids = entity.get('publicIds', [])
            for pid in public_ids:
                if pid.get('type') == 'IANA Registrar ID':
                    structured['iana_id'] = pid.get('identifier', '')
    
    structured['registrar_abuse_email'] = None
    structured['registrar_abuse_phone'] = None
    structured['registrant_state'] = None
    structured['registrant_country'] = None
    
    return structured

@router.get("")
async def whois_domain(domain: str = Query(..., description="Domain name to lookup")):
    start_time = time.time()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")

    domain = domain.strip().lower()
    
    url = get_rdap_url(domain)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=20) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail="Failed to fetch RDAP data")
                rdap_data = await resp.json()
    except Exception as e:
        LOGGER.error(f"Failed to fetch RDAP for {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch RDAP data")

    structured = parse_rdap_data(rdap_data)

    time_taken = f"{time.time() - start_time:.2f}s"

    response = OrderedDict()
    response.update(structured)
    response["data"] = {
        "name": rdap_data.get("name"),
        "ldhName": rdap_data.get("ldhName"),
        "status": rdap_data.get("status", []),
        "events": rdap_data.get("events", []),
        "entities": rdap_data.get("entities", []),
        "remarks": rdap_data.get("remarks", []),
        "notices": rdap_data.get("notices", []),
        "links": rdap_data.get("links", []),
        "_raw_rdap": rdap_data
    }
    response["time_taken"] = time_taken
    response["api_owner"] = "@ISmartCoder"
    response["api_dev"] = "@abirxdhackz"
    response["source"] = "rdap"

    return JSONResponse(content=dict(response))