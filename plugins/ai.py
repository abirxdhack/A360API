from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from bs4 import BeautifulSoup
import re
import uuid
import time
import json
from datetime import datetime

router = APIRouter(prefix="/ai")

def extract_snlm0e_token(html):
    patterns = [
        r'"SNlM0e":"([^"]+)"',
        r"'SNlM0e':'([^']+)'",
        r'SNlM0e["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'"FdrFJe":"([^"]+)"',
        r"'FdrFJe':'([^']+)'",
        r'FdrFJe["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'"cfb2h":"([^"]+)"',
        r"'cfb2h':'([^']+)'",
        r'cfb2h["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'at["\']?\s*[:=]\s*["\']([^"\']{50,})["\']',
        r'"at":"([^"]+)"',
        r'"token":"([^"]+)"',
        r'data-token["\']?\s*=\s*["\']([^"\']+)["\']'
    ]
    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            token = match.group(1)
            if len(token) > 20:
                return token
    return None

def extract_from_script_tags(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script"):
        if script.string:
            content = script.string
            if "SNlM0e" in content or "FdrFJe" in content:
                token = extract_snlm0e_token(content)
                if token:
                    return token
            json_patterns = [
                r'\{[^}]*"[^"]*token[^"]*"[^}]*\}',
                r'\{[^}]*SNlM0e[^}]*\}',
                r'\{[^}]*FdrFJe[^}]*\}'
            ]
            for pat in json_patterns:
                for m in re.finditer(pat, content, re.IGNORECASE):
                    try:
                        obj = json.loads(m.group(0))
                        for val in obj.values():
                            if isinstance(val, str) and len(val) > 50:
                                return val
                    except:
                        continue
    return None

def extract_build_and_session_params(html):
    params = {}
    bl_patterns = [
        r'bl["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'"bl":"([^"]+)"',
        r'buildLabel["\']?\s*[:=]\s*["\']([^"\']+)["\']',
        r'boq[_-]assistant[^"\']*_(\d+\.\d+[^"\']*)',
        r'/_/BardChatUi.*?bl=([^&"\']+)'
    ]
    for pat in bl_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            params["bl"] = m.group(1)
            break
    fsid_patterns = [
        r'f\.sid["\']?\s*[:=]\s*["\']?([^"\'\s&]+)',
        r'"fsid":"([^"]+)"',
        r'f\.sid=([^&"\']+)',
        r'sessionId["\']?\s*[:=]\s*["\']([^"\']+)["\']'
    ]
    for pat in fsid_patterns:
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            params["fsid"] = m.group(1)
            break
    reqid = re.search(r'_reqid["\']?\s*[:=]\s*["\']?(\d+)', html)
    if reqid:
        params["reqid"] = int(reqid.group(1))
    if "bl" not in params:
        params["bl"] = "boq_assistant-bard-web-server_20251231.00_p0"
    if "fsid" not in params:
        params["fsid"] = str(-1 * int(time.time() * 1000))
    if "reqid" not in params:
        params["reqid"] = int(time.time() * 1000) % 1000000
    return params

def scrape_fresh_session_gemini():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }
    try:
        resp = session.get("https://gemini.google.com/app", headers=headers, timeout=30)
        html = resp.text
        cookies = {c.name: c.value for c in session.cookies}
        token = extract_snlm0e_token(html) or extract_from_script_tags(html)
        if not token:
            return None
        params = extract_build_and_session_params(html)
        return {
            "session": session,
            "cookies": cookies,
            "snlm0e": token,
            "bl": params["bl"],
            "fsid": params["fsid"],
            "reqid": params["reqid"]
        }
    except:
        return None

def build_payload_gemini(prompt, snlm0e):
    prompt_esc = prompt.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    session_id = uuid.uuid4().hex
    request_uuid = str(uuid.uuid4()).upper()
    data = [
        [prompt_esc, 0, None, None, None, None, 0],
        ["en-US"],
        ["", "", "", None, None, None, None, None, None, ""],
        snlm0e,
        session_id,
        None,
        [0],
        1,
        None,
        None,
        1,
        0,
        None,
        None,
        None,
        None,
        None,
        [[0]],
        0,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        1,
        None,
        None,
        [4],
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        [2],
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        0,
        None,
        None,
        None,
        None,
        None,
        request_uuid,
        None,
        []
    ]
    payload_str = json.dumps(data, separators=(",", ":"))
    esc_payload = payload_str.replace("\\", "\\\\").replace('"', '\\"')
    return {"f.req": f'[null,"{esc_payload}"]', "": ""}

def parse_streaming_response_gemini(text):
    full = ""
    for line in text.strip().split("\n"):
        if not line or line.startswith(")]}"):
            continue
        try:
            if line.isdigit():
                continue
            data = json.loads(line)
            if isinstance(data, list) and len(data) > 0 and data[0][0] == "wrb.fr" and len(data[0]) > 2:
                inner = data[0][2]
                if inner:
                    parsed = json.loads(inner)
                    if isinstance(parsed, list) and len(parsed) > 4:
                        arr = parsed[4]
                        if isinstance(arr, list) and len(arr) > 0:
                            item = arr[0]
                            if isinstance(item, list) and len(item) > 1 and isinstance(item[1], list):
                                texts = item[1]
                                if len(texts) > 0:
                                    cand = texts[0]
                                    if isinstance(cand, str) and len(cand) > len(full):
                                        full = cand
        except:
            continue
    if full:
        full = full.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
    return full or None

def scrape_fresh_session_pplxty():
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Redmi 8A Dual) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8"
    }
    try:
        resp = session.get("https://www.perplexity.ai", headers=headers, timeout=30)
        html = resp.text
        cookies = {c.name: c.value for c in session.cookies}
        visitor = cookies.get("pplx.visitor-id", str(uuid.uuid4()))
        sess = cookies.get("pplx.session-id", str(uuid.uuid4()))
        ver = re.search(r'"version":"([\d.]+)"', html)
        version = ver.group(1) if ver else "2.35"
        csrf = re.search(r'csrf-token["\']?\s*[:=]\s*["\']([^"\']+)', html)
        csrf_token = csrf.group(1) if csrf else f"{uuid.uuid4().hex}|{uuid.uuid4().hex}"
        api = re.search(r'"apiUrl":"([^"]+)"', html)
        api_url = api.group(1) if api else "https://www.perplexity.ai/rest/sse/perplexity_ask"
        ts = int(time.time())
        return {
            "session": session,
            "cookies": cookies,
            "visitor_id": visitor,
            "session_id": sess,
            "version": version,
            "csrf_token": csrf_token,
            "api_url": api_url,
            "timestamp": ts
        }
    except:
        return None

def parse_response_pplxty(text):
    answer = ""
    sources = []
    metadata = {}
    for line in text.strip().split("\n"):
        if not line.startswith("data: "):
            continue
        js = line[6:].strip()
        if not js or js == "{}":
            continue
        try:
            data = json.loads(js)
            if "backend_uuid" in data:
                metadata["backend_uuid"] = data["backend_uuid"]
            if "text" in data and data.get("step_type") == "FINAL":
                content = data["text"]
                try:
                    steps = json.loads(content)
                    if isinstance(steps, list):
                        for s in steps:
                            if s.get("step_type") == "FINAL":
                                ans = s.get("content", {}).get("answer", "")
                                if ans:
                                    obj = json.loads(ans)
                                    answer = obj.get("answer", "")
                                    sources = obj.get("web_results", [])
                                    if not sources:
                                        sources = obj.get("extra_web_results", [])
                                    break
                except:
                    pass
            if "blocks" in data and not answer:
                for b in data["blocks"]:
                    if b.get("intended_usage") in ["ask_text_0_markdown", "ask_text"]:
                        mb = b.get("markdown_block", {})
                        if mb.get("answer"):
                            answer = mb["answer"]
                            break
        except:
            continue
    return answer.strip() if answer else "No answer received", sources, metadata

@router.get("/gem")
async def gem(prompt: str = ""):
    if not prompt:
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Missing required parameter: prompt",
            "api_dev": "@ISmartCoder",
            "usage": {
                "endpoint": "/api/gem",
                "method": "GET",
                "parameters": {
                    "prompt": "Your question or message (required)"
                },
                "example": "/api/gem?prompt=Hello, how are you?"
            }
        })
    
    if len(prompt.strip()) == 0:
        return JSONResponse(status_code=400, content={
            "success": False,
            "error": "Prompt cannot be empty",
            "api_dev": "@ISmartCoder"
        })
    
    start_time = time.time()
    data = scrape_fresh_session_gemini()
    
    if not data:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "Failed to establish session with Gemini",
            "api_dev": "@ISmartCoder"
        })
    
    cookie_str = "; ".join(f"{k}={v}" for k, v in data["cookies"].items())
    url = f"https://gemini.google.com/_/BardChatUi/data/assistant.lamda.BardFrontendService/StreamGenerate?bl={data['bl']}&f.sid={data['fsid']}&hl=en-US&_reqid={data['reqid']}&rt=c"
    payload = build_payload_gemini(prompt, data["snlm0e"])
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "origin": "https://gemini.google.com",
        "referer": "https://gemini.google.com/",
        "x-same-domain": "1",
        "Cookie": cookie_str
    }
    
    try:
        resp = data["session"].post(url, data=payload, headers=headers, timeout=60)
        if resp.status_code != 200:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": f"HTTP {resp.status_code}",
                "api_dev": "@ISmartCoder"
            })
        
        result = parse_streaming_response_gemini(resp.text)
        end_time = time.time()
        response_time = round(end_time - start_time, 2)
        
        if result:
            return JSONResponse(content={
                "success": True,
                "prompt": prompt,
                "response": result,
                "metadata": {
                    "response_time": f"{response_time}s",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "model": "gemini",
                    "character_count": len(result),
                    "word_count": len(result.split())
                },
                "api_dev": "@ISmartCoder"
            })
        else:
            return JSONResponse(status_code=500, content={
                "success": False,
                "error": "No response received from Gemini",
                "api_dev": "@ISmartCoder"
            })
    except:
        return JSONResponse(status_code=500, content={
            "success": False,
            "error": "Gemini request failed",
            "api_dev": "@ISmartCoder"
        })

@router.get("/pplxty")
async def pplxty(prompt: str = "", mode: str = "concise", model: str = "turbo", search_focus: str = "internet"):
    if not prompt:
        return JSONResponse(status_code=400, content={
            "status": "error",
            "message": "Prompt parameter is required",
            "apidev": "@ISmartCoder",
            "api_channel": "@abirxdhackz"
        })
    
    data = scrape_fresh_session_pplxty()
    if not data:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Failed to establish Perplexity session",
            "apidev": "@ISmartCoder",
            "api_channel": "@abirxdhackz"
        })
    
    frontend_uuid = str(uuid.uuid4())
    backend_uuid = str(uuid.uuid4())
    read_write_token = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    current_time = data["timestamp"]
    
    payload = {
        "params": {
            "last_backend_uuid": backend_uuid,
            "read_write_token": read_write_token,
            "attachments": [],
            "language": "en-US",
            "timezone": "Asia/Dhaka",
            "search_focus": search_focus,
            "sources": ["web"],
            "frontend_uuid": frontend_uuid,
            "mode": mode,
            "model_preference": model,
            "version": data["version"],
            "is_related_query": False,
            "is_sponsored": False,
            "prompt_source": "user",
            "query_source": "followup",
            "is_incognito": False,
            "skip_search_enabled": True,
            "source": "mweb"
        },
        "query_str": prompt
    }
    
    add_cookies = {
        "pplx.visitor-id": data["visitor_id"],
        "pplx.session-id": data["session_id"],
        "next-auth.csrf-token": data["csrf_token"],
        "pplx.mweb-splash-page-dismissed": "true",
        "pplx.la-status": "allowed",
        "__ps_fva": str(data["timestamp"] * 1000),
        "pplx.metadata": json.dumps({
            "qc": 2,
            "qcu": 0,
            "qcm": 0,
            "qcc": 0,
            "qcco": 0,
            "qccol": 0,
            "qcdr": 0,
            "qcs": 0,
            "qcd": 0,
            "hli": False,
            "hcga": False,
            "hcds": False,
            "hso": False,
            "hfo": False,
            "hsco": False,
            "hfco": False,
            "hsma": False,
            "hdc": False,
            "fqa": current_time * 1000,
            "lqa": current_time * 1000
        })
    }
    
    all_cookies = {**data["cookies"], **add_cookies}
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; Redmi 8A Dual) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Mobile Safari/537.36",
        "Accept": "text/event-stream",
        "Content-Type": "application/json",
        "origin": "https://www.perplexity.ai",
        "x-requested-with": "mark.via.gp",
        "x-request-id": request_id,
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache"
    }
    
    if data["csrf_token"] and "|" in data["csrf_token"]:
        headers["x-csrf-token"] = data["csrf_token"]
    
    try:
        time.sleep(0.5)
        resp = data["session"].post(data["api_url"], json=payload, headers=headers, cookies=all_cookies, timeout=120)
        
        if resp.status_code != 200:
            return JSONResponse(status_code=500, content={
                "status": "error",
                "message": f"Failed to fetch data: HTTP {resp.status_code}",
                "response_text": resp.text[:500],
                "apidev": "@ISmartCoder",
                "api_channel": "@abirxdhackz"
            })
        
        answer, sources, metadata = parse_response_pplxty(resp.text)
        
        return JSONResponse(content={
            "status": "success",
            "prompt": prompt,
            "answer": answer,
            "sources": sources,
            "metadata": metadata,
            "mode": mode,
            "model": model,
            "timestamp": current_time,
            "apidev": "@ISmartCoder",
            "api_channel": "@abirxdhackz"
        })
    except:
        return JSONResponse(status_code=500, content={
            "status": "error",
            "message": "Perplexity request failed",
            "apidev": "@ISmartCoder",
            "api_channel": "@abirxdhackz"
        })