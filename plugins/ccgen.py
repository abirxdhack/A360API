from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re
import random
import pycountry
from typing import Optional
from smartbindb import SmartBinDB
from utils import LOGGER

router = APIRouter(prefix="/ccgen")
smartdb = SmartBinDB()

class CardParams(BaseModel):
    bin: str
    month: Optional[str] = None
    year: Optional[str] = None
    cvv: Optional[str] = None
    amount: Optional[int] = 10

def is_amex_bin(bin_str: str) -> bool:
    clean_bin = bin_str.replace('x', '').replace('X', '')
    if len(clean_bin) >= 2:
        return clean_bin[:2] in ['34', '37']
    return False

def luhn_algorithm(card_number: str) -> bool:
    digits = [int(d) for d in str(card_number) if d.isdigit()]
    if not digits or len(digits) < 13:
        return False
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 1:
            doubled = digit * 2
            if doubled > 9:
                doubled = doubled // 10 + doubled % 10
            checksum += doubled
        else:
            checksum += digit
    return checksum % 10 == 0

def calculate_luhn_check_digit(partial_card_number: str) -> int:
    digits = [int(d) for d in str(partial_card_number) if d.isdigit()]
    if not digits:
        return 0
    checksum = 0
    for i, digit in enumerate(reversed(digits)):
        if i % 2 == 0:
            doubled = digit * 2
            if doubled > 9:
                doubled = doubled // 10 + doubled % 10
            checksum += doubled
        else:
            checksum += digit
    check_digit = (10 - (checksum % 10)) % 10
    return check_digit

def generate_credit_card(bin: str, amount: int, month: Optional[str] = None, year: Optional[str] = None, cvv: Optional[str] = None) -> list:
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 15 if is_amex else 16
    cvv_length = 4 if is_amex else 3
    bin_digits = re.sub(r'[^0-9]', '', bin)
    if len(bin_digits) >= target_length:
        return []
    for _ in range(amount):
        card_body = bin_digits
        remaining_digits = target_length - len(card_body) - 1
        if remaining_digits < 0:
            continue
        for _ in range(remaining_digits):
            card_body += str(random.randint(0, 9))
        check_digit = calculate_luhn_check_digit(card_body)
        card_number = card_body + str(check_digit)
        if not luhn_algorithm(card_number):
            continue
        card_month = month if month is not None else f"{random.randint(1, 12):02d}"
        card_year = year if year is not None else str(random.randint(2025, 2035))
        card_cvv = cvv if cvv is not None else ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
        formatted_card = f"{card_number}|{card_month}|{card_year}|{card_cvv}"
        cards.append(formatted_card)
    return cards

def generate_custom_cards(bin: str, amount: int, month: Optional[str] = None, year: Optional[str] = None, cvv: Optional[str] = None) -> list:
    cards = []
    is_amex = is_amex_bin(bin)
    target_length = 15 if is_amex else 16
    cvv_length = 4 if is_amex else 3
    bin_digits = re.sub(r'[^0-9]', '', bin)
    if len(bin_digits) >= target_length:
        return []
    for _ in range(amount):
        card_body = bin_digits
        remaining_digits = target_length - len(card_body) - 1
        if remaining_digits < 0:
            continue
        for _ in range(remaining_digits):
            card_body += str(random.randint(0, 9))
        check_digit = calculate_luhn_check_digit(card_body)
        card_number = card_body + str(check_digit)
        if not luhn_algorithm(card_number):
            continue
        card_month = month if month is not None else f"{random.randint(1, 12):02d}"
        card_year = year if year is not None else str(random.randint(2025, 2035))
        card_cvv = cvv if cvv is not None else ''.join([str(random.randint(0, 9)) for _ in range(cvv_length)])
        formatted_card = f"{card_number}|{card_month}|{card_year}|{card_cvv}"
        cards.append(formatted_card)
    return cards

def get_flag(country_code: str) -> tuple:
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        if not country:
            raise ValueError("Invalid country code")
        country_name = country.name
        flag_emoji = chr(0x1F1E6 + ord(country_code[0]) - ord('A')) + chr(0x1F1E6 + ord(country_code[1]) - ord('A'))
        return country_name, flag_emoji
    except Exception:
        return "Unknown Country", "🇺🇳"

async def get_bin_info(bin: str) -> dict:
    clean_bin = bin.replace('x', '').replace('X', '')[:6]
    try:
        result = await smartdb.get_bin_info(clean_bin)
        if result.get("status") == "SUCCESS" and result.get("data"):
            bin_data = result["data"][0]
            bank = bin_data.get("issuer", "Unknown Bank")
            country_code = bin_data.get("country_code", "UN")
            country_name, flag_emoji = get_flag(country_code)
            scheme = bin_data.get("brand", "Unknown Scheme")
            card_type = bin_data.get("type", "Unknown Type")
            bin_info = f"{scheme} - {card_type}"
            return {
                'Bank': bank,
                'Country': f"{country_name} {flag_emoji}",
                'BIN Info': bin_info
            }
        else:
            return {
                'Bank': 'Unknown Bank',
                'Country': 'Unknown Country 🇺🇳',
                'BIN Info': 'Unknown Scheme - Unknown Type'
            }
    except Exception as e:
        LOGGER.error(f"Error getting BIN info: {str(e)}")
        return {
            'Bank': 'Unknown Bank',
            'Country': 'Unknown Country 🇺🇳',
            'BIN Info': 'Unknown Scheme - Unknown Type'
        }

def parse_input(user_input: str, amount: int = 10) -> tuple:
    bin = None
    month = None
    year = None
    cvv = None
    parsed_amount = amount
    if not user_input:
        return None, None, None, None, None
    digits_x_pattern = r'([0-9xX]+)(?:[|:/]([0-9]{2}|xx)?)?(?:[|:/]([0-9]{2,4}|xx|xxxx)?)?(?:[|:/]([0-9]{3,4}|xxx|xxxx|rnd)?)?'
    matches = re.findall(digits_x_pattern, user_input, re.IGNORECASE)
    if matches:
        for match in matches:
            bin_part = ''.join(filter(lambda x: x.isdigit() or x in 'xX', match[0]))
            digits_only = re.sub(r'[^0-9]', '', bin_part)
            if 6 <= len(digits_only) <= 16:
                bin = bin_part
                if len(match) > 1 and match[1]:
                    month = match[1]
                if len(match) > 2 and match[2]:
                    year = match[2]
                if len(match) > 3 and match[3]:
                    cvv = match[3]
                break
    if not bin:
        return None, None, None, None, None
    parts = re.split(r'[|:/]', user_input)
    bin_part = parts[0] if parts else ""
    digits_only = re.sub(r'[^0-9xX]', '', bin_part)
    if digits_only:
        if 6 <= len(re.sub(r'[^0-9]', '', digits_only)) <= 16:
            bin = digits_only
        else:
            return None, None, None, None, None
    else:
        return None, None, None, None, None
    if len(parts) > 1:
        if parts[1].lower() == 'xx':
            month = None
        elif parts[1].isdigit() and len(parts[1]) == 2:
            month_val = int(parts[1])
            if 1 <= month_val <= 12:
                month = f"{month_val:02d}"
    if len(parts) > 2:
        if parts[2].lower() in ['xx', 'xxxx']:
            year = None
        elif parts[2].isdigit():
            year_str = parts[2]
            if len(year_str) == 2:
                year_int = int(year_str)
                if year_int >= 25:
                    year = f"20{year_str}"
            elif len(year_str) == 4:
                year_int = int(year_str)
                if 2025 <= year_int <= 2099:
                    year = year_str
    if len(parts) > 3 and parts[3]:
        if parts[3].lower() in ['xxx', 'xxxx', 'rnd']:
            cvv = None
        elif parts[3].isdigit():
            cvv = parts[3]
    return bin, month, year, cvv, parsed_amount

@router.get("")
async def generate_cards(bin: str, month: Optional[str] = None, year: Optional[str] = None, cvv: Optional[str] = None, amount: Optional[int] = 10):
    CC_GEN_LIMIT = 2000
    try:
        if not bin:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "BIN parameter is required",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        if amount < 1 or amount > CC_GEN_LIMIT:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Invalid amount: Must be between 1 and {CC_GEN_LIMIT}",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        user_input = bin
        if month:
            user_input += f"|{month}"
        if year:
            user_input += f"|{year}"
        if cvv:
            user_input += f"|{cvv}"
        bin, month, year, cvv, parsed_amount = parse_input(user_input, amount)
        if not bin:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Invalid BIN: Must be 6-15 digits or up to 16 digits with 'x'",
                    "api_owner": "@ISmartCoder",
                    "api_updates": "t.me/abirxdhackz"
                }
            )
        if cvv is not None:
            is_amex = is_amex_bin(bin)
            if is_amex and len(cvv) != 4:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Invalid CVV format: CVV must be 4 digits for AMEX",
                        "api_owner": "@ISmartCoder",
                        "api_updates": "t.me/abirxdhackz"
                    }
                )
            elif not is_amex and len(cvv) != 3:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "Invalid CVV format: CVV must be 3 digits for non-AMEX",
                        "api_owner": "@ISmartCoder",
                        "api_updates": "t.me/abirxdhackz"
                    }
                )
        cards = generate_credit_card(bin, parsed_amount, month, year, cvv)
        bin_info = await get_bin_info(bin)
        response = {
            "status": "success",
            "bin": bin,
            "amount": parsed_amount,
            "cards": cards,
            "Bank": bin_info['Bank'],
            "Country": bin_info['Country'],
            "BIN Info": bin_info['BIN Info'],
            "api_owner": "@ISmartCoder",
            "api_updates": "t.me/abirxdhackz"
        }
        return JSONResponse(content=response)
    except ValueError as e:
        LOGGER.error(f"Invalid input for CC generation: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "status": "error",
                "message": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )
    except Exception as e:
        LOGGER.error(f"Error processing CC generation request: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": str(e),
                "api_owner": "@ISmartCoder",
                "api_updates": "t.me/abirxdhackz"
            }
        )