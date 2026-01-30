from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime


def get_main_keyboard():
    """Return the main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Точки"), KeyboardButton(text="👤 Профиль")],
            [KeyboardButton(text="📅 Мои бронирования"), KeyboardButton(text="ℹ️ Помощь")]
        ],
        resize_keyboard=True
    )


def get_agreements_keyboard():
    """Return keyboard for agreements"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Принимаю")],
            [KeyboardButton(text="❌ Не принимаю")]
        ],
        resize_keyboard=True
    )


def get_phone_request_keyboard():
    """Return keyboard for phone number request"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
            [KeyboardButton(text="✏️ Ввести номер вручную")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )


def get_login_register_keyboard():
    """Return keyboard for login/register"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔑 Войти", callback_data="start_login"),
                InlineKeyboardButton(text="📝 Зарегистрироваться", callback_data="start_registration")
            ]
        ]
    )


def get_locations_keyboard(locations):
    """Return keyboard for location selection"""
    keyboard = []
    for location in locations:
        keyboard.append([InlineKeyboardButton(
            text=location['address'][:50] + "..." if len(location['address']) > 50 else location['address'],
            callback_data=f"location_{location['id']}"
        )])

    keyboard.append([InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_schedule_keyboard():
    """Return keyboard for duration selection and schedule viewing"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 час", callback_data="duration_1"),
                InlineKeyboardButton(text="2 часа", callback_data="duration_2")
            ],
            [InlineKeyboardButton(text="📅 Показать расписание", callback_data="show_schedule")],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")]
        ]
    )


def get_booking_confirmation_keyboard():
    """Return keyboard for booking confirmation"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
                InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_booking")
            ]
        ]
    )


def get_user_booking_keyboard(booking_id):
    """Return keyboard for user booking actions"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить бронирование", callback_data=f"cancel_booking_{booking_id}")]
        ]
    )


def get_start_booking_keyboard():
    """Return keyboard to start booking process"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎤 Забронировать точку", callback_data="start_booking")]
        ]
    )


def get_admin_cooldown_keyboard():
    """Return keyboard for admin cooldown management"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1 день", callback_data="cooldown_1"),
                InlineKeyboardButton(text="2 дня", callback_data="cooldown_2")
            ],
            [
                InlineKeyboardButton(text="3 дня", callback_data="cooldown_3"),
                InlineKeyboardButton(text="7 дней", callback_data="cooldown_7")
            ],
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_cooldown")]
        ]
    )
