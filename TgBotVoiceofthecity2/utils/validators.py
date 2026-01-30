import re

def validate_name(name):
    """Validate name (first name or last name)"""
    return bool(re.fullmatch(r"[А-Яа-яЁё]{2,}", name.strip()))

def validate_patronymic(patronymic):
    """Validate patronymic (middle name)"""
    return bool(re.fullmatch(r"[А-Яа-яЁё]+", patronymic.strip()))

def validate_email(email):
    """Validate email address"""
    return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", email))

def validate_phone(phone):
    """Validate phone number"""
    return bool(re.fullmatch(r'^(?:\+7|8)(?:\d{10}|[348]\d{9}|[3489]\d{8}|[3489]\d{7})$|^(?:\+7|7)[349]\d{9}$',phone))

def validate_password(password):
    """Validate password"""
    return len(password) >= 8
