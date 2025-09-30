#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from utils import LOGGER

router = APIRouter(prefix="/country")

@router.get("")
async def get_country_info(name: str = ""):
    if not name:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Country name parameter is required",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        response = requests.get(f"https://restcountries.com/v3.1/name/{name}")
        if response.status_code != 200:
            LOGGER.error(f"REST Countries API returned status {response.status_code} for country {name}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No country found for name {name}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        data = response.json()
        return JSONResponse(content=data)
    
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching country data for {name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to fetch data: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing country request for {name}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )