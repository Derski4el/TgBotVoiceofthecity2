from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from handlers.auth import register_auth_handlers
from handlers.start import register_start_handlers
from handlers.profile import register_profile_handlers
from handlers.bookings import register_booking_handlers
from handlers.help import register_help_handlers
from handlers.admin import register_admin_handlers
from handlers.common import register_common_handlers


def setup_bot():
    """Set up the bot with all handlers and middleware"""
    dp = Dispatcher(storage=MemoryStorage())

    # Register all handlers
    register_start_handlers(dp)
    register_auth_handlers(dp)
    register_profile_handlers(dp)
    register_booking_handlers(dp)
    register_help_handlers(dp)
    register_admin_handlers(dp)  # Register admin handlers
    register_common_handlers(dp)

    return dp
