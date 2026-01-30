from aiogram.fsm.state import State, StatesGroup

# Define states for login
class LoginForm(StatesGroup):
    identifier = State()  # Email or phone
    password = State()
