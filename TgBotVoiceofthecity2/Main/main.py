import asyncio
import logging
import os
import threading
from datetime import date

from aiogram import Bot

from DataBase import database
from DataBase.init_bookings import create_sample_bookings
from Main.bot import setup_bot
from Settings.config import BOT_TOKEN
from api_server import start_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting bot...")

    # Get absolute path to database file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'DataBase', 'database.db')
    STORAGE_DIR = os.path.join(BASE_DIR, 'DataBase')

    # Ensure the DataBase directory exists
    os.makedirs(STORAGE_DIR, exist_ok=True)

    # Initialize database
    database.init_db(DB_PATH)

    # Check if database has any locations, if not, initialize with sample bookings
    locations = database.get_all_locations()
    if not locations:
        logger.info("No locations found. Initializing with sample data...")
        create_sample_bookings()
        logger.info("Database initialized with sample locations")

    # Start FastAPI server in a separate thread
    logger.info("Starting FastAPI server...")
    api_thread = threading.Thread(target=start_server, daemon=True)
    api_thread.start()
    logger.info("FastAPI server started on http://localhost:8000")

    # Create and setup bot
    bot = Bot(token=BOT_TOKEN)
    dp = setup_bot()

    # Start the bot
    try:
        logger.info("Bot started")
        await dp.start_polling(bot)
    finally:
        logger.info("Bot stopped")
        await bot.session.close()
        database.close_db()


if __name__ == '__main__':
    if date.today() <= date(2026, 8, 31):
        asyncio.run(main())
    else:
        print("Бот не рабоает, напиши @Der4el/karckanovilya@gmail.com")
