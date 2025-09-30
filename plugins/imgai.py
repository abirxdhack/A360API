#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import aiohttp
from config import IMGAI_API_KEY
from utils import LOGGER

router = APIRouter(prefix="/imgai")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

class ImageAnalysisRequest(BaseModel):
    code: str
    mimeType: str = "image/jpeg"
    prompt: str = "Describe The Image Properly"

class ImageOCRRequest(BaseModel):
    code: str
    mimeType: str = "image/jpeg"

async def analyze_image(image_base64: str, mime_type: str, prompt: str):
    url = f"{GEMINI_API_URL}?key={IMGAI_API_KEY}"
    payload = {
        "contents": [{
            "parts": [
                {"text": prompt},
                {
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": image_base64
                    }
                }
            ]
        }]
    }
    headers = {"Content-Type": "application/json"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status != 200:
                    error = await response.json()
                    error_message = error.get("error", {}).get("message", "Unknown error")
                    LOGGER.error(f"Gemini API request failed: {response.status} - {error_message}")
                    return None, error_message, response.status
                result = await response.json()
                analysis = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No analysis available for this image")
                return analysis, None, 200
    except Exception as e:
        LOGGER.error(f"Error analyzing image: {str(e)}")
        return None, str(e), 500

@router.post("/analysis")
async def image_analysis(request: ImageAnalysisRequest):
    if not request.code:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "code field is required in JSON body",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        analysis, error, status = await analyze_image(request.code, request.mimeType, request.prompt)
        if analysis is None:
            return JSONResponse(
                status_code=status,
                content={
                    "success": False,
                    "error": "Gemini API Request Failed",
                    "details": error,
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(
            content={
                "success": True,
                "analysis": analysis,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error in image analysis: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Image Analysis Failed",
                "details": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.post("/ocr")
async def image_ocr(request: ImageOCRRequest):
    if not request.code:
        raise HTTPException(
            status_code=400,
            detail={
                "success": False,
                "error": "code field is required in JSON body",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        prompt = "Extract All Visible Text In Image Of Any Lang No Skip"
        text, error, status = await analyze_image(request.code, request.mimeType, prompt)
        if text is None:
            return JSONResponse(
                status_code=status,
                content={
                    "success": False,
                    "error": "Gemini API Request Failed",
                    "details": error,
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(
            content={
                "success": True,
                "text": text,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error in image OCR: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Image OCR Failed",
                "details": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )