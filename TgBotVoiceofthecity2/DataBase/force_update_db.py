"""
Force database schema update script
Run this script to manually update the database schema
"""
import os
import sys
import logging

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DataBase import database
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def force_update_database():
    """Force update the database schema"""
    # Get absolute path to database file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'DataBase', 'database.db')

    logger.info(f"Database path: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        logger.error("Database file not found!")
        return False

    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        database.init_db(DB_PATH)

        # Check current schema
        logger.info("Checking current database schema...")
        needs_update = database.check_if_needs_recreation(DB_PATH)

        if needs_update:
            logger.info("Database needs update - forcing recreation...")
            database.recreate_database_tables()
            logger.info("✅ Database update completed successfully!")
        else:
            logger.info("Database schema is already up to date")

        # Verify the new schema
        logger.info("Verifying database schema...")
        with database.engine.connect() as conn:
            result = conn.execute(database.text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            logger.info(f"Current users table columns: {columns}")

            if 'passport' not in columns:
                logger.info("✅ Schema verification successful - passport column not found")
            else:
                logger.error("❌ Schema verification failed - passport column still exists")
                return False

        # Verify users can be created
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

        return True

    except Exception as e:
        logger.error(f"Error during database update: {e}")
        return False
    finally:
        database.close_db()


if __name__ == "__main__":
    logger.info("🔄 Starting forced database update...")
    success = force_update_database()

    if success:
        logger.info("🎉 Database update completed successfully!")
        print("\n✅ Database has been updated successfully!")
        print("You can now restart the bot and try registration again.")
    else:
        logger.error("❌ Database update failed!")
        print("\n❌ Database update failed!")
        print("Please check the logs for more details.")
