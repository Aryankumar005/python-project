from abc import ABC, abstractmethod
from typing import Dict, Any, Union
from datetime import datetime


class Habit(ABC):
    def __init__(
        self,
        habit_id: str,
        user_id: str,
        name: str,
        category: str,
        is_public: bool = True,
        created_at: str = None
    ) -> None:
        self._habit_id = habit_id
        self._user_id = user_id
        self._name = name.strip()
        self._category = category.strip()
        self._is_public = is_public
        self._created_at = created_at or datetime.now().isoformat()

    @property
    def habit_id(self) -> str:
        return self._habit_id

    @property
    def user_id(self) -> str:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def category(self) -> str:
        return self._category

    @property
    def is_public(self) -> bool:
        return self._is_public

    @is_public.setter
    def is_public(self, value: bool) -> None:
        self._is_public = bool(value)

    @property
    def created_at(self) -> str:
        return self._created_at

    @abstractmethod
    def habit_type(self) -> str:
        pass

    @abstractmethod
    def evaluate_completion(self, recorded_value: Union[float, int, bool]) -> bool:
        pass

    @abstractmethod
    def format_target(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Habit":
        htype = data.get("type", "binary")
        if htype == "binary":
            return BinaryHabit(
                habit_id=data["habit_id"],
                user_id=data["user_id"],
                name=data["name"],
                category=data.get("category", "General"),
                is_public=data.get("is_public", True),
                created_at=data.get("created_at")
            )
        elif htype == "numeric":
            return NumericHabit(
                habit_id=data["habit_id"],
                user_id=data["user_id"],
                name=data["name"],
                target_value=float(data["target_value"]),
                unit=data["unit"],
                operator=data.get("operator", ">="),
                category=data.get("category", "General"),
                is_public=data.get("is_public", True),
                created_at=data.get("created_at")
            )
        else:
            raise ValueError(f"Unknown habit type: {htype}")


class BinaryHabit(Habit):
    def habit_type(self) -> str:
        return "binary"

    def evaluate_completion(self, recorded_value: Union[float, int, bool]) -> bool:
        if isinstance(recorded_value, bool):
            return recorded_value
        try:
            return float(recorded_value) > 0.0
        except (ValueError, TypeError):
            return False

    def format_target(self) -> str:
        return "Complete (Yes / No)"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "habit_id": self.habit_id,
            "user_id": self.user_id,
            "name": self.name,
            "category": self.category,
            "type": self.habit_type(),
            "is_public": self.is_public,
            "created_at": self.created_at
        }


class NumericHabit(Habit):
    def __init__(
        self,
        habit_id: str,
        user_id: str,
        name: str,
        target_value: float,
        unit: str,
        operator: str = ">=",
        category: str = "General",
        is_public: bool = True,
        created_at: str = None
    ) -> None:
        super().__init__(habit_id, user_id, name, category, is_public, created_at)
        self._target_value = float(target_value)
        self._unit = unit.strip()
        self._operator = operator if operator in (">=", "<=") else ">="

    @property
    def target_value(self) -> float:
        return self._target_value

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def operator(self) -> str:
        return self._operator

    def habit_type(self) -> str:
        return "numeric"

    def evaluate_completion(self, recorded_value: Union[float, int, bool]) -> bool:
        try:
            val = float(recorded_value)
        except (ValueError, TypeError):
            return False

        if self._operator == ">=":
            return val >= self._target_value
        elif self._operator == "<=":
            return val <= self._target_value
        return False

    def format_target(self) -> str:
        return f"{self._operator} {self._target_value} {self._unit}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "habit_id": self.habit_id,
            "user_id": self.user_id,
            "name": self.name,
            "category": self.category,
            "type": self.habit_type(),
            "target_value": self.target_value,
            "unit": self.unit,
            "operator": self.operator,
            "is_public": self.is_public,
            "created_at": self.created_at
        }