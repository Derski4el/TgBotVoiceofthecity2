from aiogram.fsm.state import State, StatesGroup

# Define states for booking
class BookingForm(StatesGroup):
    booking_id = State()
    role = State()
    confirmation = State()
