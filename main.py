"""
Daily Habit Tracker & Behavioral Synergy Platform - Main Entry Point.
Built for CS213 Python Course Project.
"""

import sys
import uvicorn
from habit_tracker.storage.db import DataManager
from habit_tracker.engine.seeder import DemoDataSeeder


def main():
    print("=" * 70)
    print("🔥 Habit Synergy & Gamification Platform | CS213 Course Project")
    print("=" * 70)

    if "--demo" in sys.argv:
        print("\n🌱 Generating multi-user behavioral dataset with seeded correlations...")
        db = DataManager()
        seeder = DemoDataSeeder(db)
        summary = seeder.seed_complete_demo_environment()
        days = summary.get("history_days") or summary.get("days_seeded", 25)
        users = summary.get("users_seeded", 15)
        print(f"✓ Seeded {days} days of data across {users} student accounts.")
        print(f"✓ Primary user: {summary.get('primary_user', 'cs25b1008@iiitr.ac.in')}")
        print("✓ Ready for evaluation.\n")

    print("\n🚀 Starting Web Application Server on http://localhost:8000 ...")
    print("👉 Open your browser to http://localhost:8000 to view the dashboard.")
    print("Press CTRL+C to terminate the server.\n")

    uvicorn.run("habit_tracker.web.app:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()