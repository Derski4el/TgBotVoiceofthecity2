from Settings.config import ADMIN_TELEGRAM_IDS
from datetime import datetime


def is_admin(telegram_id):
    """Check if a user is an admin based on their Telegram ID"""
    return str(telegram_id) in ADMIN_TELEGRAM_IDS


def format_users_table(users):
    """Format users list as an HTML table"""
    if not users:
        return "Пользователи не найдены."

    # Start HTML table
    table = "<b>Список пользователей:</b>\n\n"
    table += "<pre>"

    # Table header
    header = f"{'ID':<10} | {'Имя':<15} | {'Фамилия':<15} | {'Email':<20} | {'Телефон':<15} | {'Подтв.':<6}"
    table += header + "\n"
    table += "-" * len(header) + "\n"

    # Table rows
    for user in users:
        # Truncate ID to first 8 characters for better display
        user_id = user.get('id', 'N/A')
        if isinstance(user_id, str) and len(user_id) > 8:
            user_id = user_id[:8] + "..."

        # Format verification status
        verified_status = "✅" if user.get('verified') else "❌"

        row = f"{user_id:<10} | {user.get('first_name', 'N/A'):<15} | {user.get('second_name', 'N/A'):<15} | {user.get('email', 'N/A'):<20} | {user.get('phone', 'N/A'):<15} | {verified_status:<6}"
        table += row + "\n"

    table += "</pre>"
    return table


def format_users_data(users):
    """Format users data for Jinja2 template"""
    if not users:
        return []

    result = []
    for user in users:
        # Format cooldown date
        cooldown = user.get('cooldown', 'N/A')
        try:
            cooldown_date = datetime.fromisoformat(cooldown)
            cooldown = cooldown_date.strftime('%d.%m.%Y %H:%M')
        except (ValueError, TypeError):
            pass

        result.append({
            'id': user.get('id', 'N/A'),
            'first_name': user.get('first_name', 'N/A'),
            'patronymic': user.get('patronymic', ''),
            'second_name': user.get('second_name', 'N/A'),
            'email': user.get('email', 'N/A'),
            'confirm_email': user.get('confirm_email', False),
            'phone': user.get('phone', 'N/A'),
            'confirm_phone': user.get('confirm_phone', False),
            'role_id': user.get('role_id', 'N/A'),
            'telegram_id': user.get('telegram_id', 'Нет'),
            'saved_telegram_id': user.get('saved_telegram_id', 'Нет'),
            'cooldown': cooldown,
            'agreements_status': user.get('agreements_status', False),
            'verified': user.get('verified', False)
        })

    return result


def format_bookings_data(bookings):
    """Format bookings data for Jinja2 template"""
    if not bookings:
        return []

    result = []
    for booking in bookings:
        # Format date
        date = booking.get('date', 'Не указана')
        try:
            date_obj = datetime.fromisoformat(date)
            date = date_obj.strftime('%d.%m.%Y')
        except (ValueError, TypeError):
            pass

        # Format musician (speaker)
        musician = None
        if booking.get('speaker'):
            musician_data = booking['speaker']
            musician = {
                'id': musician_data.get('id', 'N/A'),
                'name': f"{musician_data.get('first_name', '')} {musician_data.get('second_name', '')}".strip(),
                'email': musician_data.get('email', 'Не указан'),
                'phone': musician_data.get('phone', 'Не указан')
            }

        result.append({
            'id': booking.get('id', 'N/A'),
            'location_id': booking.get('location_id', 'N/A'),
            'location_address': booking.get('location_address', 'Не указано'),
            'date': date,
            'time': booking.get('time', 'Не указано'),
            'duration': booking.get('duration_hours', 'Не указана'),
            'available': booking.get('available', True),
            'musician': musician,
        })

    return result
