#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import aiohttp
from PIL import Image
from io import BytesIO
import random
import base64  
from pydantic import BaseModel
from utils import LOGGER

router = APIRouter(prefix="/ph")
UPSCALE_API_URL = "https://api.upscalepics.com/upscale-to-size"

class ImageEnhanceRequest(BaseModel):
    code: str  
    width: int = None  
    height: int = None  

async def upscale_image(image_base64: str, width: int, height: int):
    try:
        random_number = random.randint(1_000_000, 999_999_999_999)
        form_data = aiohttp.FormData()
        form_data.add_field("image_file", base64.b64decode(image_base64), filename=f"image_{random_number}.jpg", content_type="image/jpeg")
        form_data.add_field("name", str(random_number))
        form_data.add_field("desiredHeight", str(height * 4 if height else 0))
        form_data.add_field("desiredWidth", str(width * 4 if width else 0))
        form_data.add_field("outputFormat", "png")
        form_data.add_field("compressionLevel", "high")
        form_data.add_field("anime", "false")
        headers = {
            "Accept": "application/json, text/plain, */*",
            "Origin": "https://upscalepics.com",
            "Referer": "https://upscalepics.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(UPSCALE_API_URL, data=form_data, headers=headers) as response:
                if response.status == 200:
                    json_response = await response.json()
                    image_url = json_response.get("bgRemoved", "").strip()
                    if image_url and image_url.startswith("http"):
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                img_bytes = await img_response.read()
                                return base64.b64encode(img_bytes).decode("utf-8"), None
                    return None, "No valid image URL returned"
                else:
                    return None, f"API request failed with status {response.status}"
    except Exception as e:
        LOGGER.error(f"Upscale error: {str(e)}")
        return None, f"Upscale error: {str(e)}"

@router.post("/enh")
async def enhance_image(request: ImageEnhanceRequest):
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

        image_data = base64.b64decode(request.code)
        with Image.open(BytesIO(image_data)) as img:
            width, height = img.size if request.width is None and request.height is None else (request.width or img.width, request.height or img.height)
       
        enhanced_image, error = await upscale_image(request.code, width, height)
        if enhanced_image is None:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": error,
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        return JSONResponse(
            content={
                "success": True,
                "enhanced_image": enhanced_image,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except ValueError as e:
        LOGGER.error(f"Invalid image data: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Invalid image data",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error in image enhancement: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Image enhancement failed: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )