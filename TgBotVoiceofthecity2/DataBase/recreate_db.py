"""
Simple database recreation script
This script will completely recreate the database with the new schema
"""
import os
import sys
import logging
import shutil
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataBase import database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def recreate_database():
    """Completely recreate the database"""
    # Get absolute path to database file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'DataBase', 'database.db')

    logger.info(f"Database path: {DB_PATH}")

    try:
        # Backup existing database if it exists
        if os.path.exists(DB_PATH):
            backup_path = f"{DB_PATH}.backup_{int(datetime.now().timestamp())}"
            shutil.copy2(DB_PATH, backup_path)
            logger.info(f"Created backup: {backup_path}")

            # Remove old database
            os.remove(DB_PATH)
            logger.info("Removed old database file")

        # Initialize new database
        logger.info("Creating new database with updated schema...")
        database.init_db(DB_PATH)

        # Verify the new schema
        logger.info("Verifying new database schema...")
        with database.engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            logger.info(f"New users table columns: {columns}")

            if 'passport' not in columns:
                logger.info("✅ Schema verification successful - passport column not found")
            else:
                logger.error("❌ Schema verification failed - passport column still exists")
                return False

        # Test user creation
        logger.info("Testing user creation...")
        test_user_data = {
            'first_name': 'Test',
            'patronymic': '',
            'second_name': 'User',
            'email': f'test_{int(datetime.now().timestamp())}@test.com',
            'phone': f'+7919{int(datetime.now().timestamp()) % 10000000}',
            'hash_password': 'test_hash',
            'role_id': database.get_default_role(),
            'confirm_phone': True
        }

        try:
            user_id = database.add_user(test_user_data)
            logger.info(f"✅ Test user created successfully: {user_id}")

            # Clean up test user
            with database.session_scope() as session:
                test_user = session.query(database.User).filter_by(id=user_id).first()
                if test_user:
                    session.delete(test_user)
                    logger.info("Test user cleaned up")
        except Exception as e:
            logger.error(f"❌ Test user creation failed: {e}")
            return False

        # Initialize sample locations
        logger.info("Initializing sample locations...")
        from DataBase.init_bookings import create_sample_bookings
        create_sample_bookings()

        return True

    except Exception as e:
        logger.error(f"Error during database recreation: {e}")
        return False
    finally:
        database.close_db()


if __name__ == "__main__":
    logger.info("🔄 Starting database recreation...")

    # Ask for confirmation
    print("⚠️  WARNING: This will completely recreate the database!")
    print("All existing data will be lost (but backed up).")
    response = input("Do you want to continue? (yes/no): ").lower().strip()

    if response in ['yes', 'y']:
        success = recreate_database()

        if success:
            logger.info("🎉 Database recreation completed successfully!")
            print("\n✅ Database has been recreated successfully!")
            print("You can now restart the bot and try registration again.")
        else:
            logger.error("❌ Database recreation failed!")
            print("\n❌ Database recreation failed!")
            print("Please check the logs for more details.")
    else:
        print("Operation cancelled.")
