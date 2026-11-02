"""
Comprehensive Unit Test Suite for CS213 Habit Tracker.
Tests Models, File Storage, SHA-256 Hashing, Synergy Analytics, and Social Sets.
"""

import os
import shutil
import unittest
from datetime import date, timedelta

from habit_tracker.storage.db import DataManager
from habit_tracker.models.habit import BinaryHabit, NumericHabit, Habit
from habit_tracker.models.user import User
from habit_tracker.engine.auth import AuthService
from habit_tracker.engine.analytics import HabitSynergyAnalyzer
from habit_tracker.engine.social import SocialEngine
from habit_tracker.storage.exceptions import InvalidEmailError, UserAlreadyExistsError


class TestHabitTrackerCore(unittest.TestCase):

    def setUp(self):
        self.test_data_dir = "test_data_sandbox"
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)
        self.db = DataManager(data_dir=self.test_data_dir)
        self.auth = AuthService(self.db)
        self.social = SocialEngine(self.db)

    def tearDown(self):
        if os.path.exists(self.test_data_dir):
            shutil.rmtree(self.test_data_dir)

    def test_habit_oop_polymorphism(self):
        b_habit = BinaryHabit("h1", "u1", "Morning Jog", "Fitness")
        self.assertTrue(b_habit.evaluate_completion(True))
        self.assertTrue(b_habit.evaluate_completion(1.0))
        self.assertFalse(b_habit.evaluate_completion(0.0))

        n_habit = NumericHabit("h2", "u1", "Sleep Duration", 7.5, "hours", ">=", "Health")
        self.assertTrue(n_habit.evaluate_completion(8.0))
        self.assertFalse(n_habit.evaluate_completion(6.5))

        serialized = n_habit.to_dict()
        reconstructed = Habit.from_dict(serialized)
        self.assertIsInstance(reconstructed, NumericHabit)
        self.assertEqual(reconstructed.name, "Sleep Duration")
        self.assertEqual(reconstructed.target_value, 7.5)

    def test_user_salted_sha256_security(self):
        pw_hash, salt = User.hash_password("mySecretPass123")
        user = User("u_test", "student@iiitr.ac.in", pw_hash, salt, "Student")

        self.assertTrue(user.verify_password("mySecretPass123"))
        self.assertFalse(user.verify_password("wrongPassword"))

        with self.assertRaises(InvalidEmailError):
            User.validate_and_normalize_email("9876543210")

    def test_auth_registration_and_duplicate_guard(self):
        user = self.auth.register_user("cs25b1008@iiitr.ac.in", "pass1234", "Aryan Kumar")
        self.assertEqual(user.email, "cs25b1008@iiitr.ac.in")

        with self.assertRaises(UserAlreadyExistsError):
            self.auth.register_user("cs25b1008@iiitr.ac.in", "anotherPass")

        logged_in = self.auth.authenticate_user("cs25b1008@iiitr.ac.in", "pass1234")
        self.assertEqual(logged_in.user_id, user.user_id)

    def test_csv_time_series_logging(self):
        self.db.log_activity("2026-11-01", "u1", "h1", 1.0, True)
        self.db.log_activity("2026-11-02", "u1", "h1", 0.0, False)

        logs = self.db.get_user_logs("u1")
        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[0]["completed"], "1")
        self.assertEqual(logs[1]["completed"], "0")

    def test_social_set_operations_and_leaderboard(self):
        u1 = self.auth.register_user("u1@iiitr.ac.in", "pass1234", "User 1")
        u2 = self.auth.register_user("u2@iiitr.ac.in", "pass1234", "User 2")
        u3 = self.auth.register_user("u3@iiitr.ac.in", "pass1234", "User 3")

        self.social.send_follow_request(u1.user_id, u2.user_id)
        self.social.send_follow_request(u2.user_id, u1.user_id)
        self.social.send_follow_request(u1.user_id, u3.user_id)

        mutuals_of_u1 = self.social.get_mutual_friends(u1.user_id)
        self.assertIn(u2.user_id, mutuals_of_u1)
        self.assertNotIn(u3.user_id, mutuals_of_u1)

        today = date.today().isoformat()
        self.db.log_activity(today, u2.user_id, "h_study", 1.0, True)

        leaderboard = self.social.get_leaderboard(u1.user_id, board_type="friends", timeframe="momentum")
        self.assertTrue(len(leaderboard) >= 2)
        self.assertEqual(leaderboard[0]["user_id"], u2.user_id)
        self.assertEqual(leaderboard[0]["badge"], "🥇")

    def test_synergy_analyzer_pandas(self):
        u = self.auth.register_user("analyst@iiitr.ac.in", "pass1234", "Analyst")
        h_sleep = NumericHabit("h_sleep", u.user_id, "Sleep", 8.0, "hrs")
        h_study = BinaryHabit("h_study", u.user_id, "Study", "Academics")
        self.db.save_habit(h_sleep.to_dict())
        self.db.save_habit(h_study.to_dict())

        start = date.today() - timedelta(days=10)
        for i in range(10):
            d = (start + timedelta(days=i)).isoformat()
            did = 1.0 if i % 2 == 0 else 0.0
            self.db.log_activity(d, u.user_id, "h_sleep", 8.0 if did else 6.0, bool(did))
            self.db.log_activity(d, u.user_id, "h_study", did, bool(did))

        analyzer = HabitSynergyAnalyzer(self.db, u.user_id)
        df = analyzer.build_time_series_dataframe()
        self.assertFalse(df.empty)
        corr = analyzer.calculate_same_day_correlation(df)
        self.assertFalse(corr.empty)


if __name__ == "__main__":
    unittest.main()