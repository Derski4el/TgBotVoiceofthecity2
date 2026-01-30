from aiogram.fsm.state import State, StatesGroup

class RegisterForm(StatesGroup):
    first_name = State()
    patronymic = State()
    second_name = State()
    phone = State()
    email = State()
    password = State()
    agreements = State()
    artist_form = State()
    consent = State()

class LoginForm(StatesGroup):
    email = State()
    password = State()
