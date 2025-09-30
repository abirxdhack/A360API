#Copyright @ISmartCoder
#Updates Channel @abirxdhackz 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import aiohttp
from config import OPENAI_API_KEY, GEMINI_API_KEY, GROQ_API_KEY, REPLICATE_API_TOKEN
from utils import LOGGER

router = APIRouter(prefix="/ai")
SMARTAI_API_URL = "https://abirthetech.serv00.net/ai.php"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"  # Assuming Groq's OpenAI-compatible endpoint
CLAUDE_API_URL = "https://api.replicate.com/v1/models/anthropic/claude-3.7-sonnet/predictions"

@router.get("/smartai")
async def smartai(prompt: str = ""):
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'prompt' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{SMARTAI_API_URL}?prompt={aiohttp.formdata.urlencode({'prompt': prompt})}") as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get("response", "No response received")
                    if len(response_text) > 4000:
                        response_text = response_text[:4000]
                    return JSONResponse(
                        content={
                            "success": True,
                            "response": response_text,
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                else:
                    LOGGER.error(f"SmartAI API request failed with status {response.status}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": "**❌Sorry Bro SmartAI API Error**",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
    except Exception as e:
        LOGGER.error(f"SmartAI error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "**❌Sorry Bro SmartAI API Error**",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/gpt")
async def gpt(prompt: str = ""):
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'prompt' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    if not OPENAI_API_KEY or not OPENAI_API_KEY.strip():
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "OpenAI API key not configured",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        async with aiohttp.ClientSession() as session:
            url = OPENAI_API_URL
            headers = {
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 100,
                "n": 1,
                "stop": None,
                "temperature": 0.5
            }
            async with session.post(url, headers=headers, json=data) as response:
                LOGGER.info(f"GPT API response status: {response.status}, headers: {dict(response.headers)}")
                if response.status == 200:
                    json_response = await response.json()
                    response_text = json_response['choices'][0]['message']['content']
                    return JSONResponse(
                        content={
                            "success": True,
                            "response": response_text,
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                else:
                    error_text = await response.text()
                    LOGGER.error(f"GPT API request failed with status {response.status}: {error_text}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": "GPT API request failed",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
    except Exception as e:
        LOGGER.error(f"GPT error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"GPT processing failed: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/gemi")
async def gemi(prompt: str = ""):
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'prompt' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    if not GEMINI_API_KEY or not GEMINI_API_KEY.strip():
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Gemini API key not configured",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": prompt}]}
                ],
                "systemInstruction": {"parts": [{"text": ""}]},
                "generationConfig": {
                    "temperature": 1,
                    "topP": 0.95,
                    "topK": 40,
                    "maxOutputTokens": 1024
                }
            }
            headers = {"Content-Type": "application/json"}
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received")
                    response_text = response_text[:3000]  # Limit to 3000 characters
                    return JSONResponse(
                        content={
                            "success": True,
                            "response": response_text,
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                else:
                    LOGGER.error(f"Gemini API request failed with status {response.status}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": f"Gemini API error {response.status}",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
    except Exception as e:
        LOGGER.error(f"Gemini error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Gemini processing failed: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/dep")
async def dep(prompt: str = ""):
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'prompt' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    if not GROQ_API_KEY or not GROQ_API_KEY.strip():
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Groq API key not configured",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        async with aiohttp.ClientSession() as session:
            url = GROQ_API_URL
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "deepseek-r1-distill-llama-70b",  
                "messages": [
                    {"role": "system", "content": "Reply in the same language as the user's message But Always Try To Answer Shortly"},
                    {"role": "user", "content": prompt}
                ]
            }
            async with session.post(url, headers=headers, json=data) as response:
                LOGGER.info(f"DeepSeek API response status: {response.status}, headers: {dict(response.headers)}")
                if response.status == 200:
                    data = await response.json()
                    response_text = data.get("choices", [{}])[0].get("message", {}).get("content", "Sorry DeepSeek API Dead")
                    return JSONResponse(
                        content={
                            "success": True,
                            "response": response_text,
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                else:
                    error_text = await response.text()
                    LOGGER.error(f"DeepSeek API request failed with status {response.status}: {error_text}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": "DeepSeek API request failed",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
    except Exception as e:
        LOGGER.error(f"DeepSeek error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"DeepSeek processing failed: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/cla")
async def cla(prompt: str = ""):
    if not prompt:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": "Missing 'prompt' parameter",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    if not REPLICATE_API_TOKEN or not REPLICATE_API_TOKEN.strip():
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Replicate API token not configured",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        async with aiohttp.ClientSession() as session:
            url = CLAUDE_API_URL
            headers = {
                "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
                "Content-Type": "application/json",
                "Prefer": "wait"
            }
            payload = {
                "input": {
                    "prompt": prompt,
                    "max_tokens": 8192,
                    "system_prompt": "",
                    "extended_thinking": False,
                    "max_image_resolution": 0.5,
                    "thinking_budget_tokens": 1024
                }
            }
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 201:
                    result = await response.json()
                    output = result.get("output", [])
                    response_text = ''.join(output).strip() if isinstance(output, list) else str(output)
                    return JSONResponse(
                        content={
                            "success": True,
                            "response": response_text,
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
                else:
                    LOGGER.error(f"Claude API request failed with status {response.status}")
                    return JSONResponse(
                        status_code=500,
                        content={
                            "success": False,
                            "error": f"Claude API error {response.status}",
                            "api_owner": "@ISmartCoder",
                            "api_updates": "t.me/abirxdhackz"
                        }
                    )
    except Exception as e:
        LOGGER.error(f"Claude error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Claude processing failed: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
              )
