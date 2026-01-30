import os
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import secrets
from datetime import datetime
from typing import Optional
from pathlib import Path

from DataBase import database
from utils.admin import format_bookings_data, format_users_data
from utils.email_sender import send_verification_email, send_test_email
from Settings.config import ADMIN_API_USERNAME, ADMIN_API_PASSWORD

# Get absolute path to database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'DataBase', 'database.db')

# Create templates and static directories if they don't exist
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
os.makedirs(TEMPLATES_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, 'css'), exist_ok=True)

# Initialize FastAPI app
app = FastAPI(title="Voice of the City Admin API", description="Admin API for Voice of the City Telegram Bot")

# Mount static files directory
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize security
security = HTTPBasic()

# Путь к директории с документами пользователей
USER_DOCS_DIR = Path(__file__).parent / "user_docs"


def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials"""
    correct_username = secrets.compare_digest(credentials.username, ADMIN_API_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_API_PASSWORD)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={
                "WWW-Authenticate": 'Basic realm="Secure Area"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            },
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Root endpoint"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/users", response_class=HTMLResponse)
async def get_users(request: Request, admin: str = Depends(get_current_admin)):
    """Get all users as HTML table"""
    users = database.get_all_users()
    roles = database.get_all_roles()
    users_data = format_users_data(users)

    return templates.TemplateResponse("users.html", {
        "request": request,
        "users": users_data,
        "roles": roles
    })


@app.get("/users/{user_id}/edit", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: str, admin: str = Depends(get_current_admin)):
    """Show form to edit a user"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    roles = database.get_all_roles()
    return templates.TemplateResponse("edit_user.html", {
        "request": request,
        "user": user,
        "roles": roles
    })


@app.post("/users/{user_id}/edit")
async def update_user(
        request: Request,
        user_id: str,
        first_name: str = Form(...),
        patronymic: Optional[str] = Form(""),
        second_name: str = Form(...),
        email: str = Form(...),
        phone: str = Form(...),
        role_id: str = Form(...),
        confirm_email: bool = Form(False),
        confirm_phone: bool = Form(False),
        verified: bool = Form(False),
        admin: str = Depends(get_current_admin)
):
    """Update user information"""
    success = database.update_user(
        user_id=user_id,
        first_name=first_name,
        patronymic=patronymic,
        second_name=second_name,
        email=email,
        phone=phone,
        role_id=role_id,
        confirm_email=confirm_email,
        confirm_phone=confirm_phone,
        verified=verified
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update user")

    return RedirectResponse(url="/users", status_code=303)


@app.post("/users/{user_id}/verify")
async def verify_user(user_id: str, admin: str = Depends(get_current_admin)):
    """Verify user account"""
    success = database.update_user_verification_status(user_id, True)
    if success:
        return {"status": "success", "message": "Пользователь успешно подтвержден"}
    return {"status": "error", "message": "Не удалось подтвердить пользователя"}


@app.post("/users/{user_id}/unverify")
async def unverify_user(user_id: str, admin: str = Depends(get_current_admin)):
    """Unverify user account"""
    success = database.update_user_verification_status(user_id, False)
    if success:
        return {"status": "success", "message": "Подтверждение пользователя отменено"}
    return {"status": "error", "message": "Не удалось отменить подтверждение пользователя"}


@app.get("/users/{user_id}/send-verification", response_class=HTMLResponse)
async def send_verification_form(request: Request, user_id: str, admin: str = Depends(get_current_admin)):
    """Show form to send verification email"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return templates.TemplateResponse("send_verification.html", {
        "request": request,
        "user": user
    })


@app.post("/users/{user_id}/send-verification")
async def send_verification(
        request: Request,
        background_tasks: BackgroundTasks,
        user_id: str,
        verification_type: str = Form(...),
        admin: str = Depends(get_current_admin)
):
    """Send verification email or SMS"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get base URL from request
    base_url = str(request.base_url).rstrip('/')

    if verification_type == 'email':
        # Create verification token
        token = database.create_verification_token(user_id, 'email')

        # Send verification email in background
        background_tasks.add_task(
            send_verification_email,
            user['email'],
            f"{user['first_name']} {user['second_name']}",
            token,
            base_url
        )

        return RedirectResponse(
            url=f"/users/{user_id}/edit?message=Verification+email+sent",
            status_code=303
        )

    elif verification_type == 'phone':
        # Phone verification would be implemented here
        # For now, just return a message
        return RedirectResponse(
            url=f"/users/{user_id}/edit?message=Phone+verification+not+implemented+yet",
            status_code=303
        )

    else:
        raise HTTPException(status_code=400, detail="Invalid verification type")


@app.get("/verify/email/{token}")
async def verify_email(request: Request, token: str):
    """Verify email with token"""
    success, message = database.verify_token(token, 'email')

    return templates.TemplateResponse("verification_result.html", {
        "request": request,
        "success": success,
        "message": message
    })


@app.get("/email-settings", response_class=HTMLResponse)
async def email_settings_form(request: Request, admin: str = Depends(get_current_admin)):
    """Show form to edit email settings"""
    settings = database.get_email_settings()

    return templates.TemplateResponse("email_settings.html", {
        "request": request,
        "settings": settings
    })


@app.post("/email-settings")
async def update_email_settings(
        request: Request,
        smtp_server: str = Form(...),
        smtp_port: str = Form(...),
        smtp_username: str = Form(...),
        smtp_password: str = Form(...),
        email_from: str = Form(...),
        admin: str = Depends(get_current_admin)
):
    """Update email settings"""
    settings = {
        'smtp_server': smtp_server,
        'smtp_port': smtp_port,
        'smtp_username': smtp_username,
        'smtp_password': smtp_password,
        'email_from': email_from
    }

    success = database.update_email_settings(settings)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update email settings")

    return RedirectResponse(url="/email-settings?message=Settings+updated", status_code=303)


@app.post("/test-email")
async def test_email(
        request: Request,
        test_email: str = Form(...),
        admin: str = Depends(get_current_admin)
):
    """Send test email"""
    settings = database.get_email_settings()
    success, message = send_test_email(test_email, settings)

    if not success:
        return templates.TemplateResponse("email_settings.html", {
            "request": request,
            "settings": settings,
            "error": message
        })

    return templates.TemplateResponse("email_settings.html", {
        "request": request,
        "settings": settings,
        "success": message
    })


@app.get("/bookings", response_class=HTMLResponse)
async def get_bookings(
        request: Request,
        admin: str = Depends(get_current_admin),
        search: Optional[str] = Query(None, description="Поиск по названию точки")
):
    """Get all locations with their bookings"""
    # Get all locations first
    all_locations = database.get_all_locations()

    # Apply search filter to locations if provided
    if search:
        search_lower = search.lower()
        filtered_locations = [
            location for location in all_locations
            if search_lower in location.get('address', '').lower()
        ]
    else:
        filtered_locations = all_locations

    # Get all bookings
    all_bookings = database.get_all_bookings_with_users()

    # Group bookings by location
    bookings_by_location = {}
    for booking in all_bookings:
        location_id = booking.get('location_id')
        if location_id not in bookings_by_location:
            bookings_by_location[location_id] = []
        bookings_by_location[location_id].append(booking)

    # Create locations data with their bookings
    locations_data = []
    for location in filtered_locations:
        location_id = location['id']
        location_bookings = bookings_by_location.get(location_id, [])

        locations_data.append({
            'id': location_id,
            'address': location['address'],
            'bookings': format_bookings_data(location_bookings)
        })

    # Count total bookings for search results
    total_bookings = sum(len(bookings_by_location.get(loc['id'], [])) for loc in all_locations)
    filtered_bookings = sum(len(loc['bookings']) for loc in locations_data)

    return templates.TemplateResponse("bookings.html", {
        "request": request,
        "locations_data": locations_data,
        "search": search or '',
        "total_locations": len(all_locations),
        "filtered_locations": len(filtered_locations),
        "total_bookings": total_bookings,
        "filtered_bookings": filtered_bookings
    })


@app.get("/locations/{location_id}/edit", response_class=HTMLResponse)
async def edit_location_form(request: Request, location_id: str, admin: str = Depends(get_current_admin)):
    """Show form to edit a location"""
    location = database.get_location_by_id(location_id)
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")

    return templates.TemplateResponse("edit_location.html", {
        "request": request,
        "location": location
    })


@app.post("/locations/{location_id}/edit")
async def update_location(
        request: Request,
        location_id: str,
        address: str = Form(...),
        admin: str = Depends(get_current_admin)
):
    """Update location information"""
    success = database.update_location(
        location_id=location_id,
        address=address
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update location")

    return RedirectResponse(url="/bookings", status_code=303)


@app.get("/bookings/{booking_id}/edit", response_class=HTMLResponse)
async def edit_booking_form(request: Request, booking_id: str, admin: str = Depends(get_current_admin)):
    """Show form to edit a booking"""
    booking = database.get_booking_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return templates.TemplateResponse("edit_booking.html", {
        "request": request,
        "booking": booking
    })


@app.post("/bookings/{booking_id}/edit")
async def update_booking(
        request: Request,
        booking_id: str,
        date: str = Form(...),
        time: str = Form(...),
        duration_hours: int = Form(...),
        admin: str = Depends(get_current_admin)
):
    """Update booking information"""
    success = database.update_booking(
        booking_id=booking_id,
        date=date,
        time=time,
        duration_hours=duration_hours
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to update booking")

    return RedirectResponse(url="/bookings", status_code=303)


@app.post("/bookings/{booking_id}/delete")
async def delete_booking(booking_id: str, admin: str = Depends(get_current_admin)):
    """Delete booking"""
    success = database.delete_booking(booking_id)
    if success:
        return {"status": "success", "message": "Бронирование успешно удалено"}
    return {"status": "error", "message": "Не удалось удалить бронирование"}


@app.get("/users/{user_id}/documents")
async def get_user_documents(request: Request, user_id: str, admin: str = Depends(get_current_admin)):
    """Get list of user's documents"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user_dir = USER_DOCS_DIR / str(user['telegram_id'])
    if not user_dir.exists():
        return templates.TemplateResponse("user_documents.html", {
            "request": request,
            "user": user,
            "documents": []
        })

    documents = []
    for file in user_dir.glob("*.docx"):
        documents.append({
            "name": file.name,
            "path": f"/users/{user_id}/documents/{file.name}",
            "date": datetime.fromtimestamp(file.stat().st_mtime).strftime("%d.%m.%Y %H:%M:%S")
        })

    return templates.TemplateResponse("user_documents.html", {
        "request": request,
        "user": user,
        "documents": documents
    })


@app.get("/users/{user_id}/documents/{filename}")
async def download_user_document(user_id: str, filename: str, admin: str = Depends(get_current_admin)):
    """Download user's document"""
    user = database.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_path = USER_DOCS_DIR / str(user['telegram_id']) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.post("/users/{user_id}/delete")
async def delete_user(user_id: str, admin: str = Depends(get_current_admin)):
    """Delete user"""
    success = database.delete_user(user_id)
    if success:
        return {"status": "success", "message": "Пользователь успешно удален"}
    return {"status": "error", "message": "Не удалось удалить пользователя"}


def start_server():
    """Start the FastAPI server"""
    # Initialize database if not already initialized
    if not database.engine:
        database.init_db(DB_PATH)
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start_server()
