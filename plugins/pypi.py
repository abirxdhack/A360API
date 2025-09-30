#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from utils import LOGGER

router = APIRouter(prefix="/pypi")

@router.get("")
async def get_pypi_info(query: str = ""):
    if not query:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Query parameter is required",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        response = requests.get(f"https://pypi.org/pypi/{query}/json")
        if response.status_code != 200:
            LOGGER.error(f"PyPI API returned status {response.status_code} for package {query}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No package found for {query}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        data = response.json()
        info = data.get("info", {})
        
        formatted_response = {
            "author": info.get("author"),
            "authorEmail": info.get("author_email"),
            "bugtrackUrl": info.get("bugtrack_url"),
            "description": info.get("summary"),
            "docsUrl": info.get("docs_url"),
            "homePage": info.get("home_page"),
            "keywords": info.get("keywords", []),
            "license": info.get("license"),
            "link": info.get("package_url"),
            "releaseUrl": info.get("release_url"),
            "title": info.get("name"),
            "version": info.get("version"),
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }
        
        return JSONResponse(content=formatted_response)
    
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching PyPI data for {query}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to fetch data: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing PyPI request for {query}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )