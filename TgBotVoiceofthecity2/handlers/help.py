from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from utils.user import get_user_from_message
from utils.admin import is_admin
from DataBase import database

def register_help_handlers(dp):
    """Register help handlers"""
    router = Router()
    
    # Help command handler
    @router.message(Command("help"))
    async def cmd_help(message: Message):
        await show_help(message)
    
    # Help button handler
    @router.message(F.text == "ℹ️ Помощь")
    async def button_help(message: Message):
        await show_help(message)
    
    # Add the router to the dispatcher
    dp.include_router(router)

async def show_help(message):
    """Show help information"""
    # Check if user is logged in
    user = get_user_from_message(message)
    login_register_commands = "/login - Войти в систему\n/register - Зарегистрироваться в системе\n"
    
    # Admin commands are not shown in regular help - only in /admin_help
    
    await message.answer(
        "📋 <b>Доступные команды:</b>\n\n"
        "/start - Начать работу с ботом\n"
        f"{login_register_commands}"
        "/bookings - Просмотреть доступные точки\n"
        "/mybookings - Просмотреть ваши бронирования\n"
        "/profile - Просмотреть ваш профиль\n"
        "/help - Показать справку\n\n"
        "Вы также можете использовать кнопки меню для навигации.",
        parse_mode="HTML"
    )
