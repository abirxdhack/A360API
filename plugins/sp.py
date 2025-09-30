from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
import requests
import re
import base64
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from utils import LOGGER
from urllib.parse import quote

router = APIRouter(prefix="/sp")

SPOTIFY_AUTH_URL = 'https://accounts.spotify.com/api/token'
SPOTIFY_API_BASE = 'https://api.spotify.com/v1'

def get_spotify_token():
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
    headers = {
        'Authorization': f'Basic {auth_b64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}
    try:
        response = requests.post(SPOTIFY_AUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Failed to get Spotify token: {str(e)}")
        raise ValueError('Unable to authenticate with Spotify')

def validate_spotify_url(url):
    if not url or not re.match(r'^https://open\.spotify\.com/track/[a-zA-Z0-9]+', url):
        LOGGER.error('Invalid Spotify track URL')
        raise ValueError('Valid Spotify track URL required')
    return url

def extract_track_id(url):
    if re.match(r'^[a-zA-Z0-9]{22}$', url):
        return url
    match = re.search(r'spotify\.com/track/([a-zA-Z0-9]{22})', url)
    if match:
        return match.group(1)
    LOGGER.error('Failed to extract track ID')
    raise ValueError('Invalid Spotify track ID or URL')

def get_track_metadata(track_id):
    token = get_spotify_token()
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.get(f"{SPOTIFY_API_BASE}/tracks/{track_id}", headers=headers)
        response.raise_for_status()
        track = response.json()
        return {
            'id': track['id'],
            'title': track['name'],
            'artists': [{'name': a['name'], 'id': a['id']} for a in track['artists']],
            'album': {
                'name': track['album']['name'],
                'id': track['album']['id'],
                'release_date': track['album']['release_date']
            },
            'duration': f"{track['duration_ms'] // 60000}:{(track['duration_ms'] % 60000) // 1000:02d}",
            'cover': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'url': track['external_urls']['spotify'],
            'isrc': track['external_ids'].get('isrc', 'N/A')
        }
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Failed to fetch track metadata: {str(e)}")
        raise ValueError('Unable to retrieve track data')

@router.get("/dl")
async def download(url: str = Query(..., description="Spotify track URL")):
    try:
        validated_url = validate_spotify_url(url)
        track_id = extract_track_id(validated_url)
        LOGGER.info(f"Processing track ID: {track_id}")
        track_data = get_track_metadata(track_id)
        LOGGER.info(f"Retrieved metadata for track: {track_data['title']}")
        check_endpoint = f"https://spotmp3.app/api/check-direct-download?url={quote(validated_url)}"
        LOGGER.info(f"Checking download availability: {check_endpoint}")
        check_response = requests.get(check_endpoint)
        check_response.raise_for_status()
        check_result = check_response.json()
        LOGGER.info(f"Download check result: {check_result}")
        response_data = {
            'status': 'success',
            'track': track_data,
            'download': None,
            'api_owner': '@ISmartCoder',
            'api_updates': 't.me/TheSmartDev'
        }
        if check_result.get('cached'):
            download_link = f"https://spotmp3.app/api/direct-download?url={quote(validated_url)}"
            LOGGER.info(f"Download link available: {download_link}")
            response_data['download'] = {'link': download_link}
        else:
            response_data['download'] = check_result
        return JSONResponse(content=response_data)
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Network error during download check: {str(e)}")
        raise HTTPException(status_code=500, detail={'status': 'error', 'message': str(e), 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
    except ValueError as e:
        LOGGER.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail={'status': 'error', 'message': str(e), 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
    except Exception as e:
        LOGGER.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail={'status': 'error', 'message': str(e), 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})

@router.get("/search")
async def search(q: str = Query(..., description="Search query for Spotify tracks")):
    if not q:
        LOGGER.error('Search query missing')
        raise HTTPException(status_code=400, detail={'status': 'error', 'message': 'Query required', 'example': '/sp/search?q=Song+Name', 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
    try:
        token = get_spotify_token()
        headers = {'Authorization': f'Bearer {token}'}
        params = {'q': q, 'type': 'track', 'limit': 5}
        response = requests.get(f"{SPOTIFY_API_BASE}/search", headers=headers, params=params)
        response.raise_for_status()
        tracks = response.json()['tracks']['items']
        if not tracks:
            LOGGER.info(f"No tracks found for query: {q}")
            raise HTTPException(status_code=404, detail={'status': 'error', 'message': 'No tracks found', 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
        response_data = [{
            'title': t['name'],
            'artist': ', '.join(a['name'] for a in t['artists']),
            'id': t['id'],
            'url': t['external_urls']['spotify'],
            'album': t['album']['name'],
            'release_date': t['album']['release_date'],
            'duration': f"{t['duration_ms'] // 60000}:{(t['duration_ms'] % 60000) // 1000:02d}",
            'cover': t['album']['images'][0]['url'] if t['album']['images'] else None
        } for t in tracks]
        LOGGER.info(f"Found {len(response_data)} tracks for query: {q}")
        return JSONResponse(content={'status': 'success', 'results': response_data, 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
    except requests.exceptions.RequestException as e:
        LOGGER.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail={'status': 'error', 'message': str(e), 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})
    except Exception as e:
        LOGGER.error(f"Unexpected search error: {str(e)}")
        raise HTTPException(status_code=500, detail={'status': 'error', 'message': str(e), 'api_owner': '@ISmartCoder', 'api_updates': 't.me/TheSmartDev'})