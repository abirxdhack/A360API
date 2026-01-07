from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
import aiohttp
import asyncio
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import os
import pytz
import pycountry
import requests
import tempfile
from utils import LOGGER

router = APIRouter(prefix="/wth")

def get_timezone_from_coordinates(lat, lon):
    from timezonefinder import TimezoneFinder
    try:
        tf = TimezoneFinder()
        timezone_str = tf.timezone_at(lat=lat, lng=lon)
        if timezone_str:
            return pytz.timezone(timezone_str)
        return pytz.timezone('UTC')
    except Exception as e:
        LOGGER.error(f"Timezone detection failed: {str(e)}")
        return pytz.timezone('UTC')

def get_country_name(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else country_code
    except Exception:
        return country_code

def create_weather_image(weather_data, output_path):
    current = weather_data["current_weather"]
    
    try:
        timezone = get_timezone_from_coordinates(weather_data["coordinates"]["latitude"], weather_data["coordinates"]["longitude"])
        local_time = datetime.now(timezone)
        time_text = local_time.strftime("%I:%M %p")
    except Exception as e:
        LOGGER.error(f"Time formatting failed: {str(e)}")
        time_text = datetime.now().strftime("%I:%M %p")
    
    img_width, img_height = 1200, 600
    background_color = (30, 39, 50)
    white = (255, 255, 255)
    light_gray = (200, 200, 200)
    
    img = Image.new("RGB", (img_width, img_height), color=background_color)
    draw = ImageDraw.Draw(img)
    
    try:
        font_bold_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
        font_bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 38)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    except Exception:
        font_bold_large = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    main_title = "Current Weather"
    temp_text = f"{current['temperature']}°C"
    condition_text = current["condition"]
    realfeel_text = f"RealFeel® {current['feels_like']}°C"
    country_name = get_country_name(weather_data['location']['country_code'])
    location_text = f"{weather_data['location']['city']}, {country_name}"
    
    draw.text((1140, 30), time_text, font=font_regular, fill=light_gray, anchor="ra")
    draw.text((40, 40), main_title, font=font_bold, fill=white)
    
    icon_x, icon_y = 320, 230
    for i in range(3):
        y = icon_y + i * 15
        draw.line([(icon_x, y), (icon_x + 60, y)], fill=light_gray, width=5)
    
    temp_x, temp_y = 500, 180
    draw.text((temp_x, temp_y), temp_text, font=font_bold_large, fill=white)
    draw.text((temp_x + 30, temp_y + 130), condition_text, font=font_regular, fill=light_gray)
    draw.text((temp_x + 10, temp_y + 180), realfeel_text, font=font_small, fill=light_gray)
    draw.text((40, 520), location_text, font=font_regular, fill=light_gray)
    
    img.save(output_path)
    return output_path

async def fetch_data(session, url):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
    except Exception as e:
        LOGGER.error(f"Fetch error for {url}: {str(e)}")
    return None

def upload_to_tmpfiles(file_path):
    try:
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post('https://tmpfiles.org/api/v1/upload', files=files)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    url = data['data']['url']
                    url = url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
                    LOGGER.info(f"Image uploaded successfully: {url}")
                    return url
        LOGGER.error(f"Upload failed: {response.text}")
    except Exception as e:
        LOGGER.error(f"Upload to tmpfiles failed: {str(e)}")
    return None

async def get_weather_data(city):
    async with aiohttp.ClientSession() as session:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geocode_data = await fetch_data(session, geocode_url)
        
        if not geocode_data or "results" not in geocode_data or not geocode_data["results"]:
            LOGGER.warning(f"No geocode results for city: {city}")
            return None
        
        result = geocode_data["results"][0]
        lat, lon = result["latitude"], result["longitude"]
        country_code = result.get("country_code", "").upper()
        
        LOGGER.info(f"Fetching weather for {city} at coordinates: {lat}, {lon}")
        
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}&"
            f"current=temperature_2m,relative_humidity_2m,apparent_temperature,weathercode,"
            f"wind_speed_10m,wind_direction_10m&"
            f"hourly=temperature_2m,apparent_temperature,relative_humidity_2m,weathercode,"
            f"precipitation_probability&"
            f"daily=temperature_2m_max,temperature_2m_min,sunrise,sunset,weathercode&"
            f"timezone=auto"
        )
        
        aqi_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality?"
            f"latitude={lat}&longitude={lon}&"
            f"hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone&"
            f"timezone=auto"
        )
        
        weather_data, aqi_data = await asyncio.gather(
            fetch_data(session, weather_url),
            fetch_data(session, aqi_url)
        )
        
        if not weather_data or not aqi_data:
            LOGGER.error(f"Failed to fetch weather or AQI data for {city}")
            return None
        
        current = weather_data["current"]
        hourly = weather_data["hourly"]
        daily = weather_data["daily"]
        aqi = aqi_data["hourly"]
        
        weather_code = {
            0: "Clear", 1: "Scattered Clouds", 2: "Scattered Clouds", 3: "Overcast Clouds",
            45: "Fog", 48: "Haze", 51: "Light Drizzle", 53: "Drizzle",
            55: "Heavy Drizzle", 61: "Light Rain", 63: "Moderate Rain", 65: "Heavy Rain",
            66: "Freezing Rain", 67: "Heavy Freezing Rain", 71: "Light Snow",
            73: "Snow", 75: "Heavy Snow", 77: "Snow Grains", 80: "Showers",
            81: "Heavy Showers", 82: "Violent Showers", 95: "Thunderstorm",
            96: "Thunderstorm", 99: "Heavy Thunderstorm"
        }
        
        hourly_forecast = []
        for i in range(min(12, len(hourly["time"]))):
            time_str = hourly["time"][i].split("T")[1][:5]
            hour = int(time_str[:2])
            time_format = f"{hour % 12 or 12} {'AM' if hour < 12 else 'PM'}"
            
            hourly_forecast.append({
                "time": time_format,
                "temperature": round(hourly["temperature_2m"][i], 1),
                "condition": weather_code.get(hourly["weathercode"][i], "Unknown"),
                "humidity": hourly["relative_humidity_2m"][i],
                "precipitation_chance": hourly["precipitation_probability"][i]
            })
        
        current_date = datetime.now()
        daily_forecast = []
        for i in range(min(7, len(daily["temperature_2m_max"]))):
            day_date = (current_date + timedelta(days=i))
            daily_forecast.append({
                "date": day_date.strftime('%Y-%m-%d'),
                "day_name": day_date.strftime('%a, %b %d'),
                "temperature": {
                    "min": round(daily["temperature_2m_min"][i], 1),
                    "max": round(daily["temperature_2m_max"][i], 1)
                },
                "condition": weather_code.get(daily["weathercode"][i], "Unknown"),
                "sun": {
                    "sunrise": daily["sunrise"][i].split("T")[1][:5],
                    "sunset": daily["sunset"][i].split("T")[1][:5]
                }
            })
        
        pm25 = aqi["pm2_5"][0]
        if pm25 <= 12:
            aqi_level = "Good"
        elif pm25 <= 35:
            aqi_level = "Fair"
        elif pm25 <= 55:
            aqi_level = "Moderate"
        else:
            aqi_level = "Poor"
        
        try:
            timezone = get_timezone_from_coordinates(lat, lon)
            local_time = datetime.now(timezone)
            current_time = local_time.strftime("%I:%M %p")
            current_date_str = local_time.strftime("%Y-%m-%d")
        except Exception:
            current_time = datetime.now().strftime("%I:%M %p")
            current_date_str = datetime.now().strftime("%Y-%m-%d")
        
        LOGGER.info(f"Successfully fetched weather data for {city}")
        
        return {
            "status": "success",
            "location": {
                "city": city.capitalize(),
                "country": get_country_name(country_code),
                "country_code": country_code
            },
            "coordinates": {
                "latitude": lat,
                "longitude": lon
            },
            "current_weather": {
                "timestamp": {
                    "time": current_time,
                    "date": current_date_str
                },
                "temperature": round(current["temperature_2m"], 1),
                "feels_like": round(current["apparent_temperature"], 1),
                "condition": weather_code.get(current["weathercode"], "Unknown"),
                "condition_code": current["weathercode"],
                "humidity": current["relative_humidity_2m"],
                "wind": {
                    "speed": round(current["wind_speed_10m"], 1),
                    "direction": current["wind_direction_10m"]
                },
                "sun": {
                    "sunrise": daily["sunrise"][0].split("T")[1][:5],
                    "sunset": daily["sunset"][0].split("T")[1][:5]
                }
            },
            "forecast": {
                "hourly": hourly_forecast,
                "daily": daily_forecast
            },
            "air_quality": {
                "level": aqi_level,
                "fine_particles": round(aqi["pm2_5"][0], 2),
                "coarse_particles": round(aqi["pm10"][0], 2),
                "carbon_monoxide": round(aqi["carbon_monoxide"][0], 2),
                "nitrogen_dioxide": round(aqi["nitrogen_dioxide"][0], 2),
                "ozone": round(aqi["ozone"][0], 2)
            },
            "weather_maps": {
                "temperature": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=8",
                "clouds": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=clouds&lat={lat}&lon={lon}&zoom=8",
                "precipitation": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=precipitation&lat={lat}&lon={lon}&zoom=8",
                "wind": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=wind&lat={lat}&lon={lon}&zoom=8",
                "pressure": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=pressure&lat={lat}&lon={lon}&zoom=8"
            }
        }

@router.get("")
async def get_weather(area: str = None):
    try:
        if not area:
            LOGGER.warning("Missing area parameter in request")
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Missing 'area' parameter. Usage: /wth?area=London",
                    "api_owner": "@ISmartCoder",
                    "api_dev": "@abirxdhackz"
                }
            )
        
        LOGGER.info(f"Received weather request for area: {area}")
        
        weather_data = await get_weather_data(area)
        
        if not weather_data:
            LOGGER.error(f"No weather data found for area: {area}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Weather data unavailable for '{area}'. Please check the city name.",
                    "api_owner": "@ISmartCoder",
                    "api_dev": "@abirxdhackz"
                }
            )
        
        temp_dir = tempfile.gettempdir()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = os.path.join(temp_dir, f"weather_{area}_{timestamp}.png")
        
        LOGGER.info(f"Generating weather image at: {image_path}")
        create_weather_image(weather_data, image_path)
        
        LOGGER.info("Uploading image to tmpfiles.org")
        image_url = upload_to_tmpfiles(image_path)
        
        try:
            os.remove(image_path)
            LOGGER.info(f"Successfully removed local image: {image_path}")
        except Exception as e:
            LOGGER.error(f"Failed to remove image: {str(e)}")
        
        if image_url:
            weather_data["weather_image"] = {
                "url": image_url,
                "status": "available"
            }
        else:
            weather_data["weather_image"] = {
                "url": None,
                "status": "unavailable",
                "error": "Failed to upload image to hosting service"
            }
        
        weather_data["api_owner"] = "@ISmartCoder"
        weather_data["api_dev"] = "@abirxdhackz"
        
        LOGGER.info(f"Successfully processed weather request for {area}")
        return JSONResponse(content=weather_data)
        
    except ValueError as e:
        LOGGER.error(f"Invalid input for weather lookup: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": str(e),
                "api_owner": "@ISmartCoder",
                "api_dev": "@abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error processing weather request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error. Please try again later.",
                "error_details": str(e),
                "api_owner": "@ISmartCoder",
                "api_dev": "@abirxdhackz"
            }
        )