from datetime import datetime


def format_date(date_str):
    """Format date string for display"""
    try:
        dt = datetime.fromisoformat(date_str)
        return dt.strftime("%d.%m.%Y %H:%M")
    except:
        return date_str


def format_profile_text(user, is_in_cooldown, cooldown_date):
    """Format profile information text"""
    # Format verification status
    email_status = "✅ Подтвержден" if user.get('confirm_email') else "❌ Не подтвержден"
    phone_status = "✅ Подтвержден" if user.get('confirm_phone') else "❌ Не подтвержден"
    verified_status = "✅ Подтвержден" if user.get('verified') else "❌ Не подтвержден администратором"

    # Format cooldown info
    cooldown_info = f"\n⏳ Вы не можете бронировать до: {cooldown_date.strftime('%d.%m.%Y %H:%M')}" if is_in_cooldown else ""

    # Format patronymic for display
    patronymic_display = f"\nОтчество: {user['patronymic']}" if user.get('patronymic') else ""

    # Add verification warning if not verified
    verification_warning = ""
    if not user.get('verified'):
        verification_warning = "\n\n⚠️ <b>Внимание:</b> Ваш аккаунт не подтвержден администратором. Вы не можете бронировать точки до подтверждения."

    # Create profile information message
    return (
        "👤 <b>Ваш профиль</b>\n\n"
        f"Имя: {user['first_name']}{patronymic_display}\n"
        f"Фамилия: {user['second_name']}\n"
        f"Email: {user['email']} ({email_status})\n"
        f"Телефон: {user['phone']} ({phone_status})\n"
        f"Статус аккаунта: {verified_status}\n"
        f"Дата регистрации: {format_date(user['cooldown'])}{cooldown_info}{verification_warning}\n"
    )
