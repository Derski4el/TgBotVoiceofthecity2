from sqlalchemy import create_engine, and_, or_, update, text
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import IntegrityError
from contextlib import contextmanager
import logging
import uuid
import secrets
import os
from datetime import datetime, timedelta

from DataBase.models import Base, Role, User, Location, Booking, Settings, VerificationToken

# Global engine and session factory
engine = None
Session = None


def init_db(db_path):
    """Initialize the database with SQLAlchemy"""
    global engine, Session

    # Create SQLite engine
    connection_string = f"sqlite:///{db_path}"
    engine = create_engine(connection_string, echo=False)

    # Create session factory
    Session = scoped_session(sessionmaker(bind=engine))

    # Force check for schema changes and recreate if needed
    logging.info("Checking database schema...")
    needs_recreation = check_if_needs_recreation(db_path)

    if needs_recreation:
        logging.info("Database schema needs update - recreating tables...")
        recreate_database_tables()
    else:
        # Create tables if they don't exist
        Base.metadata.create_all(engine)

    # Initialize default data
    with session_scope() as session:
        # Create default roles if they don't exist
        if not session.query(Role).filter_by(name="user").first():
            session.add(Role(name="user"))

        if not session.query(Role).filter_by(name="admin").first():
            session.add(Role(name="admin"))

        # Create default settings if they don't exist
        if not session.query(Settings).filter_by(key="cooldown_days").first():
            session.add(Settings(key="cooldown_days", value="2"))

        # Create email settings if they don't exist
        if not session.query(Settings).filter_by(key="smtp_server").first():
            session.add(Settings(key="smtp_server", value="smtp.gmail.com"))

        if not session.query(Settings).filter_by(key="smtp_port").first():
            session.add(Settings(key="smtp_port", value="587"))

        if not session.query(Settings).filter_by(key="smtp_username").first():
            session.add(Settings(key="smtp_username", value="your-email@gmail.com"))

        if not session.query(Settings).filter_by(key="smtp_password").first():
            session.add(Settings(key="smtp_password", value="your-app-password"))

        if not session.query(Settings).filter_by(key="email_from").first():
            session.add(Settings(key="email_from", value="Voice of the City <your-email@gmail.com>"))

    logging.info("Database initialized successfully")


def check_if_needs_recreation(db_path):
    """Check if database needs recreation due to schema changes"""
    if not os.path.exists(db_path):
        return False

    try:
        # Try to connect and check table structure
        temp_engine = create_engine(f"sqlite:///{db_path}")
        with temp_engine.connect() as conn:
            # Check if users table exists
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='users'"))
            if not result.fetchone():
                temp_engine.dispose()
                return False

            # Check table structure
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]

            logging.info(f"Current users table columns: {columns}")

            # Check for old schema (passport column) or missing new schema (verified column)
            if 'passport' in columns:
                logging.info("Found passport column - database needs recreation")
                temp_engine.dispose()
                return True

            if 'verified' not in columns:
                logging.info("Missing verified column - database needs recreation")
                temp_engine.dispose()
                return True

        temp_engine.dispose()
        return False
    except Exception as e:
        logging.error(f"Error checking database schema: {e}")
        return True  # Force recreation if we can't check


def recreate_database_tables():
    """Recreate database tables with new schema"""
    try:
        logging.info("Starting database recreation process...")

        # Backup existing data
        backup_data = backup_existing_data()
        logging.info("Data backup completed")

        # Drop all tables
        Base.metadata.drop_all(engine)
        logging.info("Dropped old tables")

        # Create new tables
        Base.metadata.create_all(engine)
        logging.info("Created new tables with updated schema")

        # Restore data
        restore_data(backup_data)
        logging.info("Restored data to new schema")

        # Verify the new schema
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            new_columns = [row[1] for row in result.fetchall()]
            logging.info(f"New users table columns: {new_columns}")

            if 'passport' not in new_columns and 'verified' in new_columns:
                logging.info("✅ Database recreation successful - passport column removed, verified column added")
            else:
                logging.error("❌ Database recreation failed - schema not updated correctly")

    except Exception as e:
        logging.error(f"Error recreating database: {e}")
        raise


def backup_existing_data():
    """Backup existing data before recreation"""
    backup = {
        'users': [],
        'locations': [],
        'bookings': [],
        'roles': [],
        'settings': [],
        'verification_tokens': []
    }

    try:
        with engine.connect() as conn:
            # Backup users (excluding passport, including verified if exists)
            try:
                # First check what columns exist
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]

                # Build SELECT query based on available columns
                user_columns = ['id', 'first_name', 'patronymic', 'second_name', 'email', 'confirm_email',
                                'phone', 'confirm_phone', 'hash_password', 'cooldown', 'role_id',
                                'agreements_status', 'telegram_id', 'saved_telegram_id']

                # Add verified column if it exists
                if 'verified' in columns:
                    user_columns.append('verified')

                # Filter out columns that don't exist
                existing_columns = [col for col in user_columns if col in columns]

                query = f"SELECT {', '.join(existing_columns)} FROM users"
                result = conn.execute(text(query))
                backup['users'] = [dict(row._mapping) for row in result.fetchall()]
                logging.info(f"Backed up {len(backup['users'])} users")
            except Exception as e:
                logging.warning(f"Could not backup users: {e}")

            # Backup other tables
            for table in ['locations', 'bookings', 'roles', 'settings', 'verification_tokens']:
                try:
                    result = conn.execute(text(f"SELECT * FROM {table}"))
                    backup[table] = [dict(row._mapping) for row in result.fetchall()]
                    logging.info(f"Backed up {len(backup[table])} {table}")
                except Exception as e:
                    logging.warning(f"Could not backup {table}: {e}")

    except Exception as e:
        logging.error(f"Error during backup: {e}")

    return backup


def restore_data(backup_data):
    """Restore data after recreation"""
    with session_scope() as session:
        try:
            # Restore roles first
            for role_data in backup_data['roles']:
                role = Role(name=role_data['name'])
                role.id = role_data['id']
                session.merge(role)

            # Restore settings
            for setting_data in backup_data['settings']:
                setting = Settings(key=setting_data['key'], value=setting_data['value'])
                setting.id = setting_data['id']
                session.merge(setting)

            # Restore locations
            for location_data in backup_data['locations']:
                location = Location(address=location_data['address'], img=location_data['img'])
                location.id = location_data['id']
                session.merge(location)

            # Restore users (without passport, with verified)
            for user_data in backup_data['users']:
                user = User(
                    first_name=user_data['first_name'],
                    patronymic=user_data.get('patronymic', ''),
                    second_name=user_data['second_name'],
                    email=user_data['email'],
                    phone=user_data['phone'],
                    hash_password=user_data['hash_password'],
                    role_id=user_data['role_id'],
                    telegram_id=user_data.get('telegram_id'),
                    saved_telegram_id=user_data.get('saved_telegram_id')
                )
                user.id = user_data['id']
                user.confirm_email = user_data.get('confirm_email', False)
                user.confirm_phone = user_data.get('confirm_phone', False)
                user.cooldown = user_data.get('cooldown', datetime.now().isoformat())
                user.agreements_status = user_data.get('agreements_status', True)
                user.verified = user_data.get('verified', False)  # Restore verified status or default to False
                session.merge(user)

            # Restore bookings
            for booking_data in backup_data['bookings']:
                booking = Booking()
                booking.id = booking_data['id']
                booking.user_id = booking_data['user_id']
                booking.location_id = booking_data['location_id']
                booking.date = booking_data['date']
                booking.time = booking_data['time']
                booking.duration_hours = booking_data['duration_hours']
                booking.created_at = booking_data['created_at']
                session.merge(booking)

            # Restore verification tokens
            for token_data in backup_data['verification_tokens']:
                token = VerificationToken(
                    user_id=token_data['user_id'],
                    token=token_data['token'],
                    type=token_data['type']
                )
                token.id = token_data['id']
                token.created_at = token_data['created_at']
                token.expires_at = token_data['expires_at']
                token.is_used = token_data.get('is_used', False)
                session.merge(token)

            session.commit()
            logging.info("Successfully restored all data")

        except Exception as e:
            logging.error(f"Error restoring data: {e}")
            session.rollback()
            raise


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logging.error(f"Database error: {e}")
        raise
    finally:
        session.close()


def close_db():
    """Close database connections"""
    if Session:
        Session.remove()
    if engine:
        engine.dispose()


# User functions
def add_user(user_data):
    """Add a new user to the database"""
    with session_scope() as session:
        try:
            # Debug: Check if email already exists
            email = user_data['email']
            phone = user_data['phone']

            logging.info(f"Attempting to add user with email: {email}, phone: {phone}")

            # Check for existing email
            existing_email_user = session.query(User).filter_by(email=email).first()
            if existing_email_user:
                logging.error(f"Email {email} already exists for user ID: {existing_email_user.id}")
                raise ValueError("Пользователь с таким email уже зарегистрирован")

            # Check for existing phone
            existing_phone_user = session.query(User).filter_by(phone=phone).first()
            if existing_phone_user:
                logging.error(f"Phone {phone} already exists for user ID: {existing_phone_user.id}")
                raise ValueError("Пользователь с таким номером телефона уже зарегистрирован")

            # Get default role
            role_id = user_data.get('role_id') or get_default_role()
            if not role_id:
                raise ValueError("Не удалось найти роль пользователя")

            # Create new user
            new_user = User(
                first_name=user_data['first_name'],
                patronymic=user_data.get('patronymic', ''),
                second_name=user_data['second_name'],
                email=email,
                phone=phone,
                hash_password=user_data['hash_password'],
                role_id=role_id,
                telegram_id=user_data.get('telegram_id'),
                saved_telegram_id=user_data.get('saved_telegram_id')
            )

            # Set phone verification status if provided
            if 'confirm_phone' in user_data:
                new_user.confirm_phone = user_data['confirm_phone']

            # Set verified status if provided (default is False)
            if 'verified' in user_data:
                new_user.verified = user_data['verified']

            session.add(new_user)
            session.flush()  # Flush to get the ID and check for constraint violations

            logging.info(f"User successfully added with ID: {new_user.id}")
            return new_user.id

        except IntegrityError as e:
            error_msg = str(e).lower()
            logging.error(f"IntegrityError: {e}")

            if "email" in error_msg or "unique" in error_msg:
                if "email" in error_msg:
                    raise ValueError("Пользователь с таким email уже зарегистрирован")
                elif "phone" in error_msg:
                    raise ValueError("Пользователь с таким номером телефона уже зарегистрирован")
                else:
                    raise ValueError("Пользователь с такими данными уже зарегистрирован")
            else:
                raise ValueError("Ошибка при регистрации пользователя")
        except ValueError as e:
            # Re-raise ValueError as is
            raise e
        except Exception as e:
            logging.error(f"Unexpected error in add_user: {e}")
            raise ValueError(f"Неожиданная ошибка при регистрации: {str(e)}")


def update_user(user_id, first_name, patronymic, second_name, email, phone, role_id, confirm_email, confirm_phone,
                verified=None):
    """Update user information"""
    with session_scope() as session:
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False

            # Update user fields
            user.first_name = first_name
            user.patronymic = patronymic
            user.second_name = second_name
            user.email = email
            user.phone = phone
            user.role_id = role_id
            user.confirm_email = confirm_email
            user.confirm_phone = confirm_phone

            # Update verified status if provided
            if verified is not None:
                user.verified = verified

            return True
        except Exception as e:
            logging.error(f"Error updating user: {e}")
            return False


def update_user_verification_status(user_id, verified):
    """Update user verification status"""
    with session_scope() as session:
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False

            user.verified = verified
            return True
        except Exception as e:
            logging.error(f"Error updating user verification status: {e}")
            return False


def get_user_by_email(email):
    """Get user by email"""
    with session_scope() as session:
        user = session.query(User).filter_by(email=email).first()
        return user_to_dict(user) if user else None


def get_user_by_phone(phone):
    """Get user by phone"""
    with session_scope() as session:
        user = session.query(User).filter_by(phone=phone).first()
        return user_to_dict(user) if user else None


def get_user_by_id(user_id):
    """Get user by ID"""
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        return user_to_dict(user) if user else None


def get_user_by_telegram_id(telegram_id):
    """Get user by Telegram ID"""
    with session_scope() as session:
        user = session.query(User).filter_by(telegram_id=telegram_id).first()
        return user_to_dict(user) if user else None


def get_all_users():
    """Get all users"""
    with session_scope() as session:
        users = session.query(User).all()
        return [user_to_dict(user) for user in users]


def update_user_telegram_id(user_id, telegram_id):
    """Update user's Telegram ID"""
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.telegram_id = telegram_id
            return True
        return False


def remove_user_telegram_id(user_id):
    """Remove user's Telegram ID"""
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.telegram_id = None
            return True
        return False


def update_user_email_verification(user_id, verified):
    """Update user email verification status"""
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.confirm_email = verified
            return True
        return False


def update_user_phone_verification(user_id, verified):
    """Update user phone verification status"""
    with session_scope() as session:
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.confirm_phone = verified
            return True
        return False


# Debug function to check existing users
def debug_existing_users():
    """Debug function to check existing users in database"""
    with session_scope() as session:
        users = session.query(User).all()
        logging.info(f"Total users in database: {len(users)}")
        for user in users:
            logging.info(f"User: ID={user.id}, Email={user.email}, Phone={user.phone}, Verified={user.verified}")
        return users


# Verification token functions
def create_verification_token(user_id, type):
    """Create a verification token for email or phone"""
    with session_scope() as session:
        # Generate a secure token
        token = secrets.token_urlsafe(32)

        # Check if there are existing unused tokens for this user and type
        existing_tokens = session.query(VerificationToken).filter(
            and_(
                VerificationToken.user_id == user_id,
                VerificationToken.type == type,
                VerificationToken.is_used == False
            )
        ).all()

        # Mark existing tokens as used
        for existing_token in existing_tokens:
            existing_token.is_used = True

        # Create a new token
        new_token = VerificationToken(
            user_id=user_id,
            token=token,
            type=type
        )

        session.add(new_token)
        session.flush()

        return token


def verify_token(token, type):
    """Verify a token and update user verification status"""
    with session_scope() as session:
        # Find the token
        token_obj = session.query(VerificationToken).filter(
            and_(
                VerificationToken.token == token,
                VerificationToken.type == type,
                VerificationToken.is_used == False
            )
        ).first()

        if not token_obj:
            return False, "Недействительный или использованный токен"

        # Check if token is expired
        try:
            expires_at = datetime.fromisoformat(token_obj.expires_at)
            if expires_at < datetime.now():
                return False, "Срок действия токена истек"
        except ValueError:
            return False, "Ошибка проверки срока действия токена"

        # Mark token as used
        token_obj.is_used = True

        # Update user verification status
        user = session.query(User).filter_by(id=token_obj.user_id).first()
        if not user:
            return False, "Пользователь не найден"

        if type == 'email':
            user.confirm_email = True
        elif type == 'phone':
            user.confirm_phone = True

        return True, "Верификация успешно завершена"


def get_email_settings():
    """Get email settings from database"""
    with session_scope() as session:
        settings = {}
        for key in ['smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'email_from']:
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                settings[key] = setting.value

        return settings


def update_email_settings(settings_data):
    """Update email settings"""
    with session_scope() as session:
        for key, value in settings_data.items():
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                setting.value = value
            else:
                session.add(Settings(key=key, value=value))

        return True


# Role functions
def get_default_role():
    """Get default user role ID"""
    with session_scope() as session:
        role = session.query(Role).filter_by(name="user").first()
        return role.id if role else None


def get_admin_role():
    """Get admin role ID"""
    with session_scope() as session:
        role = session.query(Role).filter_by(name="admin").first()
        return role.id if role else None


def get_all_roles():
    """Get all roles"""
    with session_scope() as session:
        roles = session.query(Role).all()
        return [{"id": role.id, "name": role.name} for role in roles]


def set_user_role(user_id, role_name):
    """Set user role by role name"""
    with session_scope() as session:
        role = session.query(Role).filter_by(name=role_name).first()
        if not role:
            return False, f"Role '{role_name}' not found"

        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return False, "User not found"

        user.role_id = role.id
        return True, f"User role updated to {role_name}"


# Location functions
def add_location(location_data):
    """Add a new location"""
    with session_scope() as session:
        new_location = Location(
            address=location_data['address'],
            img=location_data['img']
        )
        session.add(new_location)
        session.flush()  # Flush to get the ID
        return new_location.id


def update_location(location_id, address):
    """Update location information"""
    with session_scope() as session:
        try:
            location = session.query(Location).filter_by(id=location_id).first()
            if not location:
                return False

            location.address = address
            return True
        except Exception as e:
            logging.error(f"Error updating location: {e}")
            return False


def get_location_by_id(location_id):
    """Get location by ID"""
    with session_scope() as session:
        location = session.query(Location).filter_by(id=location_id).first()
        return location_to_dict(location) if location else None


def get_all_locations():
    """Get all locations"""
    with session_scope() as session:
        locations = session.query(Location).all()
        return [location_to_dict(location) for location in locations]


# Cooldown functions
def check_user_cooldown(user_id):
    """Check if user is in cooldown period - DISABLED"""
    return False, None


def get_cooldown_days():
    """Get cooldown days setting"""
    with session_scope() as session:
        setting = session.query(Settings).filter_by(key="cooldown_days").first()
        return int(setting.value) if setting else 2


def set_cooldown_days(days):
    """Set cooldown days setting"""
    with session_scope() as session:
        setting = session.query(Settings).filter_by(key="cooldown_days").first()
        if setting:
            setting.value = str(days)
            return True
        return False


# Time interval checking functions
def time_to_minutes(time_str):
    """Convert time string (HH:MM) to minutes since midnight"""
    try:
        hours, minutes = map(int, time_str.split(':'))
        return hours * 60 + minutes
    except:
        return None


def check_time_overlap(new_start, new_duration, existing_start, existing_duration):
    """Check if two time intervals overlap"""
    # Convert times to minutes
    new_start_min = time_to_minutes(new_start)
    existing_start_min = time_to_minutes(existing_start)

    if new_start_min is None or existing_start_min is None:
        return False

    # Calculate end times
    new_end_min = new_start_min + (new_duration * 60)
    existing_end_min = existing_start_min + (existing_duration * 60)

    # Check for overlap: intervals overlap if new_start < existing_end AND new_end > existing_start
    return new_start_min < existing_end_min and new_end_min > existing_start_min


def get_location_schedule(location_id, date):
    """Get detailed schedule for a location on a specific date"""
    with session_scope() as session:
        # Get all bookings for this location and date
        bookings = session.query(Booking).filter(
            and_(
                Booking.location_id == location_id,
                Booking.date == date
            )
        ).order_by(Booking.time).all()

        # Create time slots from 9:00 to 22:00
        schedule = []
        for hour in range(9, 23):
            time_slot = f"{hour:02d}:00"

            # Check if this hour is occupied
            is_occupied = False
            occupying_booking = None

            for booking in bookings:
                booking_start = time_to_minutes(booking.time)
                booking_end = booking_start + (booking.duration_hours * 60)
                current_hour_minutes = hour * 60

                # Check if current hour falls within any booking
                if booking_start <= current_hour_minutes < booking_end:
                    is_occupied = True
                    occupying_booking = booking
                    break

            schedule.append({
                'time': time_slot,
                'hour': hour,
                'is_occupied': is_occupied,
                'booking': booking_to_dict(occupying_booking) if occupying_booking else None,
                'can_book_1h': not is_occupied,
                'can_book_2h': not is_occupied and hour < 20  # Can book 2h if current and next hour are free
            })

        # Check 2-hour availability more precisely
        for i, slot in enumerate(schedule):
            if not slot['is_occupied'] and i < len(schedule) - 1:
                next_slot = schedule[i + 1]
                slot['can_book_2h'] = not next_slot['is_occupied']

        return schedule


def get_available_time_suggestions(location_id, date, requested_start, requested_duration):
    """Get alternative time suggestions when requested time is not available"""
    with session_scope() as session:
        # Get all bookings for this location and date
        existing_bookings = session.query(Booking).filter(
            and_(
                Booking.location_id == location_id,
                Booking.date == date
            )
        ).all()

        suggestions = []

        # Check common time slots (every hour from 9:00 to 20:00)
        for hour in range(9, 21):
            for duration in [1, 2]:
                start_time = f"{hour:02d}:00"

                # Skip if this is the same as requested (we know it's not available)
                if start_time == requested_start and duration == requested_duration:
                    continue

                # Skip 2-hour slots that would go past 21:00
                if duration == 2 and hour >= 20:
                    continue

                # Check if this slot is available
                is_available = True
                for booking in existing_bookings:
                    if check_time_overlap(start_time, duration, booking.time, booking.duration_hours):
                        is_available = False
                        break

                if is_available:
                    end_hour = hour + duration
                    suggestions.append({
                        'start_time': start_time,
                        'duration': duration,
                        'end_time': f"{end_hour:02d}:00",
                        'description': f"{start_time}-{end_hour:02d}:00 ({duration} час{'а' if duration == 2 else ''})"
                    })

        # Sort suggestions by start time
        suggestions.sort(key=lambda x: x['start_time'])

        return suggestions[:5]  # Return first 5 suggestions


def format_schedule_visualization(schedule):
    """Format schedule as a visual text representation"""
    lines = []
    lines.append("📅 Расписание на выбранную дату:")
    lines.append("")

    # Group consecutive occupied hours
    i = 0
    while i < len(schedule):
        slot = schedule[i]

        if slot['is_occupied']:
            # Find the end of this booking
            booking = slot['booking']
            start_hour = slot['hour']
            end_hour = start_hour + booking['duration_hours']

            lines.append(f"🔴 {start_hour:02d}:00-{end_hour:02d}:00 - Занято")

            # Skip hours that are part of this booking
            while i < len(schedule) and schedule[i]['hour'] < end_hour:
                i += 1
        else:
            # Free slot
            hour = slot['hour']
            availability = []

            if slot['can_book_1h']:
                availability.append("1ч")
            if slot['can_book_2h']:
                availability.append("2ч")

            if availability:
                avail_text = "/".join(availability)
                lines.append(f"🟢 {hour:02d}:00 - Свободно ({avail_text})")
            else:
                lines.append(f"🟡 {hour:02d}:00 - Ограниченно")

            i += 1

    lines.append("")
    lines.append("🟢 - Можно забронировать")
    lines.append("🔴 - Занято")
    lines.append("🟡 - Частично доступно")

    return "\n".join(lines)


# Booking functions
def create_booking(user_id, location_id, date, time, duration_hours):
    """Create a new booking with time overlap checking and verification check"""
    logging.info(
        f"Creating booking: user_id={user_id}, location_id={location_id}, date={date}, time={time}, duration={duration_hours}")

    try:
        with session_scope() as session:
            # Check if user is verified
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False, "Пользователь не найден"

            if not user.verified:
                return False, "Ваш аккаунт не подтвержден администратором. Обратитесь к администратору для подтверждения."

            # Get all existing bookings for this location and date
            existing_bookings = session.query(Booking).filter(
                and_(
                    Booking.location_id == location_id,
                    Booking.date == date
                )
            ).all()

            # Check for time overlaps with existing bookings
            for existing_booking in existing_bookings:
                if check_time_overlap(time, duration_hours, existing_booking.time, existing_booking.duration_hours):
                    logging.error(
                        f"Time overlap detected: new {time}-{duration_hours}h conflicts with existing {existing_booking.time}-{existing_booking.duration_hours}h")

                    # Get schedule visualization
                    schedule = get_location_schedule(location_id, date)
                    schedule_text = format_schedule_visualization(schedule)

                    # Get alternative suggestions
                    suggestions = get_available_time_suggestions(location_id, date, time, duration_hours)

                    if suggestions:
                        suggestion_text = "\n\n💡 Доступные альтернативы:\n" + "\n".join([
                            f"• {s['description']}" for s in suggestions
                        ])
                    else:
                        suggestion_text = "\n\n❌ К сожалению, на эту дату нет свободных слотов."

                    return False, f"Выбранное время пересекается с существующим бронированием.\n\n{schedule_text}{suggestion_text}"

            # Get cooldown days within the same session
            cooldown_setting = session.query(Settings).filter_by(key="cooldown_days").first()
            cooldown_days = int(cooldown_setting.value) if cooldown_setting else 2

            # Create the booking with explicit values
            booking_id = str(uuid.uuid4())
            created_at = datetime.now().isoformat()

            new_booking = Booking()
            new_booking.id = booking_id
            new_booking.user_id = user_id
            new_booking.location_id = location_id
            new_booking.date = date
            new_booking.time = time
            new_booking.duration_hours = duration_hours
            new_booking.created_at = created_at

            session.add(new_booking)

            # Update user cooldown
            booking_date = datetime.fromisoformat(date)
            cooldown_end = booking_date + timedelta(days=cooldown_days)

            # Update the same user object we already retrieved
            user.cooldown = cooldown_end.isoformat()

            # Commit the transaction
            session.commit()

            logging.info(f"✅ Booking created successfully: {booking_id}")
            return True, "Бронирование успешно создано"

    except Exception as e:
        logging.error(f"Error in create_booking: {e}")
        return False, f"Ошибка при создании бронирования: {str(e)}"


def get_booking_by_id(booking_id):
    """Get booking by ID"""
    with session_scope() as session:
        booking = session.query(
            Booking, Location.address.label('location_address')
        ).join(
            Location, Booking.location_id == Location.id
        ).filter(
            Booking.id == booking_id
        ).first()

        if not booking:
            return None

        booking_dict = booking_to_dict(booking[0])
        booking_dict['location_address'] = booking[1]
        return booking_dict


def update_booking(booking_id, date, time, duration_hours):
    """Update booking information with overlap checking"""
    with session_scope() as session:
        try:
            booking = session.query(Booking).filter_by(id=booking_id).first()
            if not booking:
                return False

            # Check for overlaps with other bookings (excluding this one)
            existing_bookings = session.query(Booking).filter(
                and_(
                    Booking.location_id == booking.location_id,
                    Booking.date == date,
                    Booking.id != booking_id  # Exclude current booking
                )
            ).all()

            # Check for time overlaps
            for existing_booking in existing_bookings:
                if check_time_overlap(time, duration_hours, existing_booking.time, existing_booking.duration_hours):
                    logging.error(f"Time overlap detected during update")
                    return False

            # Update booking
            booking.date = date
            booking.time = time
            booking.duration_hours = duration_hours
            return True
        except Exception as e:
            logging.error(f"Error updating booking: {e}")
            return False


def get_user_bookings(user_id):
    """Get all bookings for a user"""
    with session_scope() as session:
        logging.info(f"Getting bookings for user: {user_id}")

        bookings = session.query(
            Booking, Location.address.label('location_address')
        ).join(
            Location, Booking.location_id == Location.id
        ).filter(
            Booking.user_id == user_id
        ).order_by(
            Booking.date, Booking.time
        ).all()

        result = []
        for booking, location_address in bookings:
            booking_dict = booking_to_dict(booking)
            booking_dict['location_address'] = location_address
            result.append(booking_dict)

        logging.info(f"Found {len(result)} bookings for user {user_id}")
        return result


def cancel_booking(booking_id, user_id):
    """Cancel a booking"""
    with session_scope() as session:
        # Check if booking exists and belongs to user
        booking = session.query(Booking).filter(
            and_(
                Booking.id == booking_id,
                Booking.user_id == user_id
            )
        ).first()

        if not booking:
            return False, "Бронирование не найдено"

        # Delete the booking
        session.delete(booking)

        # Reset user cooldown
        user = session.query(User).filter_by(id=user_id).first()
        if user:
            user.cooldown = datetime.now().isoformat()

        return True, "Бронирование успешно отменено"


def get_all_bookings_with_users():
    """Get all bookings with user and location info"""
    with session_scope() as session:
        bookings = session.query(
            Booking,
            Location.address.label('location_address'),
            User.id.label('user_id'),
            User.first_name,
            User.second_name,
            User.email,
            User.phone
        ).join(
            Location, Booking.location_id == Location.id
        ).join(
            User, Booking.user_id == User.id
        ).order_by(
            Booking.date, Booking.time
        ).all()

        result = []
        for booking, location_address, user_id, first_name, second_name, email, phone in bookings:
            booking_dict = booking_to_dict(booking)
            booking_dict['location_address'] = location_address
            booking_dict['available'] = False
            booking_dict['speaker'] = {
                'id': user_id,
                'first_name': first_name,
                'second_name': second_name,
                'email': email,
                'phone': phone
            }
            result.append(booking_dict)

        return result


def debug_database_tables():
    """Debug function to check database contents"""
    with session_scope() as session:
        booking_count = session.query(Booking).count()
        logging.info(f"Total bookings in database: {booking_count}")

        location_count = session.query(Location).count()
        logging.info(f"Total locations in database: {location_count}")

        user_count = session.query(User).count()
        logging.info(f"Total users in database: {user_count}")

        # Show all bookings
        bookings = session.query(Booking).all()
        for booking in bookings:
            logging.info(f"Booking: {booking_to_dict(booking)}")

        return True


# Helper functions to convert SQLAlchemy objects to dictionaries
def user_to_dict(user):
    """Convert User object to dictionary"""
    if not user:
        return None

    return {
        'id': user.id,
        'first_name': user.first_name,
        'patronymic': user.patronymic,
        'second_name': user.second_name,
        'email': user.email,
        'confirm_email': user.confirm_email,
        'phone': user.phone,
        'confirm_phone': user.confirm_phone,
        'hash_password': user.hash_password,
        'cooldown': user.cooldown,
        'role_id': user.role_id,
        'agreements_status': user.agreements_status,
        'telegram_id': user.telegram_id,
        'saved_telegram_id': user.saved_telegram_id,
        'verified': user.verified,
        'artist_form_filled': user.artist_form_filled
    }


def location_to_dict(location):
    """Convert Location object to dictionary"""
    if not location:
        return None

    return {
        'id': location.id,
        'address': location.address,
        'img': location.img
    }


def booking_to_dict(booking):
    """Convert Booking object to dictionary"""
    if not booking:
        return None

    return {
        'id': booking.id,
        'user_id': booking.user_id,
        'location_id': booking.location_id,
        'date': booking.date,
        'time': booking.time,
        'duration_hours': booking.duration_hours,
        'created_at': booking.created_at
    }


def update_user_artist_form_status(user_id: str, status: bool) -> bool:
    """Обновляет статус заполнения анкеты артиста"""
    try:
        with session_scope() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False

            user.artist_form_filled = status
            session.commit()
            return True
    except Exception as e:
        logging.error(f"Error updating artist form status: {e}")
        return False


def update_booking_status(booking_id: str, status: str) -> bool:
    """Обновляет статус бронирования"""
    try:
        with session_scope() as session:
            booking = session.query(Booking).filter_by(id=booking_id).first()
            if not booking:
                return False

            booking.status = status
            session.commit()
            return True
    except Exception as e:
        logging.error(f"Error updating booking status: {e}")
        return False


def get_booking_by_id(booking_id: str) -> dict:
    """Получает информацию о бронировании по ID"""
    try:
        with session_scope() as session:
            booking = session.query(Booking).filter_by(id=booking_id).first()
            return booking_to_dict(booking) if booking else None
    except Exception as e:
        logging.error(f"Error getting booking by ID: {e}")
        return None


def delete_user(user_id: str) -> bool:
    """Delete user from database"""
    try:
        with session_scope() as session:
            # Удаляем все связанные записи
            session.execute(text("DELETE FROM bookings WHERE user_id = :user_id"), {"user_id": user_id})
            session.execute(text("DELETE FROM verification_tokens WHERE user_id = :user_id"), {"user_id": user_id})
            
            # Удаляем пользователя
            result = session.execute(text("DELETE FROM users WHERE id = :user_id"), {"user_id": user_id})
            session.commit()
            return result.rowcount > 0
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
        return False


def delete_booking(booking_id: str) -> bool:
    """Delete booking from database"""
    try:
        with session_scope() as session:
            # Удаляем бронирование
            result = session.execute(text("DELETE FROM bookings WHERE id = :booking_id"), {"booking_id": booking_id})
            session.commit()
            return result.rowcount > 0
    except Exception as e:
        logging.error(f"Error deleting booking: {e}")
        return False
