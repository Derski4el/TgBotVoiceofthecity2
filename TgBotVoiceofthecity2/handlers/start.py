from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from pathlib import Path

from utils.keyboards import get_main_keyboard
from utils.user import get_user_from_message

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    # Проверяем, авторизован ли пользователь
    user = get_user_from_message(message)

    # Путь к изображению
    image_path = Path(__file__).parent.parent / "docs" / "image.jpg"

    # Отправляем фото с подписью и клавиатурой
    await message.answer_photo(
        photo=FSInputFile(image_path),
        caption=(
            "👋 Привет, друг! Добро пожаловать в телеграм бот проекта «Голос города» | ЕКБ\n\n"
            "Тут ты сможешь зарегистрироваться и забронировать наши сцены, чтобы этим летом весь город услышал именно тебя\n\n"
            "Для удобства можешь использовать кнопки или команды в боте, чтобы найти нужное\n\n"
            "Чувствуй себя как дома ❤️"
        ),
        reply_markup=get_main_keyboard()
    )

def register_start_handlers(dp):
    dp.include_router(router)