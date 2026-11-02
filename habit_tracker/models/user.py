import re
import hashlib
import secrets
from datetime import datetime
from typing import Dict, Any, List
from habit_tracker.storage.exceptions import InvalidEmailError, InvalidPasswordError


class User:
    EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

    def __init__(
        self,
        user_id: str,
        email: str,
        password_hash: str,
        salt: str,
        display_name: str,
        avatar: str = "👤",
        all_time_points: int = 0,
        badges: List[str] = None,
        created_at: str = None
    ) -> None:
        self._user_id = user_id
        self._email = self.validate_and_normalize_email(email)
        self._password_hash = password_hash
        self._salt = salt
        self._display_name = display_name.strip() or self._email.split("@")[0]
        self._avatar = avatar
        self._all_time_points = max(0, int(all_time_points))
        self._badges = badges or []
        self._created_at = created_at or datetime.now().isoformat()

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def email(self) -> str:
        return self._email

    @property
    def display_name(self) -> str:
        return self._display_name

    @property
    def avatar(self) -> str:
        return self._avatar

    @property
    def all_time_points(self) -> int:
        return self._all_time_points

    @property
    def badges(self) -> List[str]:
        return list(self._badges)

    def add_points(self, points: int) -> None:
        if points > 0:
            self._all_time_points += points

    def add_badge(self, badge: str) -> None:
        if badge and badge not in self._badges:
            self._badges.append(badge)

    @staticmethod
    def validate_and_normalize_email(email: str) -> str:
        clean_email = email.strip().lower()
        if not clean_email or not User.EMAIL_REGEX.match(clean_email):
            raise InvalidEmailError(
                f"Invalid email address '{email}'. Please provide a valid email format. Phone numbers are not allowed."
            )
        return clean_email

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        if not password or len(password) < 4:
            raise InvalidPasswordError("Password must be at least 4 characters in length.")
        if salt is None:
            salt = secrets.token_hex(16)
        salted_bytes = (password + salt).encode("utf-8")
        hashed_pw = hashlib.sha256(salted_bytes).hexdigest()
        return hashed_pw, salt

    def verify_password(self, candidate_password: str) -> bool:
        candidate_hash, _ = self.hash_password(candidate_password, self._salt)
        return secrets.compare_digest(candidate_hash, self._password_hash)

    def set_new_password(self, new_password: str) -> None:
        new_hash, new_salt = self.hash_password(new_password)
        self._password_hash = new_hash
        self._salt = new_salt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self._user_id,
            "email": self._email,
            "password_hash": self._password_hash,
            "salt": self._salt,
            "display_name": self._display_name,
            "avatar": self._avatar,
            "all_time_points": self._all_time_points,
            "badges": self._badges,
            "created_at": self._created_at
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        return cls(
            user_id=data["user_id"],
            email=data["email"],
            password_hash=data["password_hash"],
            salt=data["salt"],
            display_name=data.get("display_name", ""),
            avatar=data.get("avatar", "👤"),
            all_time_points=data.get("all_time_points", 0),
            badges=data.get("badges", []),
            created_at=data.get("created_at")
        )