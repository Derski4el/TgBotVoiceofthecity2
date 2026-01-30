from aiogram.fsm.state import State, StatesGroup

class BookingForm(StatesGroup):
    location = State()
    time_input = State()
    duration_input = State()
    confirmation = State()
    waiting_for_consent = State()
