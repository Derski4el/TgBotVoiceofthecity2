from aiogram.fsm.state import State, StatesGroup

class RegistrationForm(StatesGroup):
    first_name = State()
    patronymic = State()
    second_name = State()
    passport = State()
    email = State()
    phone = State()
    password = State()
    confirm_password = State()
    agreements = State()
