import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from utils.admin import is_admin, format_users_table
from utils.keyboards import get_admin_cooldown_keyboard
from DataBase import database

logger = logging.getLogger(__name__)


def register_admin_handlers(dp):
    """Register admin handlers"""
    router = Router()

    # Admin command to view all users
    @router.message(Command("users"))
    async def cmd_users(message: Message):
        # Check if user is an admin
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой команде.")
            return

        try:
            # Get all users from database
            users = database.get_all_users()

            # Format users as HTML table
            users_table = format_users_table(users)

            # Send the table
            await message.answer(users_table, parse_mode="HTML")

            # Inform about the web interface
            await message.answer(
                "📊 Вы также можете просмотреть таблицу пользователей в веб-интерфейсе:\n"
                "http://localhost:8000/users"
            )
        except Exception as e:
            logger.error(f"Error in admin users command: {e}")
            await message.answer("❌ Произошла ошибка при получении списка пользователей.")

    # Admin command to promote a user to admin
    @router.message(Command("add_admin"))
    async def cmd_add_admin(message: Message):
        # Check if user is an admin
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой команде.")
            return

        # Parse command arguments
        args = message.text.split()
        if len(args) != 2:
            await message.answer("❌ Неверный формат команды. Используйте: /add_admin <user_id>")
            return

        user_id = args[1]

        try:
            # Check if user exists
            user = database.get_user_by_id(user_id)
            if not user:
                await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
                return

            # Set user role to admin
            success, msg = database.set_user_role(user_id, "admin")

            if success:
                await message.answer(f"✅ Пользователь {user['first_name']} {user['second_name']} теперь администратор.")
            else:
                await message.answer(f"❌ Ошибка: {msg}")
        except Exception as e:
            logger.error(f"Error in add_admin command: {e}")
            await message.answer("❌ Произошла ошибка при назначении администратора.")

    # Admin command to view all bookings with registered users
    @router.message(Command("bookings_list"))
    async def cmd_bookings_list(message: Message):
        # Check if user is an admin
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой команде.")
            return

        try:
            # Get all bookings
            bookings = database.get_all_bookings_with_users()

            if not bookings:
                await message.answer("В настоящее время нет забронированных точек.")
                return

            # Send a message for each booking
            for booking in bookings:
                speaker = booking['speaker']  # Fixed: was 'musician', now 'speaker'
                await message.answer(
                    f"🔹 <b>ID:</b> {booking['id']}\n"
                    f"📍 Место: {booking['location_address']}\n"
                    f"📅 Дата: {booking['date']}\n"
                    f"🕒 Время: {booking['time']}\n"
                    f"⏱ Продолжительность: {booking['duration_hours']} час{'а' if booking['duration_hours'] == 2 else ''}\n"
                    f"🎤 <b>Музыкант:</b> {speaker['first_name']} {speaker['second_name']}\n"
                    f"📧 Email: {speaker['email']}\n"
                    f"📱 Телефон: {speaker['phone']}\n"
                    f"🆔 ID: {speaker['id']}",
                    parse_mode="HTML"
                )

            # Inform about the web interface
            await message.answer(
                "📊 Вы также можете просмотреть подробную информацию о точках в веб-интерфейсе:\n"
                "http://localhost:8000/bookings"
            )
        except Exception as e:
            logger.error(f"Error in bookings_list command: {e}")
            await message.answer("❌ Произошла ошибка при получении списка точек.")

    # Admin command to change cooldown duration
    @router.message(Command("set_cooldown"))
    async def cmd_set_cooldown(message: Message):
        # Check if user is an admin
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой команде.")
            return

        current_cooldown = database.get_cooldown_days()
        await message.answer(
            f"Текущий период ожидания: {current_cooldown} дней\n\n"
            "Выберите новый период ожидания:",
            reply_markup=get_admin_cooldown_keyboard()
        )

    # Cooldown setting callbacks
    @router.callback_query(F.data.startswith("cooldown_"))
    async def process_cooldown_setting(callback_query: CallbackQuery):
        # Check if user is an admin
        if not is_admin(callback_query.from_user.id):
            await callback_query.answer("❌ У вас нет доступа к этой функции.")
            return

        days = int(callback_query.data.split("_")[1])

        success = database.set_cooldown_days(days)
        if success:
            await callback_query.message.answer(
                f"✅ Период ожидания изменен на {days} дней"
            )
        else:
            await callback_query.message.answer(
                "❌ Ошибка при изменении периода ожидания"
            )

        await callback_query.answer()

    @router.callback_query(F.data == "cancel_cooldown")
    async def cancel_cooldown_setting(callback_query: CallbackQuery):
        await callback_query.message.answer("❌ Изменение периода ожидания отменено.")
        await callback_query.answer()

    # Admin help command
    @router.message(Command(commands=["admin_help"]))
    async def cmd_admin_help(message: Message):
        # Check if user is an admin
        if not is_admin(message.from_user.id):
            await message.answer("❌ У вас нет доступа к этой команде.")
            return

        current_cooldown = database.get_cooldown_days()
        await message.answer(
            "📋 <b>Команды администратора:</b>\n\n"
            "/users - Просмотреть список всех пользователей\n"
            "/add_admin ID - Назначить пользователя администратором\n"
            "/bookings_list - Просмотреть все точки и зарегистрированных участников\n"
            "/set_cooldown - Изменить период ожидания (сейчас: " + str(current_cooldown) + " дней)\n"
            "/admin_help - Показать эту справку\n\n"
            "📊 <b>Веб-интерфейс администратора:</b>\n"
            "http://localhost:8000/users - Таблица пользователей\n"
            "http://localhost:8000/bookings - Таблица точек",
            parse_mode="HTML"
        )

    # Add the router to the dispatcher
    dp.include_router(router)
