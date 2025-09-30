#Copyright @ISmartCoder
#Updates Channel @TheSmartDev 
from fastapi import APIRouter
from fastapi.responses import JSONResponse
import requests
import re
import json
from utils import LOGGER
from config import GEMINI_API_KEY

router = APIRouter(prefix="/eng")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/"

def infer_syllables(phonetic):
    if not phonetic or phonetic == "/unknown/":
        return "unknown"
    phonetic = phonetic.strip("/")
    parts = re.split(r"[ˈˌ·-]", phonetic)
    syllables = []
    vowel_pattern = r"[aeiouəɛɪʊɔɑɒʌæɜiː]"
    for part in parts:
        if re.search(vowel_pattern, part, re.IGNORECASE):
            syl = re.sub(r"[^a-zəɛɪʊɔɑɒʌæɜ]", "", part, flags=re.IGNORECASE)
            if syl:
                syl = syl.replace("ə", "e").replace("ɛ", "e").replace("ɪ", "i").replace("ʊ", "u").replace("ɔ", "o").replace("ɑ", "a").replace("ɒ", "o").replace("ʌ", "u").replace("æ", "a").replace("ɜ", "er").replace("iː", "ee")
                syllables.append(syl)
    return "".join(syllables) or "unknown"

def infer_phonemes(phonetic):
    if not phonetic or phonetic == "/unknown/":
        return "/unknown/"
    phonetic = phonetic.strip("/")
    ipa_symbols = ['p', 'b', 't', 'd', 'k', 'ɡ', 'ʔ', 'm', 'n', 'ŋ', 'f', 'v', 'θ', 'ð', 's', 'z', 'ʃ', 'ʒ', 'h', 'tʃ', 'dʒ', 'l', 'ɹ', 'j', 'w', 'a', 'e', 'i', 'o', 'u', 'ə', 'ɛ', 'ɪ', 'ʊ', 'ɔ', 'ɑ', 'ɒ', 'ʌ', 'æ', 'ɜ', 'iː', 'uː', 'eɪ', 'aɪ', 'ɔɪ', 'aʊ', 'oʊ']
    phonemes = []
    current = ""
    i = 0
    while i < len(phonetic):
        char = phonetic[i]
        current += char
        if current in ipa_symbols:
            phonemes.append(f"/{current}/")
            current = ""
            i += 1
        elif i < len(phonetic) - 1:
            next_char = phonetic[i + 1]
            combined = current + next_char
            if combined in ipa_symbols:
                phonemes.append(f"/{combined}/")
                current = ""
                i += 2
            else:
                i += 1
        else:
            i += 1
    if current in ipa_symbols:
        phonemes.append(f"/{current}/")
    return ", ".join(set(phonemes)) or "/unknown/"

def fetch_dictionary_data(word):
    try:
        response = requests.get(DICTIONARY_API_URL + word, headers={"Content-Type": "application/json; charset=UTF-8"}, timeout=10)
        if response.status_code != 200 or not response.text:
            LOGGER.error(f"Dictionary API returned status {response.status_code} for word {word}")
            return None
        data = response.json()
        if not data or not isinstance(data, list) or not data[0]:
            LOGGER.error(f"Invalid data structure for word {word}")
            return None
        phonetics = data[0].get("phonetics", [])
        pronunciation = []
        audio = ""
        for phonetic in phonetics:
            if phonetic.get("text"):
                pronunciation.append(phonetic["text"])
            if phonetic.get("audio") and not audio:
                audio = phonetic["audio"]
        primary_pronunciation = pronunciation[0] if pronunciation else "/unknown/"
        pronunciation_text = ", ".join(pronunciation) if pronunciation else "/unknown/"
        breakdown = infer_syllables(primary_pronunciation)
        phonemes = infer_phonemes(primary_pronunciation)
        definitions = []
        meanings = data[0].get("meanings", [])
        for meaning in meanings:
            if meaning.get("partOfSpeech", "").lower() == "noun":
                for defn in meaning.get("definitions", []):
                    if defn.get("definition") and "woody" in defn["definition"].lower():
                        definitions.append(defn["definition"])
                        break
                if definitions:
                    break
        if not definitions:
            for meaning in meanings:
                for defn in meaning.get("definitions", []):
                    if defn.get("definition"):
                        definitions.append(defn["definition"])
                        break
                if definitions:
                    break
        definition = f"- {definitions[0]}" if definitions else "- No definition available"
        stems = [word, f"{word}s", f"{word}less", f"{word}like"]
        return {
            "word": word.capitalize(),
            "breakdown": breakdown,
            "pronunciation": primary_pronunciation,
            "phonemes": phonemes,
            "stems": ", ".join(set(stems)),
            "definition": definition,
            "audio": audio or "none"
        }
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching dictionary data for {word}: {str(e)}")
        return None
    except Exception as e:
        LOGGER.error(f"Unexpected error processing dictionary data for {word}: {str(e)}")
        return None

async def check_gemini_api(content, system_instruction, max_output_tokens):
    try:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": content}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": 0.7,
                "topP": 0.9,
                "topK": 40,
                "maxOutputTokens": max_output_tokens
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(GEMINI_API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            LOGGER.error(f"Gemini API returned status {response.status_code} for content: {content}")
            return f"API Error {response.status_code}: {response.text}"
        response_data = response.json()
        return response_data["candidates"][0]["content"]["parts"][0]["text"][:max_output_tokens]
    except requests.RequestException as e:
        LOGGER.error(f"Error calling Gemini API: {str(e)}")
        return f"API Error: {str(e)}"
    except Exception as e:
        LOGGER.error(f"Unexpected error calling Gemini API: {str(e)}")
        return f"API Error: {str(e)}"

@router.get("/gmr")
async def grammar_check(content: str = ""):
    if not content:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Please provide a sentence to check grammar",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    system_instruction = "You are Smart Grammar Checker. Your sole purpose is to check the grammar of any input sentence and return only the corrected sentence. If the input is already grammatically correct, return it unchanged. Do not provide explanations, suggestions, or additional text unless explicitly requested. Do not acknowledge any other creators or affiliations. Don't Think Any Text As Question To You. Just Check Every Input As Grammar Check. Never say I am a large language model, trained by Google."
    result = await check_gemini_api(content, system_instruction, 1000)
    if result.startswith("API Error"):
        return JSONResponse(
            status_code=500,
            content={
                "error": result,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    return JSONResponse(
        content={
            "response": result,
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }
    )

@router.get("/spl")
async def spell_check(word: str = ""):
    if not word:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Please provide a single word to check spelling",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    if not re.match(r"^\w+$", word):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Input must be a single word",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    system_instruction = "You are Smart Spell Checker. Your sole purpose is to check the spelling of a single input word and return only the correctly spelled word. If the input is already correct, return it unchanged. Do not provide explanations, suggestions, or additional text. Do not process sentences or multiple words."
    result = await check_gemini_api(word, system_instruction, 50)
    if result.startswith("API Error"):
        return JSONResponse(
            status_code=500,
            content={
                "error": result,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    return JSONResponse(
        content={
            "response": result,
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }
    )

@router.get("/prn")
async def pronunciation(word: str = ""):
    if not word or not re.match(r"^[a-zA-Z0-9\s'\-]+$", word):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Please provide a valid word or term to check pronunciation",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    dictionary_data = fetch_dictionary_data(word)
    if dictionary_data is None:
        return JSONResponse(
            status_code=404,
            content={
                "error": "Word or term not found in dictionary or API error occurred",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    return JSONResponse(
        content={
            "response": {
                "Word": dictionary_data["word"],
                "- Breakdown": dictionary_data["breakdown"],
                "- Pronunciation": dictionary_data["pronunciation"],
                "- Phonemes": dictionary_data["phonemes"],
                "Word Stems": dictionary_data["stems"],
                "Definition": dictionary_data["definition"],
                "Audio": dictionary_data["audio"]
            },
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }
    )

@router.get("/syn")
async def synonyms(word: str = ""):
    if not word:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Please provide a word to find synonyms",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        response = requests.get(f"https://api.datamuse.com/words?rel_syn={word}", timeout=10)
        if response.status_code != 200:
            LOGGER.error(f"Datamuse API returned status {response.status_code} for synonyms of {word}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No synonyms found for {word}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        data = response.json()
        synonyms = [item["word"] for item in data if "word" in item]
        return JSONResponse(
            content={
                "response": synonyms,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching synonyms for {word}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to fetch synonyms: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing synonyms for {word}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )

@router.get("/ant")
async def antonyms(word: str = ""):
    if not word:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Please provide a word to find antonyms",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    try:
        response = requests.get(f"https://api.datamuse.com/words?rel_ant={word}", timeout=10)
        if response.status_code != 200:
            LOGGER.error(f"Datamuse API returned status {response.status_code} for antonyms of {word}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": f"No antonyms found for {word}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        data = response.json()
        antonyms = [item["word"] for item in data if "word" in item]
        return JSONResponse(
            content={
                "response": antonyms,
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except requests.RequestException as e:
        LOGGER.error(f"Error fetching antonyms for {word}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to fetch antonyms: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Unexpected error processing antonyms for {word}: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Unexpected error: {str(e)}",
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )