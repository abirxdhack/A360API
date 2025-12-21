from fastapi import APIRouter
from fastapi.responses import JSONResponse
from googletrans import Translator, LANGUAGES
from utils import LOGGER

router = APIRouter(prefix="/tr")
translator = Translator()

@router.get("")
async def translate(text: str = "", lang: str = "en"):
    if not text:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Missing 'text' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    if lang not in LANGUAGES:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid language code",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        translation = await translator.translate(text, dest=lang)
        return JSONResponse(
            content={
                "translated_text": translation.text,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error translating text '{text}' to language '{lang}': {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )