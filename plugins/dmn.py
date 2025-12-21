from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse
import aiohttp
import re
import html
import time
from collections import OrderedDict

from utils import LOGGER

router = APIRouter(prefix="/dmn")

HEADERS = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 11; RMX1993 Build/RKQ1.201112.002) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.7390.122 Mobile Safari/537.36",
    'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    'Accept-Encoding': "gzip, deflate, br, zstd",
    'sec-ch-ua': "\"Android WebView\";v=\"141\", \"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"141\"",
    'sec-ch-ua-mobile': "?1",
    'sec-ch-ua-platform': "\"Android\"",
    'upgrade-insecure-requests': "1",
    'dnt': "1",
    'x-requested-with': "mark.via.gp",
    'sec-fetch-site': "none",
    'sec-fetch-mode': "navigate",
    'sec-fetch-user': "?1",
    'sec-fetch-dest': "document",
    'accept-language': "en-US,en;q=0.9",
    'priority': "u=0, i"
}

def clean_html_fragment(s: str) -> str:
    if s is None:
        return ""
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = re.sub(r"[ \t\r\f\v]+", " ", s).strip()
    s = re.sub(r"\n\s+", "\n", s)
    return s

def parse_label_value_pairs(html_text: str):
    pairs = {}
    pattern = re.compile(
        r'<div\s+class=["\']df-row["\']\s*>\s*'
        r'<div\s+class=["\']df-label["\']\s*>(?P<label>.*?)</div>\s*'
        r'<div\s+class=["\']df-value["\']\s*>(?P<value>.*?)</div>\s*'
        r'</div>',
        re.S | re.I
    )
    for m in pattern.finditer(html_text):
        raw_label = m.group("label")
        raw_value = m.group("value")
        label = clean_html_fragment(raw_label).rstrip(":").strip()
        value = clean_html_fragment(raw_value)
        norm_label = label.lower().replace(" ", "_")
        pairs[norm_label] = value
    return pairs

def fallback_domain_from_h1(html_text: str) -> str:
    m = re.search(r"<h1[^>]*>\s*([^<\n\r]+?)\s*</h1>", html_text, re.I)
    if m:
        return clean_html_fragment(m.group(1))
    return ""

def build_structured_json(pairs, html_text):
    out = {}
    out['domain'] = pairs.get('domain') or fallback_domain_from_h1(html_text)
    out['registered_on'] = pairs.get('registered_on') or pairs.get('registration_date')
    out['expires_on'] = pairs.get('expires_on') or pairs.get('expiry_date') or pairs.get('registrar_registration_expiration_date')
    out['updated_on'] = pairs.get('updated_on') or pairs.get('last_updated')
    out['status'] = pairs.get('status')
    ns_raw = pairs.get('name_servers') or pairs.get('name_server') or pairs.get('name_servers:')
    if ns_raw:
        ns = [line.strip().strip(".") for line in ns_raw.splitlines() if line.strip()]
    else:
        ns = []
    out['name_servers'] = ns
    out['registrar'] = pairs.get('registrar')
    out['iana_id'] = pairs.get('iana_id')
    out['registrar_email'] = pairs.get('email')
    out['registrar_abuse_email'] = pairs.get('abuse_email')
    out['registrar_abuse_phone'] = pairs.get('abuse_phone')
    out['registrant_state'] = pairs.get('state')
    out['registrant_country'] = pairs.get('country')
    out['raw_pairs'] = pairs
    return out

@router.get("")
async def whois_domain(domain: str = Query(..., description="Domain name to lookup")):
    start_time = time.time()
    if not domain:
        raise HTTPException(status_code=400, detail="Domain parameter is required")

    domain = domain.strip().lower()
    if not re.match(r'^[a-z0-9.-]+\.[a-z]{2,}$', domain):
        raise HTTPException(status_code=400, detail="Invalid domain format")

    url = f"https://www.whois.com/whois/{domain}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=HEADERS, timeout=20) as resp:
                if resp.status != 200:
                    raise HTTPException(status_code=resp.status, detail="Failed to fetch WHOIS page")
                html_text = await resp.text()
    except Exception as e:
        LOGGER.error(f"Failed to fetch whois for {domain}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch WHOIS data")

    pairs = parse_label_value_pairs(html_text)
    structured = build_structured_json(pairs, html_text)

    time_taken = f"{time.time() - start_time:.2f}s"

    response = OrderedDict()
    response.update(structured)
    response["time_taken"] = time_taken
    response["api_owner"] = "@ISmartCoder"
    response["api_dev"] = "@abirxdhackz"
    response["source"] = "whois.com"

    return JSONResponse(content=dict(response))