from datetime import datetime
from typing import List, Dict, Optional, Any


def filter_users(
        users: List[Dict],
        search: Optional[str] = None,
        role: Optional[str] = None,
        email_verified: Optional[bool] = None,
        phone_verified: Optional[bool] = None,
        has_telegram: Optional[bool] = None,
        sort_by: str = "first_name",
        sort_order: str = "asc"
) -> List[Dict]:
    """
    Filter and sort users based on various criteria

    Args:
        users: List of user dictionaries
        search: Search term for name, surname, or email
        role: Filter by role ID
        email_verified: Filter by email verification status
        phone_verified: Filter by phone verification status
        has_telegram: Filter by presence of Telegram ID
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        Filtered and sorted list of users
    """
    filtered_users = users.copy()

    # Apply search filter
    if search:
        search_lower = search.lower()
        filtered_users = [
            user for user in filtered_users
            if (
                    search_lower in user.get('first_name', '').lower() or
                    search_lower in user.get('second_name', '').lower() or
                    search_lower in user.get('patronymic', '').lower() or
                    search_lower in user.get('email', '').lower() or
                    search_lower in user.get('phone', '').lower()
            )
        ]

    # Apply role filter
    if role:
        filtered_users = [
            user for user in filtered_users
            if user.get('role_id') == role
        ]

    # Apply email verification filter
    if email_verified is not None:
        filtered_users = [
            user for user in filtered_users
            if user.get('confirm_email', False) == email_verified
        ]

    # Apply phone verification filter
    if phone_verified is not None:
        filtered_users = [
            user for user in filtered_users
            if user.get('confirm_phone', False) == phone_verified
        ]

    # Apply Telegram ID filter
    if has_telegram is not None:
        if has_telegram:
            filtered_users = [
                user for user in filtered_users
                if user.get('telegram_id') is not None and user.get('telegram_id') != ''
            ]
        else:
            filtered_users = [
                user for user in filtered_users
                if user.get('telegram_id') is None or user.get('telegram_id') == ''
            ]

    # Apply sorting
    reverse_order = sort_order.lower() == 'desc'

    def get_sort_key(user):
        value = user.get(sort_by, '')
        if value is None:
            return ''

        # Handle datetime fields
        if sort_by == 'cooldown':
            try:
                return datetime.fromisoformat(str(value))
            except (ValueError, TypeError):
                return datetime.min

        # Handle boolean fields
        if isinstance(value, bool):
            return value

        # Handle string fields
        return str(value).lower()

    try:
        filtered_users.sort(key=get_sort_key, reverse=reverse_order)
    except Exception:
        # Fallback to simple string sorting if there's an error
        filtered_users.sort(key=lambda x: str(x.get(sort_by, '')).lower(), reverse=reverse_order)

    return filtered_users


def filter_bookings(
        bookings: List[Dict],
        search: Optional[str] = None,
        location_id: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        duration: Optional[int] = None,
        sort_by: str = "date",
        sort_order: str = "asc"
) -> List[Dict]:
    """
    Filter and sort bookings based on various criteria

    Args:
        bookings: List of booking dictionaries
        search: Search term for location address or participant name
        location_id: Filter by location ID
        date_from: Filter by date from (YYYY-MM-DD format)
        date_to: Filter by date to (YYYY-MM-DD format)
        duration: Filter by duration in hours
        sort_by: Field to sort by
        sort_order: Sort order ('asc' or 'desc')

    Returns:
        Filtered and sorted list of bookings
    """
    filtered_bookings = bookings.copy()

    # Apply search filter
    if search:
        search_lower = search.lower()
        filtered_bookings = [
            booking for booking in filtered_bookings
            if (
                    search_lower in booking.get('location_address', '').lower() or
                    (booking.get('speaker') and (
                            search_lower in booking['speaker'].get('first_name', '').lower() or
                            search_lower in booking['speaker'].get('second_name', '').lower() or
                            search_lower in booking['speaker'].get('email', '').lower() or
                            search_lower in booking['speaker'].get('phone', '').lower()
                    ))
            )
        ]

    # Apply location filter
    if location_id:
        filtered_bookings = [
            booking for booking in filtered_bookings
            if booking.get('location_id') == location_id
        ]

    # Apply date range filters
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            filtered_bookings = [
                booking for booking in filtered_bookings
                if _parse_booking_date(booking.get('date')) >= date_from_obj
            ]
        except ValueError:
            pass  # Invalid date format, skip filter

    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            filtered_bookings = [
                booking for booking in filtered_bookings
                if _parse_booking_date(booking.get('date')) <= date_to_obj
            ]
        except ValueError:
            pass  # Invalid date format, skip filter

    # Apply duration filter
    if duration is not None:
        filtered_bookings = [
            booking for booking in filtered_bookings
            if booking.get('duration_hours') == duration
        ]

    # Apply sorting
    reverse_order = sort_order.lower() == 'desc'

    def get_sort_key(booking):
        value = booking.get(sort_by, '')

        if sort_by == 'date':
            return _parse_booking_date(value)
        elif sort_by == 'time':
            try:
                return datetime.strptime(str(value), '%H:%M').time()
            except (ValueError, TypeError):
                return datetime.min.time()
        elif sort_by == 'location_address':
            return str(booking.get('location_address', '')).lower()
        elif sort_by == 'speaker_name':
            speaker = booking.get('speaker', {})
            if speaker:
                return f"{speaker.get('first_name', '')} {speaker.get('second_name', '')}".lower()
            return ''
        elif sort_by == 'duration_hours':
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        elif sort_by == 'created_at':
            try:
                return datetime.fromisoformat(str(value))
            except (ValueError, TypeError):
                return datetime.min

        # Default string sorting
        return str(value).lower()

    try:
        filtered_bookings.sort(key=get_sort_key, reverse=reverse_order)
    except Exception:
        # Fallback to simple string sorting if there's an error
        filtered_bookings.sort(key=lambda x: str(x.get(sort_by, '')).lower(), reverse=reverse_order)

    return filtered_bookings


def _parse_booking_date(date_str: Any) -> datetime.date:
    """
    Parse booking date string to date object

    Args:
        date_str: Date string in various formats

    Returns:
        Parsed date object or minimum date if parsing fails
    """
    if not date_str:
        return datetime.min.date()

    try:
        # Try ISO format first
        return datetime.fromisoformat(str(date_str)).date()
    except (ValueError, TypeError):
        try:
            # Try other common formats
            return datetime.strptime(str(date_str), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            try:
                return datetime.strptime(str(date_str), '%d.%m.%Y').date()
            except (ValueError, TypeError):
                return datetime.min.date()


def get_filter_stats(users: List[Dict], bookings: List[Dict]) -> Dict[str, Any]:
    """
    Get statistics for filters

    Args:
        users: List of all users
        bookings: List of all bookings

    Returns:
        Dictionary with filter statistics
    """
    stats = {
        'total_users': len(users),
        'verified_email_users': len([u for u in users if u.get('confirm_email')]),
        'verified_phone_users': len([u for u in users if u.get('confirm_phone')]),
        'users_with_telegram': len([u for u in users if u.get('telegram_id')]),
        'total_bookings': len(bookings),
        'bookings_by_duration': {},
        'bookings_by_location': {}
    }

    # Count bookings by duration
    for booking in bookings:
        duration = booking.get('duration_hours', 0)
        stats['bookings_by_duration'][duration] = stats['bookings_by_duration'].get(duration, 0) + 1

    # Count bookings by location
    for booking in bookings:
        location = booking.get('location_address', 'Unknown')
        stats['bookings_by_location'][location] = stats['bookings_by_location'].get(location, 0) + 1

    return stats
