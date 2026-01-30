from sqlalchemy import Column, String, Integer, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class Role(Base):
    __tablename__ = 'roles'

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, unique=True)

    # Relationship
    users = relationship("User", back_populates="role")

    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name

class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True)
    first_name = Column(String, nullable=False)
    patronymic = Column(String, nullable=True)
    second_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    confirm_email = Column(Boolean, default=False)
    phone = Column(String, nullable=False, unique=True)
    confirm_phone = Column(Boolean, default=False)
    hash_password = Column(String, nullable=False)
    cooldown = Column(String, nullable=False)  # ISO format date string
    role_id = Column(String, ForeignKey('roles.id'), nullable=False)
    agreements_status = Column(Boolean, default=False)
    telegram_id = Column(String, nullable=True)
    saved_telegram_id = Column(String, nullable=True)
    verified = Column(Boolean, default=False)  # New field for admin verification
    artist_form_filled = Column(Boolean, default=False)  # Новое поле для статуса анкеты

    # Relationships
    role = relationship("Role", back_populates="users")
    bookings = relationship("Booking", back_populates="user")
    verification_tokens = relationship("VerificationToken", back_populates="user")

    def __init__(self, first_name, patronymic, second_name, email, phone, hash_password, role_id,
                 telegram_id=None, saved_telegram_id=None):
        self.id = str(uuid.uuid4())
        self.first_name = first_name
        self.patronymic = patronymic
        self.second_name = second_name
        self.email = email
        self.confirm_email = False
        self.phone = phone
        self.confirm_phone = False
        self.hash_password = hash_password
        self.cooldown = datetime.now().isoformat()
        self.role_id = role_id
        self.agreements_status = True
        self.telegram_id = telegram_id
        self.saved_telegram_id = saved_telegram_id
        self.verified = False  # Default to not verified

class Location(Base):
    __tablename__ = 'locations'

    id = Column(String, primary_key=True)
    address = Column(String, nullable=False)
    img = Column(String, nullable=False)

    # Relationship
    bookings = relationship("Booking", back_populates="location")

    def __init__(self, address, img):
        self.id = str(uuid.uuid4())
        self.address = address
        self.img = img

class Booking(Base):
    __tablename__ = 'bookings'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    location_id = Column(String, ForeignKey('locations.id'), nullable=False)
    date = Column(String, nullable=False)  # ISO format date string
    time = Column(String, nullable=False)
    duration_hours = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False)  # ISO format datetime string

    # Relationships
    user = relationship("User", back_populates="bookings")
    location = relationship("Location", back_populates="bookings")

    def __init__(self, user_id=None, location_id=None, date=None, time=None, duration_hours=None):
        if user_id is not None:  # Only set values if provided
            self.id = str(uuid.uuid4())
            self.user_id = user_id
            self.location_id = location_id
            self.date = date
            self.time = time
            self.duration_hours = duration_hours
            self.created_at = datetime.now().isoformat()

class Settings(Base):
    __tablename__ = 'settings'

    id = Column(String, primary_key=True)
    key = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)

    def __init__(self, key, value):
        self.id = str(uuid.uuid4())
        self.key = key
        self.value = value

class VerificationToken(Base):
    __tablename__ = 'verification_tokens'

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('users.id'), nullable=False)
    token = Column(String, nullable=False, unique=True)
    type = Column(String, nullable=False)  # 'email' or 'phone'
    created_at = Column(String, nullable=False)  # ISO format datetime string
    expires_at = Column(String, nullable=False)  # ISO format datetime string
    is_used = Column(Boolean, default=False)

    # Relationship
    user = relationship("User", back_populates="verification_tokens")

    def __init__(self, user_id, token, type):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.token = token
        self.type = type
        self.created_at = datetime.now().isoformat()
        self.expires_at = (datetime.now() + datetime.timedelta(days=1)).isoformat()
        self.is_used = False
