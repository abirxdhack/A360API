#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
from utils import LOGGER

router = APIRouter(prefix="/git")

@router.get("/user")
async def get_user_repos(username: str = ""):
    if not username:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Username parameter is required",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    try:
        response = requests.get(f"https://api.github.com/users/{username}/repos")
        if response.status_code != 200:
            LOGGER.error(f"GitHub API returned status {response.status_code} for user {username}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No repositories found for user {username}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        data = response.json()
        return JSONResponse(content=data)
    
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching GitHub data for {username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to fetch data: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing GitHub request for {username}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )