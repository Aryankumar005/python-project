from datetime import datetime
from habit_tracker.engine.analytics import HabitSynergyAnalyzer
from habit_tracker.storage.db import DataManager


class DiagnosticReportGenerator:
    def __init__(self, db: DataManager, user_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.analyzer = HabitSynergyAnalyzer(db, user_id)

    def generate_markdown_report(self) -> str:
        user_data = self.db.find_user_by_id(self.user_id) or {}
        user_name = user_data.get("display_name", "User")
        user_email = user_data.get("email", "N/A")

        streaks_health = self.analyzer.compute_habit_streaks_and_health()
        keystones = self.analyzer.detect_keystone_habits()
        lag_matrix = self.analyzer.calculate_lag1_predictive_correlation()

        lines = [
            f"# Behavioral Diagnostic & Habit Synergy Report",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Account:** {user_name} ({user_email})",
            f"**Engine:** Habit Synergy Analyzer (CS213 Course Project)",
            "", "---", "## 1. Executive Summary & Habit Health Scorecard", "",
            "| Habit Name | Category | Current Streak | 7-Day Consistency | 30-Day Consistency | Health Score | Status |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |"
        ]

        for h_id, metrics in streaks_health.items():
            lines.append(
                f"| **{metrics['name']}** | {metrics['category']} | "
                f"{metrics['current_streak']} days | {metrics['rate_7d']}% | "
                f"{metrics['rate_30d']}% | **{metrics['health_score']}/100** | {metrics['status']} |"
            )

        lines.extend(["", "---", "## 2. Keystone Habit Discovery (Catalytic Behaviors)", ""])
        if keystones:
            top = keystones[0]
            lines.append(f"> 🏆 **Primary Keystone Habit Identified:** `{top['habit']}`")
            lines.append(f"> Average cross-routine synergy factor: **+{top['average_synergy']}**.")
            lines.append(f"> Boosts `{top['top_impact_target']}` completion by **+{top['prob_boost_percent']}%** on subsequent days.\n")
            lines.append("### All Detected Domino Impacts:")
            for item in keystones:
                marker = "⭐ Keystone" if item["is_keystone"] else "Impact"
                lines.append(f"* **[{marker}] {item['habit']}:** Next-day correlation with `{item['top_impact_target']}` is **{item['correlation']}** (Boost: +{item['prob_boost_percent']}%).")
        else:
            lines.append("_Insufficient data to identify keystone habits._")

        lines.extend(["", "---", "## 3. Next-Day Predictive Behavioral Matrix (Lag-1 Analysis)", ""])
        if not lag_matrix.empty:
            headers = ["Day t / Day t+1"] + list(lag_matrix.columns)
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join([":---"] * len(headers)) + " |")
            for idx, row in lag_matrix.iterrows():
                row_vals = [f"**{idx}**"] + [f"{val:.2f}" for val in row]
                lines.append("| " + " | ".join(row_vals) + " |")

        lines.extend([
            "", "---", "## 4. Actionable Behavioral Recommendations", "",
            "1. **Defend Your Keystone:** Protect the baseline habits that catalyze your day.",
            "2. **Utilize Habit Stacking:** Anchor dependent habits directly after habits with high same-day correlation.",
            "3. **Protect Against Cascading Breaks:** Leverage weekly streak freezes so a missed day does not destroy momentum."
        ])

        return "\n".join(lines)