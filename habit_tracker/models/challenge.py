from datetime import datetime, date, timedelta
from typing import Dict, Any


class Challenge:
    def __init__(
        self,
        challenge_id: str,
        challenger_id: str,
        challenger_name: str,
        opponent_id: str,
        opponent_name: str,
        habit_name: str,
        duration_days: int = 7,
        start_date: str = None,
        status: str = "pending",
        challenger_score: int = 0,
        opponent_score: int = 0,
        winner_id: str = None
    ) -> None:
        self.challenge_id = challenge_id
        self.challenger_id = challenger_id
        self.challenger_name = challenger_name
        self.opponent_id = opponent_id
        self.opponent_name = opponent_name
        self.habit_name = habit_name
        self.duration_days = duration_days
        self.start_date = start_date or date.today().isoformat()
        start_dt = datetime.strptime(self.start_date, "%Y-%m-%d").date()
        self.end_date = (start_dt + timedelta(days=duration_days)).isoformat()
        self.status = status
        self.challenger_score = challenger_score
        self.opponent_score = opponent_score
        self.winner_id = winner_id

    def accept(self) -> None:
        self.status = "active"
        self.start_date = date.today().isoformat()
        start_dt = date.today()
        self.end_date = (start_dt + timedelta(days=self.duration_days)).isoformat()

    def decline(self) -> None:
        self.status = "declined"

    def update_scores(self, c_score: int, o_score: int) -> None:
        self.challenger_score = c_score
        self.opponent_score = o_score
        if date.today().isoformat() >= self.end_date:
            self.status = "completed"
            if self.challenger_score > self.opponent_score:
                self.winner_id = self.challenger_id
            elif self.opponent_score > self.challenger_score:
                self.winner_id = self.opponent_id
            else:
                self.winner_id = "TIE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "challenger_id": self.challenger_id,
            "challenger_name": self.challenger_name,
            "opponent_id": self.opponent_id,
            "opponent_name": self.opponent_name,
            "habit_name": self.habit_name,
            "duration_days": self.duration_days,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "challenger_score": self.challenger_score,
            "opponent_score": self.opponent_score,
            "winner_id": self.winner_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Challenge":
        return cls(
            challenge_id=data["challenge_id"],
            challenger_id=data["challenger_id"],
            challenger_name=data["challenger_name"],
            opponent_id=data["opponent_id"],
            opponent_name=data["opponent_name"],
            habit_name=data["habit_name"],
            duration_days=data.get("duration_days", 7),
            start_date=data.get("start_date"),
            status=data.get("status", "pending"),
            challenger_score=data.get("challenger_score", 0),
            opponent_score=data.get("opponent_score", 0),
            winner_id=data.get("winner_id")
        )