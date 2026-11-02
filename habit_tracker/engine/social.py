import uuid
from datetime import timedelta, date
from typing import Dict, List, Any, Set

from habit_tracker.storage.db import DataManager
from habit_tracker.models.user import User
from habit_tracker.models.challenge import Challenge


class SocialEngine:
    def __init__(self, db: DataManager) -> None:
        self.db = db

    def send_follow_request(self, sender_id: str, target_id: str) -> bool:
        if sender_id == target_id:
            return False

        graph = self.db.get_social_graph()
        sender_social = graph.setdefault(sender_id, {"following": [], "followers": [], "pending_incoming": []})
        target_social = graph.setdefault(target_id, {"following": [], "followers": [], "pending_incoming": []})

        if target_id not in sender_social["following"]:
            sender_social["following"].append(target_id)
        if sender_id not in target_social["followers"]:
            target_social["followers"].append(sender_id)

        self.db.save_social_graph(graph)
        return True

    def get_mutual_friends(self, user_id: str) -> Set[str]:
        social = self.db.get_user_social(user_id)
        following_set: Set[str] = set(social.get("following", []))
        followers_set: Set[str] = set(social.get("followers", []))
        return following_set.intersection(followers_set)

    def calculate_14day_momentum_points(self, user_id: str) -> int:
        logs = self.db.get_user_logs(user_id)
        if not logs:
            return 0

        cutoff_date = (date.today() - timedelta(days=14)).isoformat()
        recent_completed = [
            row for row in logs 
            if row.get("date", "") >= cutoff_date and row.get("completed") == "1"
        ]

        day_counts: Dict[str, int] = {}
        for row in recent_completed:
            d = row["date"]
            day_counts[d] = day_counts.get(d, 0) + 1

        return sum(min(50, count * 10) for count in day_counts.values())

    def get_leaderboard(
        self,
        current_user_id: str,
        board_type: str = "global",
        timeframe: str = "momentum"
    ) -> List[Dict[str, Any]]:
        all_users = self.db.get_all_users()
        if not all_users:
            return []

        if board_type == "friends":
            mutual_ids = self.get_mutual_friends(current_user_id)
            target_ids = mutual_ids.union({current_user_id})
            scoped_users = {uid: all_users[uid] for uid in target_ids if uid in all_users}
        else:
            scoped_users = all_users

        ranked_list = []
        for uid, udata in scoped_users.items():
            score = self.calculate_14day_momentum_points(uid) if timeframe == "momentum" else udata.get("all_time_points", 0)
            ranked_list.append({
                "user_id": uid,
                "display_name": udata.get("display_name", "Anonymous"),
                "email": udata.get("email", ""),
                "avatar": udata.get("avatar", "👤"),
                "score": score,
                "is_current_user": uid == current_user_id
            })

        ranked_list.sort(key=lambda item: item["score"], reverse=True)
        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        for idx, entry in enumerate(ranked_list, start=1):
            entry["rank"] = idx
            entry["badge"] = medals.get(idx, f"#{idx}")

        return ranked_list

    def create_duel(self, challenger_id: str, opponent_id: str, habit_name: str, duration_days: int = 7) -> Challenge:
        challenger = self.db.find_user_by_id(challenger_id)
        opponent = self.db.find_user_by_id(opponent_id)

        c_name = challenger.get("display_name") if challenger else "Challenger"
        o_name = opponent.get("display_name") if opponent else "Opponent"

        duel = Challenge(
            challenge_id=f"duel_{uuid.uuid4().hex[:8]}",
            challenger_id=challenger_id,
            challenger_name=c_name,
            opponent_id=opponent_id,
            opponent_name=o_name,
            habit_name=habit_name,
            duration_days=duration_days,
            status="pending"
        )
        self.db.save_challenge(duel.to_dict())
        return duel

    def get_user_duels(self, user_id: str) -> List[Dict[str, Any]]:
        return [c for c in self.db.get_all_challenges().values() if c.get("challenger_id") == user_id or c.get("opponent_id") == user_id]

    def sync_duel_progress(self, challenge_id: str) -> Challenge:
        challenges = self.db.get_all_challenges()
        duel = Challenge.from_dict(challenges[challenge_id])

        if duel.status != "active":
            return duel

        c_logs = self.db.get_user_logs(duel.challenger_id)
        o_logs = self.db.get_user_logs(duel.opponent_id)

        c_score = sum(1 for row in c_logs if duel.start_date <= row.get("date", "") <= duel.end_date and row.get("completed") == "1")
        o_score = sum(1 for row in o_logs if duel.start_date <= row.get("date", "") <= duel.end_date and row.get("completed") == "1")
        duel.update_scores(c_score, o_score)

        if duel.status == "completed" and duel.winner_id and duel.winner_id != "TIE":
            winner_data = self.db.find_user_by_id(duel.winner_id)
            if winner_data:
                winner = User.from_dict(winner_data)
                winner.add_points(100)
                winner.add_badge(f"Duel Champion ({duel.habit_name})")
                self.db.save_user(winner.to_dict())

        self.db.save_challenge(duel.to_dict())
        return duel