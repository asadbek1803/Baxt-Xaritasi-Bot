import os
import re


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