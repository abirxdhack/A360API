from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from gtts import gTTS
from gtts.lang import tts_langs
import os
import time
from threading import Thread
from utils import LOGGER

router = APIRouter(prefix="/tts")

LANGUAGES_CACHE = None
ACCENTS_CACHE = None

def get_flag_emoji(country_code):
    try:
        if not country_code:
            return ""
        
        country_code = country_code.upper()
        
        if len(country_code) == 2:
            return chr(127397 + ord(country_code[0])) + chr(127397 + ord(country_code[1]))
        
        return ""
    except:
        return ""

def get_country_code_from_lang(lang_code):
    lang_to_country = {
        'af': 'ZA', 'ar': 'SA', 'bn': 'BD', 'bs': 'BA', 'ca': 'ES',
        'cs': 'CZ', 'da': 'DK', 'de': 'DE', 'el': 'GR', 'en': 'GB',
        'es': 'ES', 'et': 'EE', 'fi': 'FI', 'fr': 'FR', 'gu': 'IN',
        'hi': 'IN', 'hr': 'HR', 'hu': 'HU', 'id': 'ID', 'is': 'IS',
        'it': 'IT', 'ja': 'JP', 'jw': 'ID', 'km': 'KH', 'kn': 'IN',
        'ko': 'KR', 'la': 'VA', 'ml': 'IN', 'mr': 'IN', 'my': 'MM',
        'ne': 'NP', 'nl': 'NL', 'no': 'NO', 'pl': 'PL', 'pt': 'PT',
        'ro': 'RO', 'ru': 'RU', 'si': 'LK', 'sk': 'SK', 'sq': 'AL',
        'sr': 'RS', 'su': 'ID', 'sv': 'SE', 'sw': 'KE', 'ta': 'IN',
        'te': 'IN', 'th': 'TH', 'tr': 'TR', 'uk': 'UA', 'ur': 'PK',
        'vi': 'VN', 'zh-CN': 'CN', 'zh-TW': 'TW', 'zh-cn': 'CN', 'zh-tw': 'TW'
    }
    return lang_to_country.get(lang_code, None)

def get_available_languages():
    langs = tts_langs()
    result = []
    
    for code, name in sorted(langs.items()):
        country_code = get_country_code_from_lang(code)
        flag = get_flag_emoji(country_code)
        
        result.append({
            'code': code,
            'name': name,
            'flag': flag
        })
    
    return result

def get_accent_flag(tld):
    tld_to_country = {
        'com.au': 'AU', 'co.uk': 'GB', 'us': 'US', 'ca': 'CA',
        'co.in': 'IN', 'ie': 'IE', 'co.za': 'ZA', 'com.ng': 'NG',
        'fr': 'FR', 'com.br': 'BR', 'pt': 'PT', 'com.mx': 'MX',
        'es': 'ES', 'com': 'US'
    }
    country_code = tld_to_country.get(tld, None)
    return get_flag_emoji(country_code)

def get_available_accents():
    accents = {
        'en': [
            {'tld': 'com.au', 'name': 'English (Australia)'},
            {'tld': 'co.uk', 'name': 'English (United Kingdom)'},
            {'tld': 'us', 'name': 'English (United States)'},
            {'tld': 'ca', 'name': 'English (Canada)'},
            {'tld': 'co.in', 'name': 'English (India)'},
            {'tld': 'ie', 'name': 'English (Ireland)'},
            {'tld': 'co.za', 'name': 'English (South Africa)'},
            {'tld': 'com.ng', 'name': 'English (Nigeria)'}
        ],
        'fr': [
            {'tld': 'ca', 'name': 'French (Canada)'},
            {'tld': 'fr', 'name': 'French (France)'}
        ],
        'pt': [
            {'tld': 'com.br', 'name': 'Portuguese (Brazil)'},
            {'tld': 'pt', 'name': 'Portuguese (Portugal)'}
        ],
        'es': [
            {'tld': 'com.mx', 'name': 'Spanish (Mexico)'},
            {'tld': 'es', 'name': 'Spanish (Spain)'},
            {'tld': 'us', 'name': 'Spanish (United States)'}
        ]
    }
    
    result = {}
    for lang, accent_list in accents.items():
        result[lang] = []
        for accent in accent_list:
            result[lang].append({
                'tld': accent['tld'],
                'name': accent['name'],
                'flag': get_accent_flag(accent['tld'])
            })
    
    return result

def cleanup_file(filepath: str, delay: int = 60):
    time.sleep(delay)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            LOGGER.info(f"Deleted TTS file: {filepath}")
    except Exception as e:
        LOGGER.error(f"Error deleting TTS file {filepath}: {e}")

def get_base_url(request: Request):
    return f"{request.url.scheme}://{request.url.netloc}"

def initialize_cache():
    global LANGUAGES_CACHE, ACCENTS_CACHE
    
    if LANGUAGES_CACHE is None:
        LOGGER.info("Loading available TTS languages...")
        LANGUAGES_CACHE = get_available_languages()
        LOGGER.info(f"Loaded {len(LANGUAGES_CACHE)} TTS languages")
    
    if ACCENTS_CACHE is None:
        ACCENTS_CACHE = get_available_accents()
        total_accents = sum(len(a) for a in ACCENTS_CACHE.values())
        LOGGER.info(f"Loaded {total_accents} TTS accents")

initialize_cache()

@router.get("/langlist")
async def get_languages_list():
    try:
        return JSONResponse(
            content={
                "total": len(LANGUAGES_CACHE),
                "languages": LANGUAGES_CACHE,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error getting language list: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/accentlist")
async def get_accents_list():
    try:
        return JSONResponse(
            content={
                "total": sum(len(accent_list) for accent_list in ACCENTS_CACHE.values()),
                "accents": ACCENTS_CACHE,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error getting accent list: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/generated/{filename}")
async def download_file(filename: str):
    try:
        filepath = os.path.join("/tmp", filename)
        
        if not os.path.exists(filepath):
            return JSONResponse(
                status_code=404,
                content={
                    "error": "File not found or expired",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        return FileResponse(
            path=filepath,
            media_type="audio/mpeg",
            filename=filename
        )
    except Exception as e:
        LOGGER.error(f"Error downloading TTS file: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/generate")
async def generate_speech(
    request: Request,
    text: str = None,
    lang: str = "en",
    accent: str = None
):
    try:
        if not text or text.strip() == "":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Text parameter is required",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        available_langs = tts_langs()
        if lang not in available_langs:
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Unsupported language: {lang}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        os.makedirs("/tmp", exist_ok=True)
        
        timestamp = int(time.time() * 1000)
        filename = f"tts_{timestamp}.mp3"
        filepath = os.path.join("/tmp", filename)
        
        tld = None
        
        if accent:
            if lang in ACCENTS_CACHE:
                valid_tlds = [a['tld'] for a in ACCENTS_CACHE[lang]]
                if accent not in valid_tlds:
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": f"Invalid accent for {lang}. Valid accents: {', '.join(valid_tlds)}",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                tld = accent
            else:
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": f"Language '{lang}' does not support accents. Only these languages support accents: {', '.join(ACCENTS_CACHE.keys())}",
                        "api_owner": "@ISmartCoder",
                        "api_updates": "t.me/abirxdhackz"
                    }
                )
        
        if tld:
            tts = gTTS(text=text, lang=lang, tld=tld, slow=False)
        else:
            tts = gTTS(text=text, lang=lang, slow=False)
        
        tts.save(filepath)
        
        file_size = os.path.getsize(filepath)
        base_url = get_base_url(request)
        download_url = f"{base_url}/tts/generated/{filename}"
        
        cleanup_thread = Thread(target=cleanup_file, args=(filepath, 60))
        cleanup_thread.daemon = True
        cleanup_thread.start()
        
        LOGGER.info(f"Generated TTS file: {filename} ({file_size} bytes)")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Speech generated successfully",
                "data": {
                    "download_url": download_url,
                    "filename": filename,
                    "size_bytes": file_size,
                    "size_kb": round(file_size / 1024, 2),
                    "language": lang,
                    "accent": accent if accent else "default",
                    "text": text,
                    "expires_in_seconds": 60
                },
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
        
    except ValueError as e:
        LOGGER.error(f"Invalid input for TTS generation: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error generating TTS: {str(e)}")
        if os.path.exists(filepath):
            os.remove(filepath)
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )