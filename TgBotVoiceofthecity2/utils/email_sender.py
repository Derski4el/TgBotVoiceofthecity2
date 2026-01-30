import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from DataBase import database


def send_verification_email(user_email, user_name, verification_token, base_url):
    """Send verification email to user"""
    try:
        # Get email settings from database
        settings = database.get_email_settings()

        # Create verification link
        verification_link = f"{base_url}/verify/email/{verification_token}"

        # Create email message
        msg = MIMEMultipart()
        msg['From'] = settings.get('email_from', 'Voice of the City <noreply@example.com>')
        msg['To'] = user_email
        msg['Subject'] = 'Подтверждение email - Voice of the City'

        # Email body
        body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #4caf50; color: white; padding: 10px; text-align: center; }}
                .content {{ padding: 20px; background-color: #f9f9f9; }}
                .button {{ display: inline-block; background-color: #4caf50; color: white; padding: 10px 20px; 
                          text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 20px; font-size: 12px; color: #777; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Voice of the City</h1>
                </div>
                <div class="content">
                    <h2>Здравствуйте, {user_name}!</h2>
                    <p>Спасибо за регистрацию в системе Voice of the City. Для подтверждения вашего email, пожалуйста, нажмите на кнопку ниже:</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Подтвердить email</a>
                    </p>
                    <p>Или перейдите по следующей ссылке:</p>
                    <p><a href="{verification_link}">{verification_link}</a></p>
                    <p>Если вы не регистрировались в нашей системе, просто проигнорируйте это письмо.</p>
                </div>
                <div class="footer">
                    <p>© 2025 Voice of the City. Все права защищены.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Attach HTML content
        msg.attach(MIMEText(body, 'html'))

        # Connect to SMTP server and send email
        server = smtplib.SMTP(settings.get('smtp_server', 'smtp.gmail.com'),
                              int(settings.get('smtp_port', 587)))
        server.starttls()
        server.login(settings.get('smtp_username', ''),
                     settings.get('smtp_password', ''))
        server.send_message(msg)
        server.quit()

        logging.info(f"Verification email sent to {user_email}")
        return True
    except Exception as e:
        logging.error(f"Error sending verification email: {e}")
        return False


def send_test_email(email_address, settings):
    """Send a test email to verify email settings"""
    try:
        # Create email message
        msg = MIMEMultipart()
        msg['From'] = settings.get('email_from', 'Voice of the City <noreply@example.com>')
        msg['To'] = email_address
        msg['Subject'] = 'Тестовое письмо - Voice of the City'

        # Email body
        body = """
        <html>
        <body>
            <h1>Тестовое письмо</h1>
            <p>Это тестовое письмо для проверки настроек SMTP.</p>
            <p>Если вы получили это письмо, значит настройки SMTP работают корректно.</p>
        </body>
        </html>
        """

        # Attach HTML content
        msg.attach(MIMEText(body, 'html'))

        # Connect to SMTP server and send email
        server = smtplib.SMTP(settings.get('smtp_server', 'smtp.gmail.com'),
                              int(settings.get('smtp_port', 587)))
        server.starttls()
        server.login(settings.get('smtp_username', ''),
                     settings.get('smtp_password', ''))
        server.send_message(msg)
        server.quit()

        logging.info(f"Test email sent to {email_address}")
        return True, "Тестовое письмо успешно отправлено"
    except Exception as e:
        logging.error(f"Error sending test email: {e}")
        return False, f"Ошибка отправки письма: {str(e)}"
