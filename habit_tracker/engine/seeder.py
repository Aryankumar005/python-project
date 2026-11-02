import random
from datetime import date, timedelta
from typing import Dict, Any

from habit_tracker.storage.db import DataManager
from habit_tracker.models.user import User
from habit_tracker.models.habit import BinaryHabit, NumericHabit


class DemoDataSeeder:
    def __init__(self, db: DataManager) -> None:
        self.db = db

    def seed_complete_demo_environment(self) -> Dict[str, Any]:
        random.seed(42)

        students_roster = [
            ("usr_aryan", "cs25b1008@iiitr.ac.in", "Aryan Kumar", "🚀", 580, ["Early Adopter", "Python Pioneer", "7-Day Streak Master"]),
            ("usr_rahul", "rahul.s@iiitr.ac.in", "Rahul Sharma", "⚡", 620, ["Consistent Achiever", "Early Bird"]),
            ("usr_sneha", "sneha.k@iiitr.ac.in", "Sneha Kapoor", "🌟", 540, ["Study Marathoner"]),
            ("usr_amit", "amit.p@iiitr.ac.in", "Amit Patel", "🎯", 410, ["Fitness Freak"]),
            ("usr_priya", "priya.v@iiitr.ac.in", "Priya Verma", "🔥", 490, ["Duel Champion"]),
            ("usr_rohan", "rohan.g@iiitr.ac.in", "Rohan Gupta", "💻", 460, ["Code Monk"]),
            ("usr_ananya", "ananya.i@iiitr.ac.in", "Ananya Iyer", "📚", 510, ["Bookworm"]),
            ("usr_vikram", "vikram.s@iiitr.ac.in", "Vikram Singh", "🏋️", 430, ["Gym Beast"]),
            ("usr_pooja", "pooja.n@iiitr.ac.in", "Pooja Nair", "🧘", 380, ["Zen Master"]),
            ("usr_karthik", "karthik.r@iiitr.ac.in", "Karthik Reddy", "🌙", 350, ["Night Owl"]),
            ("usr_neha", "neha.j@iiitr.ac.in", "Neha Joshi", "🎨", 420, ["Creative Thinker"]),
            ("usr_aditya", "aditya.m@iiitr.ac.in", "Aditya Mehra", "⚽", 390, ["Sports Captain"]),
            ("usr_divya", "divya.r@iiitr.ac.in", "Divya Rao", "🌿", 470, ["Hydration Hero"]),
            ("usr_varun", "varun.m@iiitr.ac.in", "Varun Malhotra", "🧠", 340, ["Algorithm Ace"]),
            ("usr_shreya", "shreya.s@iiitr.ac.in", "Shreya Sen", "⭐", 500, ["Top Performer"]),
        ]

        for uid, uemail, uname, uavatar, upts, ubadges in students_roster:
            pw_hash, salt = User.hash_password("iiit1234")
            user = User(user_id=uid, email=uemail, password_hash=pw_hash, salt=salt, display_name=uname, avatar=uavatar, all_time_points=upts, badges=ubadges)
            self.db.save_user(user.to_dict())

        graph = self.db.get_social_graph()
        mutual_with_aryan = ["usr_rahul", "usr_sneha", "usr_priya", "usr_rohan", "usr_ananya", "usr_vikram", "usr_divya", "usr_shreya"]
        graph["usr_aryan"] = {"following": mutual_with_aryan + ["usr_amit", "usr_pooja"], "followers": mutual_with_aryan, "pending_incoming": ["usr_aditya"]}

        all_uids = [s[0] for s in students_roster]
        for uid in all_uids:
            if uid != "usr_aryan":
                friends_subset = random.sample([u for u in all_uids if u != uid], 4)
                if "usr_aryan" not in friends_subset and uid in mutual_with_aryan:
                    friends_subset.append("usr_aryan")
                graph[uid] = {"following": friends_subset, "followers": [f for f in all_uids if f != uid and random.random() < 0.3], "pending_incoming": []}
        self.db.save_social_graph(graph)

        core_habits_specs = [
            ("hab_sleep", "Sleep Duration", "Health", "numeric", 7.5, "hours", ">="),
            ("hab_study", "Python Study Session", "Academics", "binary", 0, "", ">="),
            ("hab_run", "Morning Jog", "Fitness", "binary", 0, "", ">="),
            ("hab_water", "Hydration", "Health", "numeric", 3.0, "liters", ">="),
            ("hab_screen", "Screen Time Limit", "Mindset", "numeric", 2.5, "hours", "<=")
        ]

        for hid, hname, hcat, htype, htarget, hunit, hop in core_habits_specs:
            for uid, _, _, _, _, _ in students_roster:
                user_hid = f"{hid}_{uid}"
                h = NumericHabit(user_hid, uid, hname, float(htarget), hunit, hop, hcat, True) if htype == "numeric" else BinaryHabit(user_hid, uid, hname, hcat, True)
                self.db.save_habit(h.to_dict())

        history_days = 25
        start_date = date.today() - timedelta(days=history_days)
        all_logs = []

        for uid, _, _, _, _, _ in students_roster:
            prev_good_sleep = True
            is_high_performer = uid in ["usr_aryan", "usr_rahul", "usr_sneha", "usr_shreya", "usr_ananya"]

            for day_offset in range(history_days + 1):
                curr_date = (start_date + timedelta(days=day_offset)).isoformat()
                good_sleep = random.random() < (0.75 if is_high_performer else 0.55)
                sleep_val = round(random.uniform(7.5, 9.0) if good_sleep else random.uniform(5.0, 7.2), 1)
                all_logs.append({"date": curr_date, "user_id": uid, "habit_id": f"hab_sleep_{uid}", "value": str(sleep_val), "completed": "1" if good_sleep else "0"})

                did_study = random.random() < (0.85 if prev_good_sleep else 0.35)
                all_logs.append({"date": curr_date, "user_id": uid, "habit_id": f"hab_study_{uid}", "value": "1.0" if did_study else "0.0", "completed": "1" if did_study else "0"})

                did_jog = random.random() < (0.70 if good_sleep else 0.30)
                all_logs.append({"date": curr_date, "user_id": uid, "habit_id": f"hab_run_{uid}", "value": "1.0" if did_jog else "0.0", "completed": "1" if did_jog else "0"})

                water_val = round(random.uniform(3.0, 3.8) if did_jog else random.uniform(1.8, 3.1), 1)
                all_logs.append({"date": curr_date, "user_id": uid, "habit_id": f"hab_water_{uid}", "value": str(water_val), "completed": "1" if water_val >= 3.0 else "0"})

                screen_val = round(random.uniform(1.2, 2.3) if did_study else random.uniform(2.8, 5.0), 1)
                all_logs.append({"date": curr_date, "user_id": uid, "habit_id": f"hab_screen_{uid}", "value": str(screen_val), "completed": "1" if screen_val <= 2.5 else "0"})

                prev_good_sleep = good_sleep

        self.db.write_all_logs(all_logs)

        duel = {
            "challenge_id": "duel_01", "challenger_id": "usr_rahul", "challenger_name": "Rahul Sharma",
            "opponent_id": "usr_aryan", "opponent_name": "Aryan Kumar", "habit_name": "Python Study Session",
            "duration_days": 7, "start_date": (date.today() - timedelta(days=3)).isoformat(),
            "end_date": (date.today() + timedelta(days=4)).isoformat(), "status": "active",
            "challenger_score": 3, "opponent_score": 3, "winner_id": None
        }
        self.db.save_challenge(duel)

        return {
            "users_seeded": len(students_roster),
            "days_seeded": history_days,
            "history_days": history_days,
            "total_log_records": len(all_logs),
            "primary_user": "cs25b1008@iiitr.ac.in"
        }