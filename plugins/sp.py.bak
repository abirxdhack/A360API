from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
import t.me/abirxdhackz
from bs4 import BeautifulSoup
import json
import brotli
import gzip
import zstandard
import re
import base64
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from utils import LOGGER

router = APIRouter(prefix="/sp")

def decompress_response(response):
    encodings = response.headers.get('content-encoding', '').split(',')
    data = response.content
    if not encodings or encodings == ['']:
        return response.text
    for encoding in encodings:
        encoding = encoding.strip()
        try:
            if encoding == 'br':
                data = brotli.decompress(data)
            elif encoding == 'gzip':
                data = gzip.decompress(data)
            elif encoding == 'zstd':
                data = zstandard.ZstdDecompressor().decompress(data)
        except:
            return response.text
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        return response.text

def get_csrf_token(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    meta_tag = soup.find('meta', {'name': 'csrf-token'})
    return meta_tag['content'] if meta_tag else None

def get_track_info(spotify_url, session, csrf_token):
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf_token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Origin': 'https://spotdl.io',
        'Referer': 'https://spotdl.io/',
        'Accept-Encoding': 'gzip, deflate, br, zstd'
    }
    payload = {'spotify_url': spotify_url}
    try:
        response = session.post('https://spotdl.io/getTrackData', headers=headers, json=payload)
        response.raise_for_status()
        return json.loads(decompress_response(response))
    except (requests.RequestException, json.JSONDecodeError) as e:
        LOGGER.error(f"Failed to retrieve track info for URL {spotify_url}: {str(e)}")
        return None

def get_download_url(spotify_url, session, csrf_token):
    headers = {
        'Accept': '*/*',
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrf_token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Origin': 'https://spotdl.io',
        'Referer': 'https://spotdl.io/',
        'Accept-Encoding': 'gzip, deflate, br, zstd'
    }
    payload = {'urls': spotify_url}
    try:
        response = session.post('https://spotdl.io/convert', headers=headers, json=payload)
        response.raise_for_status()
        return json.loads(decompress_response(response))
    except (requests.RequestException, json.JSONDecodeError) as e:
        LOGGER.error(f"Failed to retrieve download URL for {spotify_url}: {str(e)}")
        return None

def get_spotify_access_token():
    token_url = 'https://accounts.spotify.com/api/token'
    auth_header = base64.b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_header}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status()
        return response.json().get('access_token')
    except requests.RequestException as e:
        LOGGER.error(f"Failed to authenticate with Spotify: {str(e)}")
        return None

def search_spotify(query, access_token, limit=30, offset=0):
    search_url = 'https://api.spotify.com/v1/search'
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'q': query, 'type': 'track', 'limit': limit, 'offset': offset}
    try:
        response = requests.get(search_url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        LOGGER.error(f"Failed to search Spotify for query '{query}': {str(e)}")
        return None

@router.get("/dl")
async def download_track(url: str = None):
    if not url or not re.match(r'^https://open\.spotify\.com/track/[a-zA-Z0-9]+$', url):
        return JSONResponse(
            status_code=400,
            content={
                'error': 'Invalid Spotify track URL',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    scraper = t.me/abirxdhackz.create_scraper()
    try:
        response = scraper.get('https://spotdl.io')
        response.raise_for_status()
        csrf_token = get_csrf_token(response.text)
    except requests.RequestException as e:
        LOGGER.error(f"Failed to retrieve CSRF token: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to retrieve CSRF token',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    if not csrf_token:
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to retrieve CSRF token',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    track_info = get_track_info(url, scraper, csrf_token)
    if not track_info:
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to retrieve track information',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    download_data = get_download_url(url, scraper, csrf_token)
    if not download_data or download_data.get('error', True):
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to retrieve download URL',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    return JSONResponse(
        content={
            'name': track_info.get('name', 'Unknown'),
            'artists': [artist.get('name', 'Unknown') for artist in track_info.get('artists', [])],
            'album_image': track_info.get('album', {}).get('images', [{}])[0].get('url', 'Unknown'),
            'duration_seconds': track_info.get('duration_ms', 0) // 1000,
            'explicit': track_info.get('explicit', False),
            'download_url': download_data.get('url', 'Unknown'),
            'api_owner': '@ISmartCoder',
            'api_updates': 't.me/TheSmartDev'
        }
    )

@router.get("/search")
async def search_tracks(q: str = None, limit: int = 30, offset: int = 0):
    if not q:
        return JSONResponse(
            status_code=400,
            content={
                'error': 'Missing query parameter (q)',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    access_token = get_spotify_access_token()
    if not access_token:
        return JSONResponse(
            status_code=500,
            content={
                'error': 'Failed to authenticate with Spotify',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    if limit > 50:
        first_limit = 50
        second_limit = limit - 50
        first_offset = offset
        second_offset = offset + 50
        first_results = search_spotify(q, access_token, first_limit, first_offset)
        second_results = search_spotify(q, access_token, second_limit, second_offset)
        if not first_results or not second_results:
            return JSONResponse(
                status_code=500,
                content={
                    'error': 'Failed to retrieve search results',
                    'api_owner': '@ISmartCoder',
                    'api_updates': 't.me/TheSmartDev'
                }
            )
        tracks = first_results.get('tracks', {}).get('items', []) + second_results.get('tracks', {}).get('items', [])
    else:
        search_results = search_spotify(q, access_token, limit, offset)
        if not search_results:
            return JSONResponse(
                status_code=500,
                content={
                    'error': 'Failed to retrieve search results',
                    'api_owner': '@ISmartCoder',
                    'api_updates': 't.me/TheSmartDev'
                }
            )
        tracks = search_results.get('tracks', {}).get('items', [])

    if not tracks:
        return JSONResponse(
            status_code=404,
            content={
                'error': 'No tracks found',
                'api_owner': '@ISmartCoder',
                'api_updates': 't.me/TheSmartDev'
            }
        )

    track_details = []
    for index, track in enumerate(tracks):
        duration = f"{track.get('duration_ms', 0) // 60000}:{(track.get('duration_ms', 0) % 60000 // 1000):02d}"
        track_details.append({
            'Title': track.get('name'),
            'Artist': ', '.join(artist.get('name') for artist in track.get('artists', [])),
            'Duration': duration,
            'Id': index + 1,
            'TrackURL': track.get('external_urls', {}).get('spotify'),
            'Cover_Art': track.get('album', {}).get('images', [{}])[0].get('url', 'No image available'),
            'Release Date': track.get('album', {}).get('release_date')
        })

    return JSONResponse(
        content={
            'api_owner': '@ISmartCoder',
            'api_updates': 't.me/TheSmartDev',
            'tracks': track_details
        }
    )