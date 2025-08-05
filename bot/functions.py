import re
from bot.constants import REGIONS, GENDER, PROFESSIONS


# 📌 Telefon raqam formatlash
def format_phone_number(phone: str) -> str | None:
    clean = re.sub(r'\D', '', phone)
    if len(clean) == 12 and clean.startswith('998'):
        return '+' + clean
    elif len(clean) == 9 and clean.startswith('90'):
        return '+998' + clean
    elif len(clean) == 10 and clean.startswith('9'):
        return '+998' + clean[1:]
    return None

def get_region_code_by_name(region_name: str) -> str | None:
    for code, name in REGIONS:
        if name.lower() == region_name.lower():
            return code
    return None

def get_gender_code_by_name(gender_name: str) -> str | None:
    for code, name in GENDER:
        if name.lower() == gender_name.lower():
            return code
    return None

def get_profession_code_by_name(profession_name: str) -> str | None:
    for code, name in PROFESSIONS:
        if name.lower() == profession_name.lower():
            return code
    return None