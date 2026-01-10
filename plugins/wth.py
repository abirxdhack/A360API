from fastapi import APIRouter
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
import io
from utils import LOGGER

router = APIRouter(prefix="/wth")

FONT_CACHE = {}

def download_font(url, size):
    cache_key = f"{url}_{size}"
    if cache_key in FONT_CACHE:
        return FONT_CACHE[cache_key]
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            font = ImageFont.truetype(io.BytesIO(response.content), size)
            FONT_CACHE[cache_key] = font
            LOGGER.info(f"Font cached successfully: {cache_key}")
            return font
        else:
            LOGGER.error(f"Font download failed with status {response.status_code}")
    except Exception as e:
        LOGGER.error(f"Failed to download font from {url}: {str(e)}")
    
    return ImageFont.load_default()

def get_timezone_from_country_code(country_code):
    try:
        country_code = country_code.lower().strip()
        
        special_timezones = {
            "gb": "Europe/London",
            "uk": "Europe/London",
            "ae": "Asia/Dubai",
            "us": "America/New_York",
            "ca": "America/Toronto",
            "au": "Australia/Sydney",
            "nz": "Pacific/Auckland",
            "jp": "Asia/Tokyo",
            "cn": "Asia/Shanghai",
            "in": "Asia/Kolkata",
            "pk": "Asia/Karachi",
            "bd": "Asia/Dhaka",
            "ru": "Europe/Moscow",
            "br": "America/Sao_Paulo",
            "mx": "America/Mexico_City",
            "ar": "America/Argentina/Buenos_Aires",
            "za": "Africa/Johannesburg",
            "eg": "Africa/Cairo",
            "sa": "Asia/Riyadh",
            "tr": "Europe/Istanbul",
            "de": "Europe/Berlin",
            "fr": "Europe/Paris",
            "es": "Europe/Madrid",
            "it": "Europe/Rome",
            "nl": "Europe/Amsterdam",
            "se": "Europe/Stockholm",
            "no": "Europe/Oslo",
            "dk": "Europe/Copenhagen",
            "fi": "Europe/Helsinki",
            "pl": "Europe/Warsaw",
            "gr": "Europe/Athens",
            "pt": "Europe/Lisbon",
            "ie": "Europe/Dublin",
            "ch": "Europe/Zurich",
            "at": "Europe/Vienna",
            "be": "Europe/Brussels",
            "cz": "Europe/Prague",
            "hu": "Europe/Budapest",
            "ro": "Europe/Bucharest",
            "bg": "Europe/Sofia",
            "hr": "Europe/Zagreb",
            "sk": "Europe/Bratislava",
            "si": "Europe/Ljubljana",
            "lt": "Europe/Vilnius",
            "lv": "Europe/Riga",
            "ee": "Europe/Tallinn",
            "ua": "Europe/Kiev",
            "by": "Europe/Minsk",
            "kr": "Asia/Seoul",
            "th": "Asia/Bangkok",
            "vn": "Asia/Ho_Chi_Minh",
            "id": "Asia/Jakarta",
            "my": "Asia/Kuala_Lumpur",
            "sg": "Asia/Singapore",
            "ph": "Asia/Manila",
            "hk": "Asia/Hong_Kong",
            "tw": "Asia/Taipei",
            "il": "Asia/Jerusalem",
            "qa": "Asia/Qatar",
            "kw": "Asia/Kuwait",
            "om": "Asia/Muscat",
            "bh": "Asia/Bahrain",
            "jo": "Asia/Amman",
            "lb": "Asia/Beirut",
            "sy": "Asia/Damascus",
            "iq": "Asia/Baghdad",
            "ir": "Asia/Tehran",
            "af": "Asia/Kabul",
            "np": "Asia/Kathmandu",
            "lk": "Asia/Colombo",
            "mm": "Asia/Yangon",
            "kh": "Asia/Phnom_Penh",
            "la": "Asia/Vientiane",
            "mn": "Asia/Ulaanbaatar",
            "kz": "Asia/Almaty",
            "uz": "Asia/Tashkent",
            "tm": "Asia/Ashgabat",
            "kg": "Asia/Bishkek",
            "tj": "Asia/Dushanbe"
        }
        
        if country_code in special_timezones:
            return pytz.timezone(special_timezones[country_code])
        
        time_zones = pytz.country_timezones.get(country_code.upper())
        if time_zones:
            return pytz.timezone(time_zones[0])
        
        return pytz.timezone('UTC')
    except Exception as e:
        LOGGER.error(f"Timezone detection failed for {country_code}: {str(e)}")
        return pytz.timezone('UTC')

def get_country_name(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.name if country else country_code
    except Exception:
        return country_code

def create_weather_image(weather_data, output_path):
    current = weather_data["current"]
    
    try:
        timezone = get_timezone_from_country_code(weather_data['country_code'])
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
    
    font_url_bold_large = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf"
    font_url_bold = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans-Bold.ttf"
    font_url_regular = "https://cdn.jsdelivr.net/npm/dejavu-fonts-ttf@2.37.3/ttf/DejaVuSans.ttf"
    
    try:
        font_bold_large = download_font(font_url_bold_large, 120)
        font_bold = download_font(font_url_bold, 40)
        font_regular = download_font(font_url_regular, 38)
        font_small = download_font(font_url_regular, 36)
    except Exception:
        font_bold_large = ImageFont.load_default()
        font_bold = ImageFont.load_default()
        font_regular = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    main_title = "Current Weather"
    temp_text = f"{current['temperature']}°C"
    condition_text = current["weather"]
    realfeel_text = f"RealFeel® {current['feels_like']}°C"
    country_name = get_country_name(weather_data['country_code'])
    location_text = f"{weather_data['city']}, {country_name}"
    
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
                "weather": weather_code.get(hourly["weathercode"][i], "Unknown"),
                "humidity": hourly["relative_humidity_2m"][i],
                "precipitation_probability": hourly["precipitation_probability"][i]
            })
        
        current_date = datetime.now()
        daily_forecast = []
        for i in range(min(7, len(daily["temperature_2m_max"]))):
            day_date = (current_date + timedelta(days=i))
            daily_forecast.append({
                "date": day_date.strftime('%Y-%m-%d'),
                "day": day_date.strftime('%a, %b %d'),
                "min_temp": round(daily["temperature_2m_min"][i], 1),
                "max_temp": round(daily["temperature_2m_max"][i], 1),
                "weather": weather_code.get(daily["weathercode"][i], "Unknown"),
                "sunrise": daily["sunrise"][i].split("T")[1][:5],
                "sunset": daily["sunset"][i].split("T")[1][:5]
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
            timezone = get_timezone_from_country_code(country_code)
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
                "country_code": country_code,
                "coordinates": {
                    "latitude": lat,
                    "longitude": lon
                }
            },
            "current": {
                "time": current_time,
                "date": current_date_str,
                "temperature": round(current["temperature_2m"], 1),
                "feels_like": round(current["apparent_temperature"], 1),
                "humidity": current["relative_humidity_2m"],
                "wind_speed": round(current["wind_speed_10m"], 1),
                "wind_direction": current["wind_direction_10m"],
                "weather": weather_code.get(current["weathercode"], "Unknown"),
                "weather_code": current["weathercode"],
                "sunrise": daily["sunrise"][0].split("T")[1][:5],
                "sunset": daily["sunset"][0].split("T")[1][:5]
            },
            "hourly_forecast": hourly_forecast,
            "daily_forecast": daily_forecast,
            "air_quality": {
                "level": aqi_level,
                "pm2_5": round(aqi["pm2_5"][0], 2),
                "pm10": round(aqi["pm10"][0], 2),
                "carbon_monoxide": round(aqi["carbon_monoxide"][0], 2),
                "nitrogen_dioxide": round(aqi["nitrogen_dioxide"][0], 2),
                "ozone": round(aqi["ozone"][0], 2)
            },
            "maps": {
                "temperature": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=temperature&lat={lat}&lon={lon}&zoom=8",
                "clouds": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=clouds&lat={lat}&lon={lon}&zoom=8",
                "precipitation": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=precipitation&lat={lat}&lon={lon}&zoom=8",
                "wind": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=wind&lat={lat}&lon={lon}&zoom=8",
                "pressure": f"https://openweathermap.org/weathermap?basemap=map&cities=true&layer=pressure&lat={lat}&lon={lon}&zoom=8"
            },
            "lat": lat,
            "lon": lon,
            "country_code": country_code,
            "city": city.capitalize()
        }

@router.get("")
async def get_weather(area: str = None):
    area = area.strip() if area else ""
    
    LOGGER.info(f"Received weather request for area: {area}")
    
    if not area:
        LOGGER.warning("Missing area parameter in request")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": "Missing 'area' parameter. Usage: /wth?area=London"
            }
        )
    
    try:
        weather_data = await get_weather_data(area)
        
        if not weather_data:
            LOGGER.error(f"No weather data found for area: {area}")
            return JSONResponse(
                status_code=404,
                content={
                    "status": "error",
                    "message": f"Weather data unavailable for '{area}'. Please check the city name."
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
            weather_data["image_url"] = image_url
        else:
            weather_data["image_url"] = None
            weather_data["image_error"] = "Failed to upload image to hosting service"
        
        LOGGER.info(f"Successfully processed weather request for {area}")
        return JSONResponse(content=weather_data)
        
    except Exception as e:
        LOGGER.error(f"API error for {area}: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Internal server error. Please try again later.",
                "error": str(e)
            }
        )