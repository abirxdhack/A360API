#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from smartfaker import Faker
from utils import LOGGER

router = APIRouter(prefix="/fake")

fake = Faker()

def get_flag(country_code):
    try:
        return ''.join(chr(0x1F1E6 + ord(c) - ord('A')) for c in country_code.upper())
    except Exception:
        return "🏚"

@router.get("/address")
async def get_address(code: str = "", amount: int = 1):
    country_code = code.upper()
    if not country_code:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Country code parameter is required",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    file_country_code = 'GB' if country_code == 'UK' else country_code
    try:
        addresses = await fake.address(file_country_code, amount)
        if amount == 1:
            addresses = [addresses]
        
        if not addresses:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Sorry No Address Available For This Country",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        response_addresses = []
        for address in addresses:
            address["api_owner"] = "@ISmartCoder"
            address["api_updates"] = "t.me/abirxdhackz"
            address["country_flag"] = get_flag(file_country_code)
            response_addresses.append(address)
        
        return JSONResponse(content=response_addresses if amount > 1 else response_addresses[0])
    
    except ValueError:
        LOGGER.error(f"Invalid country code provided: {file_country_code}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Sorry Bro Invalid Country Code Provided",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error processing address request for {file_country_code}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/countries")
async def get_countries():
    try:
        countries = fake.countries()
        if not countries:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No countries found",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        
        formatted_countries = []
        for country in countries:
            country_code = country['country_code']
            display_country_code = 'GB' if country_code == 'UK' else country_code
            formatted_countries.append({
                "country_code": display_country_code,
                "country_name": country['country_name']
            })
        
        return JSONResponse(
            content={
                "countries": sorted(formatted_countries, key=lambda x: x["country_name"]),
                "total_countries": len(formatted_countries),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    
    except Exception as e:
        LOGGER.error(f"Error processing countries request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )