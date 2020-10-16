import re

allowed_chars = re.compile(r'^[A-Za-z0-9_-]+$')


# yes extensions will be provided

def validate_filename(s: str):
    return re.fullmatch(allowed_chars, s) is not None


__all__ = ['validate_filename']
