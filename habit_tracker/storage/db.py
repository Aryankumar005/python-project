import os
import json
import csv
from typing import Dict, List, Any, Optional
from habit_tracker.storage.exceptions import DataCorruptedError


class DataManager:
    def __init__(self, data_dir=None) -> None:
        if data_dir is None:
            storage_dir = os.path.dirname(os.path.abspath(__file__))
            habit_tracker_dir = os.path.dirname(storage_dir)
            project_root = os.path.dirname(habit_tracker_dir)
            self.data_dir = os.path.join(project_root, "data")
        else:
            self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

        self.users_file = os.path.join(self.data_dir, "users.json")
        self.habits_file = os.path.join(self.data_dir, "habits.json")
        self.social_file = os.path.join(self.data_dir, "social.json")
        self.challenges_file = os.path.join(self.data_dir, "challenges.json")
        self.logs_file = os.path.join(self.data_dir, "logs.csv")
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        json_defaults = [
            (self.users_file, {}),
            (self.habits_file, {}),
            (self.social_file, {}),
            (self.challenges_file, {}),
        ]
        for filepath, default_val in json_defaults:
            if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
                self._write_json_atomic(filepath, default_val)

        if not os.path.exists(self.logs_file) or os.path.getsize(self.logs_file) == 0:
            with open(self.logs_file, mode="w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["date", "user_id", "habit_id", "value", "completed"])

    def _read_json(self, filepath: str) -> Any:
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            return {}
        try:
            with open(filepath, mode="r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as err:
            raise DataCorruptedError(f"Corrupted JSON in {os.path.basename(filepath)}: {err}")
        except OSError as err:
            raise DataCorruptedError(f"Unable to read file {filepath}: {err}")

    def _write_json_atomic(self, filepath: str, data: Any) -> None:
        temp_filepath = f"{filepath}.tmp"
        try:
            with open(temp_filepath, mode="w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(temp_filepath, filepath)
        except Exception as err:
            if os.path.exists(temp_filepath):
                try: os.remove(temp_filepath)
                except OSError: pass
            raise DataCorruptedError(f"Failed to write atomically to {filepath}: {err}")

    def get_all_users(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(self.users_file)

    def save_user(self, user_dict: Dict[str, Any]) -> None:
        users = self.get_all_users()
        users[user_dict["user_id"]] = user_dict
        self._write_json_atomic(self.users_file, users)

    def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        clean_email = email.strip().lower()
        for user in self.get_all_users().values():
            if user.get("email", "").lower() == clean_email:
                return user
        return None

    def find_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self.get_all_users().get(user_id)

    def get_all_habits(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(self.habits_file)

    def get_user_habits(self, user_id: str) -> List[Dict[str, Any]]:
        return [h for h in self.get_all_habits().values() if h.get("user_id") == user_id]

    def save_habit(self, habit_dict: Dict[str, Any]) -> None:
        habits = self.get_all_habits()
        habits[habit_dict["habit_id"]] = habit_dict
        self._write_json_atomic(self.habits_file, habits)

    def get_social_graph(self) -> Dict[str, Dict[str, List[str]]]:
        return self._read_json(self.social_file)

    def save_social_graph(self, graph: Dict[str, Dict[str, List[str]]]) -> None:
        self._write_json_atomic(self.social_file, graph)

    def get_user_social(self, user_id: str) -> Dict[str, List[str]]:
        graph = self.get_social_graph()
        if user_id not in graph:
            graph[user_id] = {"following": [], "followers": [], "pending_incoming": []}
            self.save_social_graph(graph)
        return graph[user_id]

    def get_all_challenges(self) -> Dict[str, Dict[str, Any]]:
        return self._read_json(self.challenges_file)

    def save_challenge(self, challenge_dict: Dict[str, Any]) -> None:
        challenges = self.get_all_challenges()
        challenges[challenge_dict["challenge_id"]] = challenge_dict
        self._write_json_atomic(self.challenges_file, challenges)

    def log_activity(self, date_str: str, user_id: str, habit_id: str, value: float, completed: bool) -> None:
        existing_logs = self.read_all_logs()
        updated_logs = []
        replaced = False

        for row in existing_logs:
            if row["date"] == date_str and row["user_id"] == user_id and row["habit_id"] == habit_id:
                updated_logs.append({
                    "date": date_str, "user_id": user_id, "habit_id": habit_id,
                    "value": str(value), "completed": "1" if completed else "0"
                })
                replaced = True
            else:
                updated_logs.append(row)

        if not replaced:
            updated_logs.append({
                "date": date_str, "user_id": user_id, "habit_id": habit_id,
                "value": str(value), "completed": "1" if completed else "0"
            })
        self.write_all_logs(updated_logs)

    def read_all_logs(self) -> List[Dict[str, str]]:
        if not os.path.exists(self.logs_file) or os.path.getsize(self.logs_file) == 0:
            return []
        rows = []
        with open(self.logs_file, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(dict(row))
        return rows

    def write_all_logs(self, logs: List[Dict[str, str]]) -> None:
        temp_file = f"{self.logs_file}.tmp"
        fieldnames = ["date", "user_id", "habit_id", "value", "completed"]
        with open(temp_file, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in logs:
                writer.writerow(r)
        os.replace(temp_file, self.logs_file)

    def get_user_logs(self, user_id: str) -> List[Dict[str, str]]:
        return [row for row in self.read_all_logs() if row.get("user_id") == user_id]