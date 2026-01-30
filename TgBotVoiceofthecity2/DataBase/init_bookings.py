from datetime import datetime, timedelta
import os
import logging
from DataBase import database


def create_sample_bookings():
    """Create sample locations and time slots for testing"""
    # Get absolute path to database file
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, 'DataBase', 'database.db')

    # Initialize database if not already initialized
    if not database.engine:
        database.init_db(DB_PATH)

    # Create sample locations if they don't exist
    locations = database.get_all_locations()

    sample_locations = [
        {
            'address': 'Вдоль набережной реки Исеть у памятника Бажову',
            'img': '/path/to/location1.jpg'
        },
        {
            'address': 'Пересечение ул. Вайнера с Театральным пер., напротив Вайнера, 12',
            'img': '/path/to/location2.jpg'
        },
        {
            'address': 'Исторический сквер, напротив музея ИЗО',
            'img': '/path/to/location3.jpg'
        },
        {
            'address': 'ул. Вайнера, напротив дома Радищева, 12',
            'img': '/path/to/location4.jpg'
        },
        {
            'address': 'Октябрьская площадь, Смотровая площадка',
            'img': '/path/to/location5.jpg'
        }
    ]

    # If no locations exist, create them
    if not locations:
        location_ids = []
        for location in sample_locations:
            try:
                location_id = database.add_location(location)
                location_ids.append(location_id)
                logging.info(f"Created location: {location['address']}")
            except Exception as e:
                logging.error(f"Error creating location: {e}")
    else:
        location_ids = [location['id'] for location in locations]
        logging.info(f"Using existing locations: {len(location_ids)} found")

    logging.info(f"Sample data created successfully!")
    logging.info(f"Created or found {len(location_ids)} locations")

    # Print locations for reference
    for i, location in enumerate(sample_locations):
        logging.info(f"{i + 1}. {location['address']}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    create_sample_bookings()
