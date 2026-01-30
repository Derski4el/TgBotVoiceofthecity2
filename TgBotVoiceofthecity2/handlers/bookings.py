import logging
from datetime import datetime, timedelta
import re
import os
from pathlib import Path

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states.booking import BookingForm
from utils.keyboards import (
    get_main_keyboard, get_login_register_keyboard, get_start_booking_keyboard,
    get_locations_keyboard, get_booking_confirmation_keyboard, get_user_booking_keyboard,
    get_schedule_keyboard
)
from utils.user import get_user_from_message
from DataBase import database

logger = logging.getLogger(__name__)

# Путь к директории с документами
DOCS_DIR = Path(__file__).parent.parent / "docs"


def register_booking_handlers(dp):
    """Register booking handlers"""
    router = Router()

    # View available bookings
    @router.message(Command("bookings"))
    async def cmd_bookings(message: Message):
        await show_bookings(message)

    # Bookings button handler
    @router.message(F.text == "📋 Точки")
    async def button_bookings(message: Message):
        await show_bookings(message)

    # View my bookings
    @router.message(Command("mybookings"))
    async def cmd_my_bookings(message: Message):
        await show_my_bookings(message)

    # My bookings button handler
    @router.message(F.text == "📅 Мои бронирования")
    async def button_my_bookings(message: Message):
        await show_my_bookings(message)

    # Start booking process
    @router.callback_query(F.data == "start_booking")
    async def process_start_booking(callback_query: CallbackQuery, state: FSMContext):
        user = get_user_from_callback(callback_query)

        if not user:
            await callback_query.answer("Для бронирования необходимо войти в систему.")
            return

        # Проверяем, подтвержден ли аккаунт администратором
        if not user.get('verified'):
            await callback_query.message.answer(
                "⚠️ Ваш аккаунт еще не подтвержден администратором.\n"
                "После подтверждения вы сможете бронировать точки.\n"
                "Обычно это занимает не более 24 часов."
            )
            return

        # Check if user is in cooldown
        is_in_cooldown, cooldown_date = database.check_user_cooldown(user['id'])
        if is_in_cooldown:
            await callback_query.answer(
                f"Вы не можете бронировать точки до {cooldown_date.strftime('%d.%m.%Y %H:%M')}",
                show_alert=True
            )
            return

        # Get all locations
        locations = database.get_all_locations()
        if not locations:
            await callback_query.message.answer("В настоящее время нет доступных точек.")
            return

        await state.set_state(BookingForm.location)
        await callback_query.message.answer(
            "Выберите место для выступления:",
            reply_markup=get_locations_keyboard(locations)
        )
        await callback_query.answer()

    # Location selection
    @router.callback_query(F.data.startswith("location_"))
    async def process_location_selection(callback_query: CallbackQuery, state: FSMContext):
        location_id = callback_query.data.split("_")[1]

        await state.update_data(location_id=location_id)
        await state.set_state(BookingForm.time_input)

        location = database.get_location_by_id(location_id)
        await callback_query.message.answer(
            f"Место: {location['address']}\n\n"
            "Введите дату и время в формате: ДД.ММ.ГГГГ ЧЧ:ММ\n"
            "Например: 25.06.2025 14:00\n\n"
            "Или отправьте /cancel для отмены."
        )
        await callback_query.answer()

    # Time input handler
    @router.message(BookingForm.time_input)
    async def process_time_input(message: Message, state: FSMContext):
        time_text = message.text.strip()

        # Validate time format
        time_pattern = r'^(\d{2})\.(\d{2})\.(\d{4})\s+(\d{1,2}):(\d{2})$'
        match = re.match(time_pattern, time_text)

        if not match:
            await message.answer(
                "❌ Неверный формат времени. Используйте формат: ДД.ММ.ГГГГ ЧЧ:ММ\n"
                "Например: 25.06.2025 14:00"
            )
            return

        day, month, year, hour, minute = match.groups()

        try:
            # Create datetime object
            booking_datetime = datetime(
                int(year), int(month), int(day),
                int(hour), int(minute)
            )

            # Check if the date is in the future
            if booking_datetime <= datetime.now():
                await message.answer(
                    "❌ Дата и время должны быть в будущем. Попробуйте снова."
                )
                return

            # Check if the date is not too far in the future (e.g., within 30 days)
            max_date = datetime.now() + timedelta(days=30)
            if booking_datetime > max_date:
                await message.answer(
                    "❌ Дата не может быть более чем через 30 дней. Попробуйте снова."
                )
                return

            # Check working hours (9:00 - 21:00)
            if booking_datetime.hour < 9 or booking_datetime.hour >= 21:
                await message.answer(
                    "❌ Бронирование доступно только с 09:00 до 21:00. Попробуйте снова."
                )
                return

            # Only allow exact hours (no minutes)
            if booking_datetime.minute != 0:
                await message.answer(
                    "❌ Бронирование возможно только на точное время (например, 14:00). Попробуйте снова."
                )
                return

            await state.update_data(
                booking_date=booking_datetime.date().isoformat(),
                booking_time=booking_datetime.time().strftime('%H:%M')
            )

            # Show schedule for selected date and location
            data = await state.get_data()
            location_id = data['location_id']
            date = booking_datetime.date().isoformat()

            schedule = database.get_location_schedule(location_id, date)
            schedule_text = database.format_schedule_visualization(schedule)

            await message.answer(schedule_text)

            await state.set_state(BookingForm.duration_input)
            await message.answer(
                f"Дата и время: {booking_datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
                "Введите продолжительность в часах (1 или 2):",
                reply_markup=get_schedule_keyboard()
            )

        except ValueError:
            await message.answer(
                "❌ Неверная дата или время. Проверьте правильность ввода."
            )

    # Duration selection via callback
    @router.callback_query(F.data.startswith("duration_"))
    async def process_duration_callback(callback_query: CallbackQuery, state: FSMContext):
        duration = int(callback_query.data.split("_")[1])

        await state.update_data(duration_hours=duration)
        await state.set_state(BookingForm.confirmation)

        # Get booking details for confirmation
        data = await state.get_data()
        location = database.get_location_by_id(data['location_id'])

        cooldown_days = database.get_cooldown_days()
        booking_date = datetime.fromisoformat(data['booking_date'])
        cooldown_end = booking_date + timedelta(days=cooldown_days)

        await callback_query.message.answer(
            f"Подтвердите бронирование:\n\n"
            f"📍 Место: {location['address']}\n"
            f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
            f"🕒 Время: {data['booking_time']}\n"
            f"⏱ Продолжительность: {duration} час{'а' if duration == 2 else ''}\n\n"
            f"⚠️ После этого бронирования вы не сможете бронировать другие точки до {cooldown_end.strftime('%d.%m.%Y')}",
            reply_markup=get_booking_confirmation_keyboard()
        )
        await callback_query.answer()

    # Duration input handler (text)
    @router.message(BookingForm.duration_input)
    async def process_duration_input(message: Message, state: FSMContext):
        duration_text = message.text.strip()

        try:
            duration = int(duration_text)
            if duration not in [1, 2]:
                await message.answer(
                    "❌ Продолжительность может быть только 1 или 2 часа. Попробуйте снова:"
                )
                return

            await state.update_data(duration_hours=duration)
            await state.set_state(BookingForm.confirmation)

            # Get booking details for confirmation
            data = await state.get_data()
            location = database.get_location_by_id(data['location_id'])

            cooldown_days = database.get_cooldown_days()
            booking_date = datetime.fromisoformat(data['booking_date'])
            cooldown_end = booking_date + timedelta(days=cooldown_days)

            await message.answer(
                f"Подтвердите бронирование:\n\n"
                f"📍 Место: {location['address']}\n"
                f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {data['booking_time']}\n"
                f"⏱ Продолжительность: {duration} час{'а' if duration == 2 else ''}\n\n"
                f"⚠️ После этого бронирования вы не сможете бронировать другие точки до {cooldown_end.strftime('%d.%m.%Y')}",
                reply_markup=get_booking_confirmation_keyboard()
            )

        except ValueError:
            await message.answer(
                "❌ Введите число (1 или 2):"
            )

    # Show schedule callback
    @router.callback_query(F.data == "show_schedule")
    async def show_schedule_callback(callback_query: CallbackQuery, state: FSMContext):
        data = await state.get_data()
        location_id = data.get('location_id')
        booking_date = data.get('booking_date')

        if location_id and booking_date:
            schedule = database.get_location_schedule(location_id, booking_date)
            schedule_text = database.format_schedule_visualization(schedule)
            await callback_query.message.answer(schedule_text)
        else:
            await callback_query.message.answer("❌ Сначала выберите дату и место.")

        await callback_query.answer()

    # Booking confirmation
    @router.callback_query(F.data == "confirm_booking")
    async def process_booking_confirmation(callback_query: CallbackQuery, state: FSMContext):
        user = get_user_from_callback(callback_query)
        if not user:
            await callback_query.answer("Для бронирования необходимо войти в систему.")
            return

        data = await state.get_data()
        
        # Создаем бронирование
        booking_id = database.create_booking(
            user_id=user['id'],
            location_id=data['location_id'],
            date=data['booking_date'],
            time=data['booking_time'],
            duration_hours=data['duration_hours']
        )

        if booking_id:
            location = database.get_location_by_id(data['location_id'])
            booking_date = datetime.fromisoformat(data['booking_date'])
            
            await callback_query.message.answer(
                f"✅ Бронирование успешно создано!\n\n"
                f"📍 Место: {location['address']}\n"
                f"📅 Дата: {booking_date.strftime('%d.%m.%Y')}\n"
                f"🕒 Время: {data['booking_time']}\n"
                f"⏱ Продолжительность: {data['duration_hours']} час{'а' if data['duration_hours'] == 2 else ''}\n\n"
                f"ℹ️ Информация для выступления:\n"
                f"• На сценах установлены информационные таблички\n"
                f"• Рекомендуем распечатать на листе А4:\n"
                f"  - QR-код на соц. сети\n"
                f"  - Реквизиты для переводов донатов"
            )
            await state.clear()
        else:
            await callback_query.message.answer(
                "❌ Произошла ошибка при создании бронирования. Пожалуйста, попробуйте позже."
            )
        await callback_query.answer()

    # Cancel booking process
    @router.callback_query(F.data == "cancel_booking")
    async def cancel_booking_process(callback_query: CallbackQuery, state: FSMContext):
        await state.clear()
        await callback_query.message.answer("❌ Бронирование отменено.")
        await callback_query.answer()

    # Cancel existing booking
    @router.callback_query(F.data.startswith("cancel_booking_"))
    async def cancel_existing_booking(callback_query: CallbackQuery):
        booking_id = callback_query.data.split("_")[2]
        user = get_user_from_callback(callback_query)

        if not user:
            await callback_query.answer("Для отмены бронирования необходимо войти в систему.")
            return

        success, message_text = database.cancel_booking(booking_id, user['id'])
        await callback_query.message.answer(f"✅ {message_text}" if success else f"❌ {message_text}")

        if success:
            await show_my_bookings(callback_query.message)

        await callback_query.answer()

    # Add the router to the dispatcher
    dp.include_router(router)


async def show_bookings(message):
    """Show available bookings with location details and booking tables"""
    user = get_user_from_message(message)

    if not user:
        await message.answer(
            "❌ Для просмотра и бронирования точек необходимо войти в систему.\n"
            "Используйте команду /login для входа или /register для регистрации.",
            reply_markup=get_login_register_keyboard()
        )
        return

    # Check if user is in cooldown
    is_in_cooldown, cooldown_date = database.check_user_cooldown(user['id'])

    if is_in_cooldown:
        await message.answer(
            f"⏳ Вы не можете бронировать точки до {cooldown_date.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Вы можете просмотреть доступные точки, но не можете их забронировать."
        )

    # Get all locations
    locations = database.get_all_locations()
    if not locations:
        await message.answer("В настоящее время нет доступных точек.")
        return

    # Get all bookings with user details
    all_bookings = database.get_all_bookings_with_users()

    # Group bookings by location
    bookings_by_location = {}
    for booking in all_bookings:
        location_id = booking.get('location_id')
        if location_id not in bookings_by_location:
            bookings_by_location[location_id] = []
        bookings_by_location[location_id].append(booking)

    # Display each location with its bookings
    for location in locations:
        location_id = location['id']
        location_bookings = bookings_by_location.get(location_id, [])

        # Format location header
        location_text = f"📍 <b>Адрес:</b> {location['address']}\n\n"

        if location_bookings:
            # Create table header
            location_text += "<b>Забронированные времена:</b>\n"
            location_text += "<pre>"
            location_text += f"{'Время':<12} | {'ФИО':<25}\n"
            location_text += "-" * 30 + "\n"

            # Sort bookings by date and time
            location_bookings.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))

            # Add booking rows
            for booking in location_bookings:
                # Format date and time
                try:
                    booking_date = datetime.fromisoformat(booking['date']).strftime('%d.%m')
                    time_str = f"{booking_date} {booking['time']}"
                except:
                    time_str = f"{booking.get('date', 'N/A')} {booking.get('time', 'N/A')}"

                # Get user info
                speaker = booking.get('speaker', {})
                full_name = f"{speaker.get('first_name', '')} {speaker.get('second_name', '')}".strip()
                if not full_name:
                    full_name = "Не указано"

                # Truncate long names and phones for table formatting
                if len(full_name) > 25:
                    full_name = full_name[:22] + "..."

                location_text += f"{time_str:<12} | {full_name:<25}\n"

            location_text += "</pre>"
        else:
            location_text += "📅 <i>Нет забронированных времен</i>"

        await message.answer(location_text, parse_mode="HTML")

    # Show booking button if user is not in cooldown
    if not is_in_cooldown:
        await message.answer(
            "Для бронирования точки нажмите кнопку ниже:",
            reply_markup=get_start_booking_keyboard()
        )


async def show_my_bookings(message):
    """Show user's bookings"""
    user = get_user_from_message(message)

    if not user:
        await message.answer(
            "❌ Для просмотра ваших бронирований необходимо войти в систему.\n"
            "Используйте команду /login для входа или /register для регистрации.",
            reply_markup=get_login_register_keyboard()
        )
        return

    # Debug the database tables
    database.debug_database_tables()

    # Get user bookings
    bookings = database.get_user_bookings(user['id'])

    # Log the bookings for debugging
    logger.info(f"User {user['id']} has {len(bookings)} bookings")
    for i, booking in enumerate(bookings):
        logger.info(f"Booking {i + 1}: {booking}")

    if not bookings:
        await message.answer("У вас пока нет забронированных точек.")
        return

    # Check if user is in cooldown
    is_in_cooldown, cooldown_date = database.check_user_cooldown(user['id'])
    cooldown_info = f"\n⏳ Вы не можете бронировать до: {cooldown_date.strftime('%d.%m.%Y')}" if is_in_cooldown else ""

    await message.answer(f"📅 Ваши забронированные точки:{cooldown_info}")

    for booking in bookings:
        # Parse the date for better formatting
        try:
            booking_date = datetime.fromisoformat(booking['date']).strftime('%d.%m.%Y')
        except:
            booking_date = booking['date']

        # Parse the created_at date for better formatting
        try:
            created_date = datetime.fromisoformat(booking['created_at']).strftime('%d.%m.%Y %H:%M')
        except:
            created_date = booking['created_at']

        await message.answer(
            f"🔹 📍 {booking['location_address']}\n"
            f"📅 Дата: {booking_date}\n"
            f"🕒 Время: {booking['time']}\n"
            f"⏱ Продолжительность: {booking['duration_hours']} час{'а' if booking['duration_hours'] == 2 else ''}\n"
            f"📝 Забронировано: {created_date}",
            reply_markup=get_user_booking_keyboard(booking['id'])
        )


def get_user_from_callback(callback_query):
    """Get user from database by Telegram ID from callback query"""
    if not callback_query.from_user:
        return None

    telegram_id = str(callback_query.from_user.id)
    return database.get_user_by_telegram_id(telegram_id)
