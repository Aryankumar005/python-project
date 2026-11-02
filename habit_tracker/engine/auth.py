import smtplib
import secrets
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from habit_tracker.models.user import User
from habit_tracker.storage.db import DataManager
from habit_tracker.storage.exceptions import (
    UserAlreadyExistsError, UserNotFoundError, InvalidPasswordError,
    NetworkUnavailableError, OTPExpiredError, InvalidOTPError
)


class AuthService:
    def __init__(self, db: DataManager, smtp_sender: Optional[str] = None, smtp_password: Optional[str] = None) -> None:
        self.db = db
        self.smtp_sender = smtp_sender
        self.smtp_password = smtp_password
        self._otp_records: Dict[str, Dict[str, Any]] = {}

    def register_user(self, email: str, password: str, display_name: str = "") -> User:
        clean_email = User.validate_and_normalize_email(email)
        if self.db.find_user_by_email(clean_email):
            raise UserAlreadyExistsError(f"An account with email '{clean_email}' already exists. Please log in.")

        user_id = f"usr_{secrets.token_hex(6)}"
        password_hash, salt = User.hash_password(password)
        user = User(user_id=user_id, email=clean_email, password_hash=password_hash, salt=salt, display_name=display_name or clean_email.split("@")[0])
        self.db.save_user(user.to_dict())
        self.db.get_user_social(user_id)
        return user

    def authenticate_user(self, email: str, password: str) -> User:
        clean_email = User.validate_and_normalize_email(email)
        user_data = self.db.find_user_by_email(clean_email)
        if not user_data:
            raise UserNotFoundError(f"No account found registered under '{clean_email}'.")

        user = User.from_dict(user_data)
        if not user.verify_password(password):
            raise InvalidPasswordError("Incorrect password. Please verify your credentials and try again.")
        return user

    def generate_and_send_otp(self, email: str) -> str:
        clean_email = User.validate_and_normalize_email(email)
        if not self.db.find_user_by_email(clean_email):
            raise UserNotFoundError(f"No account registered with email '{clean_email}'.")

        otp_code = str(secrets.randbelow(9000) + 1000)
        self._otp_records[clean_email] = {
            "code": otp_code,
            "expires_at": datetime.now() + timedelta(minutes=5),
            "attempts": 0
        }
        self._dispatch_email_smtp(clean_email, otp_code)
        return otp_code

    def _dispatch_email_smtp(self, recipient_email: str, otp_code: str) -> None:
        if not self.smtp_sender or not self.smtp_password:
            raise NetworkUnavailableError("Unable to reach the email server. Please check your internet connection and try again.")

        msg = MIMEText(f"Hello,\n\nYour Habit Tracker verification code is: {otp_code}\nExpires in 5 minutes.")
        msg["Subject"] = "Your Verification Code - Daily Habit Tracker"
        msg["From"] = self.smtp_sender
        msg["To"] = recipient_email

        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_sender, self.smtp_password)
                server.send_message(msg)
        except Exception:
            raise NetworkUnavailableError("Unable to reach the email server. Please check your internet connection and try again.")

    def verify_otp_and_reset_password(self, email: str, entered_otp: str, new_password: str) -> bool:
        clean_email = User.validate_and_normalize_email(email)
        record = self._otp_records.get(clean_email)
        if not record:
            raise InvalidOTPError("No pending verification code found. Please request a new OTP.")

        if datetime.now() > record["expires_at"]:
            del self._otp_records[clean_email]
            raise OTPExpiredError("Your verification code has expired. Please request a new one.")

        record["attempts"] += 1
        if record["attempts"] > 3:
            del self._otp_records[clean_email]
            raise InvalidOTPError("Too many incorrect attempts. For security, please request a fresh code.")

        if record["code"] != entered_otp.strip():
            raise InvalidOTPError("Incorrect verification code. Please check your email and try again.")

        user_data = self.db.find_user_by_email(clean_email)
        user = User.from_dict(user_data)
        user.set_new_password(new_password)
        self.db.save_user(user.to_dict())
        del self._otp_records[clean_email]
        return True