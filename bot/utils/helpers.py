import re
from bot.constants import REGIONS, GENDER, PROFESSIONS




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