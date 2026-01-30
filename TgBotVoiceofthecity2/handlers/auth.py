import re
import uuid
import hashlib
import logging
from datetime import datetime
from pathlib import Path
import os

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, FSInputFile, ReplyKeyboardRemove
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states.auth import RegisterForm, LoginForm
from utils.keyboards import get_main_keyboard, get_agreements_keyboard, get_phone_request_keyboard, \
    get_login_register_keyboard
from utils.validators import (
    validate_name, validate_patronymic,
    validate_email, validate_phone, validate_password
)
from utils.user import get_user_from_message
from DataBase import database

logger = logging.getLogger(__name__)

# Путь к директории с документами пользователей
USER_DOCS_DIR = Path(__file__).parent.parent / "user_docs"
os.makedirs(USER_DOCS_DIR, exist_ok=True)


def register_auth_handlers(dp):
    """Register all authentication handlers"""
    router = Router()

    # Login command handler
    @router.message(Command("login"))
    async def cmd_login(message: Message, state: FSMContext):
        # Check if user is already logged in
        user = get_user_from_message(message)
        if user:
            await message.answer(
                "Вы уже вошли в систему.\n"
                "Используйте команду /profile для просмотра вашего профиля"
            )
            return

        # Always require manual login - removed automatic login with saved Telegram ID
        await state.set_state(LoginForm.email)
        await message.answer(
            "Вход в систему. Вы можете отменить процесс в любой момент, отправив команду /cancel.\n\n"
            "Введите ваш email или номер телефона:"
        )

    # Logout command handler
    @router.message(Command("logout"))
    async def cmd_logout(message: Message):
        # Check if user is logged in
        user = get_user_from_message(message)
        if not user:
            await message.answer(
                "Вы не вошли в систему.\n"
                "Используйте команду /login для входа."
            )
            return

        # Save Telegram ID instead of removing it
        success = database.remove_user_telegram_id(user['id'])

        if success:
            await message.answer(
                "✅ Вы успешно вышли из системы.\n"
                "Используйте команду /login для повторного входа."
            )
        else:
            await message.answer(
                "❌ Произошла ошибка при выходе из системы.\n"
                "Пожалуйста, попробуйте позже."
            )

    # Register command handler
    @router.message(Command("register"))
    async def cmd_register(message: Message, state: FSMContext):
        # Check if user is already registered
        user = get_user_from_message(message)
        if user:
            await message.answer(
                "Команда /login, что бы войти в систему")
            return

        await state.set_state(RegisterForm.first_name)
        await message.answer(
            "Давай знакомиться Про нас ты наверняка уже знаешь, осталось нам узнать про тебя😉\n\n"
            "_Напиши нам свое_ *ИМЯ*, _используй только русские буквы_ \n\n"
            "||Кстати, если нужно отойти попить чай и прервать регистрацию, можешь просто написать /cancel||",
            parse_mode='MarkdownV2'
        )

    # Cancel command handler
    @router.message(Command("cancel"))
    async def cmd_cancel(message: Message, state: FSMContext):
        current_state = await state.get_state()
        if current_state is None:
            return

        await state.clear()
        await message.answer(
            "❌*Ты прервал процесс регистрации*\n\n"
                "Ничего страшного, ты всегда можешь вернуться к нам\n"
                "Будем ждать❤️🫶\n",
            reply_markup=get_main_keyboard(),parse_mode='MarkdownV2'
        )

    # Login flow handlers
    @router.message(LoginForm.email)
    async def process_login_identifier(message: Message, state: FSMContext):
        identifier = message.text.strip()

        # Check if it's an email or phone
        is_email = re.fullmatch(r"[^@]+@[^@]+\.[^@]+", identifier)
        is_phone = re.fullmatch(r'^(?:\+7|8)(?:\d{10}|[348]\d{9}|[3489]\d{8}|[3489]\d{7})$|^(?:\+7|7)[349]\d{9}$', identifier)

        if not (is_email or is_phone):
            await message.answer("❌ Некорректный формат email или номера телефона. Попробуйте снова:")
            return

        # Store the identifier and its type
        await state.update_data(identifier=identifier, is_email=bool(is_email))

        # Move to password state
        await state.set_state(LoginForm.password)
        await message.answer("Введите ваш пароль:")

    @router.message(LoginForm.password)
    async def process_login_password(message: Message, state: FSMContext):
        password = message.text

        # Hash the password for comparison
        hash_password = hashlib.sha256(password.encode()).hexdigest()

        # Get the stored data
        data = await state.get_data()
        identifier = data['identifier']
        is_email = data['is_email']

        # Try to find the user
        user = None
        if is_email:
            user = database.get_user_by_email(identifier)
        else:
            user = database.get_user_by_phone(identifier)

        if not user or user['hash_password'] != hash_password:
            await message.answer(
                "❌ Неверный email/телефон или пароль. Попробуйте снова или используйте /cancel для отмены.")
            await state.set_state(LoginForm.email)
            return

        # Update the user's Telegram ID to link the account
        try:
            database.update_user_telegram_id(user['id'], str(message.from_user.id))
        except Exception as e:
            logger.error(f"Error updating Telegram ID: {e}")
            await message.answer("❌ Произошла ошибка при входе в систему. Пожалуйста, попробуйте позже.")
            await state.clear()
            return

        # Login successful
        await message.answer(
            f"✅ Вход выполнен успешно! Добро пожаловать, {user['first_name']}.",
            reply_markup=get_main_keyboard()
        )

        # Clear the state
        await state.clear()

    # Registration flow handlers
    @router.message(RegisterForm.first_name)
    async def process_first_name(message: Message, state: FSMContext):
        if not validate_name(message.text):
            await message.answer("❌ Имя должно содержать только русские буквы и минимум 2 символа. Попробуйте снова:")
            return

        await state.update_data(first_name=message.text.strip())
        await state.set_state(RegisterForm.patronymic)
        await message.answer(
            r"Супер, теперь напиши свое *ОТЧЕСТВО*\. Если его нет просто отправь '\-'" + "\n\n" +
            r"||Прервать регистрацию можно написав /cancel||",
            parse_mode='MarkdownV2'
        )
    @router.message(RegisterForm.patronymic)
    async def process_patronymic(message: Message, state: FSMContext):
        patronymic = message.text.strip()
        if patronymic != '-' and not validate_patronymic(patronymic):
            await message.answer("❌ Отчество должно содержать только русские буквы и минимум 2 символа, или '-' если отчества нет. Попробуйте снова:")
            return

        await state.update_data(patronymic=patronymic if patronymic != '-' else '')
        await state.set_state(RegisterForm.second_name)
        await message.answer(
            r"Супер, с именем и отчеством разобрались\! Идем дальше по нашему знакомству\." "\n\n"
            r"Теперь, пожалуйста, напиши свою *ФАМИЛИЮ*\. Используй только русские буквы, как и раньше\." "\n\n"
            r"_Если вдруг понадобится отлучиться на чашечку какао, команда /cancel всегда рядом, чтобы сделать паузу\._ ☕️",
            parse_mode='MarkdownV2'
        )
    @router.message(RegisterForm.second_name)
    async def process_second_name(message: Message, state: FSMContext):
        if not validate_name(message.text):
            await message.answer(
                "❌ Фамилия должна содержать только русские буквы и минимум 2 символа. Попробуйте снова:")
            return

        await state.update_data(second_name=message.text.strip())
        await state.set_state(RegisterForm.email)
        await message.answer(
            r"Класс\! Мы почти у цели с основными данными\." "\n\n"
            r"Теперь нам нужен твой *E\-MAIL*, чтобы мы могли отправлять тебе важные уведомления о бронированиях и держать в курсе самых интересных событий проекта «Голос города»\." "\n\n"
            r"📧 Пожалуйста, напиши его в формате\:" "\n\n"
            r"```example@mail\.ru```" "\n\n"
            r"_И помни, команда `/cancel` твой верный помощник, если нужно прерваться\! 😊_",
            parse_mode='MarkdownV2'
        )
    @router.message(RegisterForm.email)
    async def process_email(message: Message, state: FSMContext):
        email = message.text.strip()

        if not validate_email(email):
            await message.answer("❌ Некорректный формат email. Попробуйте снова:")
            return

        # Debug: Log the email being checked
        logger.info(f"Checking email: {email}")

        # Check if email already exists
        existing_user = database.get_user_by_email(email)
        if existing_user:
            logger.info(f"Email {email} already exists for user: {existing_user}")
            await message.answer("❌ Пользователь с таким email уже зарегистрирован. Введите другой email:")
            return

        logger.info(f"Email {email} is available")
        await state.update_data(email=email)
        await state.set_state(RegisterForm.phone)
        await message.answer(
            r"Отлично, мы почти закончили\! Остался только твой *НОМЕР ТЕЛЕФОНА*\." "\n\n"
            r"Он нужен для оперативной связи и чтобы мы были уверены, что ты – это именно ты \(мало ли, вдруг кто\-то захочет занять твое звездное место\! 😉\)\." "\n\n"
            r"Ты можешь\:" "\n\n"
            r"Нажать на кнопку «Поделиться номером» ниже 👇" "\n"
            r"\(Telegram всё сделает за тебя, это самый быстрый способ\!\)" "\n\n"
            r"Или написать его вручную в формате" "\n"
            r"```\+79123456789```" "\n\n"
            r"||Интересно, нужно ли каждый раз повторять про /cancel 🤔||",
            reply_markup=get_phone_request_keyboard(),
            parse_mode='MarkdownV2'
        )

    # Handle phone contact sharing
    @router.message(RegisterForm.phone, F.contact)
    async def process_phone_contact(message: Message, state: FSMContext):
        if not message.contact:
            await message.answer("❌ Не удалось получить номер телефона. Попробуйте снова.")
            return

        # Get phone number from contact
        phone_number = message.contact.phone_number

        # Normalize phone number (add + if missing)
        if not phone_number.startswith('+'):
            phone_number = '+' + phone_number

        # Debug: Log the phone being checked
        logger.info(f"Checking phone: {phone_number}")

        # Check if phone already exists
        existing_user = database.get_user_by_phone(phone_number)
        if existing_user:
            logger.info(f"Phone {phone_number} already exists for user: {existing_user}")
            await message.answer(
                "❌ Пользователь с таким номером телефона уже зарегистрирован.\n"
                "Попробуйте войти в систему командой /login",
                reply_markup=get_main_keyboard()
            )
            await state.clear()
            return

        logger.info(f"Phone {phone_number} is available")

        # Automatically verify phone since it came from Telegram
        await state.update_data(phone=phone_number, phone_verified=True)
        await state.set_state(RegisterForm.password)

        await message.answer(
            r"Молодец\! Все твои контактные данные у нас\. Теперь давай придумаем *ПАРОЛЬ*\." "\n\n"
            r"Придумай и напиши его сюда\. Постарайся сделать его надежным, но таким, чтобы ты его точно не забыл\! 🔐" "\n\n"
            r"_Ну и по традиции, /cancel, если нужно отвлечься\. Мы подождем\! ❤️_",
            reply_markup=get_main_keyboard(),
            parse_mode='MarkdownV2'
        )

    # Handle manual phone input (fallback)
    @router.message(RegisterForm.phone)
    async def process_phone_manual(message: Message, state: FSMContext):
        # Check if user clicked "Ввести вручную"
        if message.text == "✏️ Ввести номер вручную":
            await message.answer(
                "Введите ваш номер телефона (от 10 до 15 цифр, можно с '+' в начале):",
                reply_markup=get_main_keyboard()
            )
            return

        phone = message.text.strip()

        if not validate_phone(phone):
            await message.answer(
                "❌ Номер телефона должен содержать от 10 до 15 цифр, можно с '+' в начале. Попробуйте снова:")
            return

        # Debug: Log the phone being checked
        logger.info(f"Checking manual phone: {phone}")

        # Check if phone already exists
        existing_user = database.get_user_by_phone(phone)
        if existing_user:
            logger.info(f"Phone {phone} already exists for user: {existing_user}")
            await message.answer("❌ Пользователь с таким номером телефона уже зарегистрирован. Введите другой номер:")
            return

        logger.info(f"Manual phone {phone} is available")

        # Manual phone input - not verified
        await state.update_data(phone=phone, phone_verified=False)
        await state.set_state(RegisterForm.password)
        await message.answer(
            r"Молодец\! Все твои контактные данные у нас\. Теперь давай придумаем *ПАРОЛЬ*\." "\n\n"
            r"Придумай и напиши его сюда\. Постарайся сделать его надежным, но таким, чтобы ты его точно не забыл\! 🔐" "\n\n"
            r"_Ну и по традиции, /cancel, если нужно отвлечься\. Мы подождем\! ❤️_",
            reply_markup=get_main_keyboard(),
            parse_mode='MarkdownV2'
        )

    @router.message(RegisterForm.password)
    async def process_password(message: Message, state: FSMContext):
        if not validate_password(message.text):
            await message.answer("❌ Пароль должен содержать минимум 8 символов. Попробуйте снова:")
            return

        # Hash the password
        hash_password = hashlib.sha256(message.text.encode()).hexdigest()
        await state.update_data(hash_password=hash_password)

        await state.set_state(RegisterForm.agreements)

        # Create keyboard for agreements
        await message.answer(
            r"Ура\! Мы на финишной прямой\! 🏁 Остался последний, но очень важный шаг – ознакомиться и принять наше *Пользовательское Соглашение*\." "\n\n"
            r"В нем мы честно и понятно рассказали о том, как все устроено в «Голосе города», о твоих возможностях и наших обязательствах\." "\n\n"
            r"Если ты со всем согласен и готов стать частью нашего музыкального сообщества, нажми кнопку" "\n" "«✅ Принимаю»",
            reply_markup=get_agreements_keyboard(),
            parse_mode='MarkdownV2'
        )

    @router.message(RegisterForm.agreements)
    async def process_agreements(message: Message, state: FSMContext):
        if message.text == "✅ Принимаю":
            await state.set_state(RegisterForm.artist_form)
            await message.answer(
                "Поздравляем с успешной регистрацией в проекте «Голос города»! 🎉 Мы это сделали!\n\n"
                "Теперь, чтобы мы могли лучше представить тебя публике, предлагаем заполнить <b>АНКЕТУ АРТИСТА</b>\n\n"
                "Это твой шанс рассказать городу о себе! Готов? Нажми кнопку «📝 Заполнить анкету»\n"
                "<a href='https://forms.gle/ix5H48rbkWrF8NyN9'>Ссылка на анкету</a>",
                parse_mode='HTML',
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="✅ Анкета заполнена")]],
                    resize_keyboard=True
                )
            )
        else:
            await message.answer(
                "Для регистрации необходимо принять условия использования.",
                reply_markup=get_agreements_keyboard()
            )

    @router.message(RegisterForm.artist_form)
    async def process_artist_form(message: Message, state: FSMContext):
        if message.text == "✅ Анкета заполнена":
            # Формируем путь относительно текущего файла
            current_dir = Path(__file__).parent
            consent_doc = current_dir.parent / "docs" / "Договор_для_артистов_Голос_Города_2025.docx"

            if not consent_doc.exists():
                # Логируем ошибку
                logger.error(f"Файл согласия не найден: {consent_doc}")

                # Предлагаем альтернативное решение
                await message.answer(
                    "❌ Извините, возникла техническая проблема. Документ временно недоступен.\n\n"
                    "Пожалуйста, напишите администратору для получения документа.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return

            try:
                # Отправляем документ с HTML-разметкой
                await message.answer_document(
                    FSInputFile(consent_doc),
                    caption=(
                        "Супер, мы рады, что ты с нами и готов творить историю «Голоса города»! 🌟\n\n"
                        "Чтобы все было официально и по-настоящему, пожалуйста, отправь нам подписанный <b>Документ с согласием</b>. "
                        "Важно, чтобы он был именно в формате .docx.\n\n"
                        "Просто прикрепи файл к сообщению и отправь его нам.\n\n"
                        "Ждем твой файлик! 📄"
                    ),
                    parse_mode='HTML'
                )
                # Устанавливаем состояние ТОЛЬКО после успешной отправки документа
                await state.set_state(RegisterForm.consent)
            except Exception as e:
                logger.error(f"Ошибка отправки документа: {str(e)}")
                await message.answer(
                    "❌ Произошла ошибка при отправке документа. Пожалуйста, попробуйте позже.",
                    reply_markup=ReplyKeyboardRemove()
                )
        else:
            # Обрабатываем другие сообщения с HTML-разметкой
            await message.answer(
                "Ой, кажется, файлик пришел не совсем в том формате, который нам нужен. 🧐\n\n"
                "Для согласия нам необходим документ именно в формате <b>.docx</b>. Пожалуйста, проверь расширение файла и попробуй отправить его еще раз.\n\n"
                "Не волнуйся, такое бывает! Если что, мы тут, готовы помочь! 😉",
                reply_markup=ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text="✅ Анкета заполнена")]],
                    resize_keyboard=True
                ),
                parse_mode='HTML'
            )

    @router.message(RegisterForm.consent)
    async def process_consent(message: Message, state: FSMContext):
        if not message.document:
            await message.answer("Ой, кажется, файлик пришел не совсем в том формате, который нам нужен. 🧐\n\n"
                    "Для согласия нам необходим документ именно в формате .docx. Пожалуйста, проверь расширение файла и попробуй отправить его еще раз.\n\n"
                    "Не волнуйся, такое бывает! Если что, мы тут, готовы помочь! 😉")
            return

        if not message.document.file_name.endswith('.docx'):
            await message.answer("Ой, кажется, файлик пришел не совсем в том формате, который нам нужен. 🧐\n\n"
                    "Для согласия нам необходим документ именно в формате .docx. Пожалуйста, проверь расширение файла и попробуй отправить его еще раз.\n\n"
                    "Не волнуйся, такое бывает! Если что, мы тут, готовы помочь! 😉")
            return

        # Создаем директорию для пользователя
        user_dir = USER_DOCS_DIR / str(message.from_user.id)
        os.makedirs(user_dir, exist_ok=True)

        # Сохраняем документ
        file_path = user_dir / f"consent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
        
        # Скачиваем файл
        file_info = await message.bot.get_file(message.document.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)
        
        # Сохраняем файл
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file.read())

        # Получаем данные из состояния
        data = await state.get_data()
        
        # Создаем пользователя
        user_data = {
            'first_name': data.get('first_name', ''),
            'second_name': data.get('second_name', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'hash_password': data.get('hash_password', ''),
            'telegram_id': str(message.from_user.id),
            'saved_telegram_id': str(message.from_user.id),
            'agreements_status': True,
            'artist_form_filled': True
        }

        user_id = database.add_user(user_data)

        if user_id:
            await message.answer(
                "✅ Регистрация успешно завершена!\n\n"
                "Теперь вы можете использовать все функции бота.",
                reply_markup=get_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Произошла ошибка при регистрации. Пожалуйста, попробуйте позже или обратитесь к администратору.",
                reply_markup=get_login_register_keyboard()
            )

        await state.clear()

    @router.message(Command("confirm_form"))
    async def confirm_artist_form(message: Message):
        user = get_user_from_message(message)
        if not user:
            await message.answer("Для подтверждения необходимо войти в систему.")
            return

        # Обновляем статус заполнения анкеты
        if database.update_user_artist_form_status(user['id'], True):
            await message.answer(
                "✅ Спасибо за заполнение анкеты! Теперь вы можете бронировать точки."
            )
        else:
            await message.answer(
                "❌ Произошла ошибка при обновлении статуса анкеты. Пожалуйста, попробуйте позже."
            )

    # Callback for logout from profile
    @router.callback_query(F.data == "logout")
    async def process_logout_callback(callback_query: CallbackQuery):
        user = get_user_from_callback(callback_query)

        if not user:
            await callback_query.answer("Вы не вошли в систему")
            return

        # Remove Telegram ID without saving it
        success = database.remove_user_telegram_id(user['id'])

        if success:
            await callback_query.message.answer(
                "✅ Вы успешно вышли из системы.\n"
                "Используйте команду /login для повторного входа."
            )
        else:
            await callback_query.message.answer(
                "❌ Произошла ошибка при выходе из системы.\n"
                "Пожалуйста, попробуйте позже."
            )

        await callback_query.answer()

    # Callback for starting login from profile
    @router.callback_query(F.data == "start_login")
    async def process_start_login(callback_query: CallbackQuery):
        await callback_query.message.answer("Для входа в систему используйте команду /login")
        await callback_query.answer()

    # Callback for starting registration from profile
    @router.callback_query(F.data == "start_registration")
    async def process_start_registration(callback_query: CallbackQuery):
        await callback_query.message.answer("Для регистрации используйте команду /register")
        await callback_query.answer()

    # Add the router to the dispatcher
    dp.include_router(router)


def get_user_from_callback(callback_query):
    """Get user from database by Telegram ID from callback query"""
    if not callback_query.from_user:
        return None

    telegram_id = str(callback_query.from_user.id)
    return database.get_user_by_telegram_id(telegram_id)
