from DataBase import database

def get_user_from_message(message):
    """Get user from database by Telegram ID"""
    if not message.from_user:
        return None
    
    telegram_id = str(message.from_user.id)
    return database.get_user_by_telegram_id(telegram_id)
