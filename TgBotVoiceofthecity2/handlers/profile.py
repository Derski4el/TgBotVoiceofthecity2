from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from utils.keyboards import get_login_register_keyboard
from utils.user import get_user_from_message
from utils.formatters import format_date, format_profile_text
from DataBase import database

def register_profile_handlers(dp):
    """Register profile handlers"""
    router = Router()
    
    # Profile command handler
    @router.message(Command("profile"))
    async def cmd_profile(message: Message):
        await show_profile(message)
    
    # Profile button handler
    @router.message(F.text == "👤 Профиль")
    async def button_profile(message: Message):
        await show_profile(message)
    
    # Callback for email verification
    @router.callback_query(F.data == "verify_email")
    async def process_verify_email(callback_query: CallbackQuery):
        user = get_user_from_callback(callback_query)
        
        if not user:
            await callback_query.answer("Вы не вошли в систему")
            return
        
        if user.get('confirm_email'):
            await callback_query.answer("Ваш email уже подтвержден")
            return
        
        # Here you would typically implement email verification logic
        # For this example, we'll just mark the email as verified
        database.update_user_email_verification(user['id'], True)
        
        await callback_query.message.answer("✅ Ваш email успешно подтвержден!")
        await callback_query.answer()
        
        # Refresh profile view
        await show_profile(callback_query.message)
    
    # Callback for phone verification
    @router.callback_query(F.data == "verify_phone")
    async def process_verify_phone(callback_query: CallbackQuery):
        user = get_user_from_callback(callback_query)
        
        if not user:
            await callback_query.answer("Вы не вошли в систему")
            return
        
        if user.get('confirm_phone'):
            await callback_query.answer("Ваш телефон уже подтвержден")
            return
        
        # Here you would typically implement phone verification logic
        # For this example, we'll just mark the phone as verified
        database.update_user_phone_verification(user['id'], True)
        
        await callback_query.message.answer("✅ Ваш телефон успешно подтвержден!")
        await callback_query.answer()
        
        # Refresh profile view
        await show_profile(callback_query.message)
    
    # Callback for editing profile
    @router.callback_query(F.data == "edit_profile")
    async def process_edit_profile(callback_query: CallbackQuery):
        await callback_query.message.answer(
            "🔄 Функция изменения данных профиля находится в разработке.\n"
            "Скоро она будет доступна!"
        )
        await callback_query.answer()
    
    # Add the router to the dispatcher
    dp.include_router(router)

async def show_profile(message):
    """Show user profile"""
    user = get_user_from_message(message)
    
    if not user:
        # User is not registered
        await message.answer(
            "❌ Вы еще не вошли в систему.\n"
            "Для использования всех функций бота необходимо войти или зарегистрироваться.",
            reply_markup=get_login_register_keyboard()
        )
        return
    
    # Check if user is in cooldown
    is_in_cooldown, cooldown_date = database.check_user_cooldown(user['id'])
    
    # Create profile information message
    profile_text = format_profile_text(user, is_in_cooldown, cooldown_date)
    
    await message.answer(
        profile_text,
        parse_mode="HTML"
    )

def get_user_from_callback(callback_query):
    """Get user from database by Telegram ID from callback query"""
    if not callback_query.from_user:
        return None
    
    telegram_id = str(callback_query.from_user.id)
    return database.get_user_by_telegram_id(telegram_id)
