from aiogram import Router, F
from aiogram.types import Message

def register_common_handlers(dp):
    """Register common handlers"""
    router = Router()
    
    # Handle all other messages
    @router.message()
    async def echo(message: Message):
        # Check if it's a menu button we haven't handled yet
        if message.text in ["📋 Точки", "👤 Профиль", "📅 Мои бронирования", "ℹ️ Помощь"]:
            # These should be handled by their respective handlers
            return
        
        await message.answer(
            "Я не понимаю эту команду. Используйте /help для просмотра доступных команд."
        )
    
    # Add the router to the dispatcher
    dp.include_router(router)
