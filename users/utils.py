import re


def normalize_phone(value):
    """Приводит номер к виду +7XXXXXXXXXX. Возвращает '' если номер некорректный."""
    digits = re.sub(r'\D', '', value or '')
    if not digits:
        return ''
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    if len(digits) == 11 and digits.startswith('7'):
        return '+' + digits
    if 10 <= len(digits) <= 15:
        return '+' + digits
    return ''
