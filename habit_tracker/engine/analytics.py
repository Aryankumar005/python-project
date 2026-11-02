import io
import base64
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from habit_tracker.storage.db import DataManager


class HabitSynergyAnalyzer:
    def __init__(self, db: DataManager, user_id: str) -> None:
        self.db = db
        self.user_id = user_id

    def build_time_series_dataframe(self) -> pd.DataFrame:
        user_logs = self.db.get_user_logs(self.user_id)
        if not user_logs:
            return pd.DataFrame()

        all_habits = {h["habit_id"]: h["name"] for h in self.db.get_user_habits(self.user_id)}
        records = []
        for row in user_logs:
            h_id = row.get("habit_id")
            if h_id in all_habits:
                records.append({
                    "date": pd.to_datetime(row["date"]),
                    "habit_name": all_habits[h_id],
                    "completed": int(row.get("completed", 0)),
                    "value": float(row.get("value", 0.0))
                })

        if not records:
            return pd.DataFrame()

        raw_df = pd.DataFrame(records)
        pivot_df = raw_df.pivot_table(
            index="date",
            columns="habit_name",
            values="completed",
            aggfunc="max"
        ).fillna(0).sort_index()

        if len(pivot_df) > 1:
            full_date_range = pd.date_range(start=pivot_df.index.min(), end=pivot_df.index.max(), freq="D")
            pivot_df = pivot_df.reindex(full_date_range, fill_value=0)

        return pivot_df

    def calculate_same_day_correlation(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if df is None:
            df = self.build_time_series_dataframe()
        if df.empty or len(df.columns) < 2 or len(df) < 3:
            return pd.DataFrame()
        return df.corr(method="pearson").fillna(0.0).round(2)

    def calculate_lag1_predictive_correlation(self, df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if df is None:
            df = self.build_time_series_dataframe()
        if df.empty or len(df.columns) < 2 or len(df) < 4:
            return pd.DataFrame()

        df_today = df.iloc[:-1].reset_index(drop=True)
        df_tomorrow = df.iloc[1:].reset_index(drop=True)

        habits = df.columns
        lag_matrix = pd.DataFrame(index=habits, columns=habits, dtype=float)

        for h_today in habits:
            for h_next in habits:
                series_a = df_today[h_today]
                series_b = df_tomorrow[h_next]
                if series_a.std() == 0 or series_b.std() == 0:
                    corr_val = 0.0
                else:
                    corr_val = float(np.corrcoef(series_a, series_b)[0, 1])
                lag_matrix.loc[h_today, h_next] = round(corr_val if not np.isnan(corr_val) else 0.0, 2)

        return lag_matrix

    def detect_keystone_habits(self) -> List[Dict[str, Any]]:
        df = self.build_time_series_dataframe()
        if df.empty or len(df.columns) < 2 or len(df) < 5:
            return []

        lag_matrix = self.calculate_lag1_predictive_correlation(df)
        if lag_matrix.empty:
            return []

        insights = []
        habits = list(df.columns)

        for predictor in habits:
            other_habits = [h for h in habits if h != predictor]
            if not other_habits:
                continue

            scores = [lag_matrix.loc[predictor, target] for target in other_habits]
            avg_synergy = float(np.mean(scores))
            best_target = max(other_habits, key=lambda t: lag_matrix.loc[predictor, t])
            best_corr = float(lag_matrix.loc[predictor, best_target])

            pred_completed_days = df[df[predictor] == 1].index
            next_days = [d + timedelta(days=1) for d in pred_completed_days if d + timedelta(days=1) in df.index]

            if next_days:
                prob_with_predictor = float(df.loc[next_days, best_target].mean()) * 100
                baseline_prob = float(df[best_target].mean()) * 100
                prob_boost = round(prob_with_predictor - baseline_prob, 1)
            else:
                prob_with_predictor, prob_boost = 0.0, 0.0

            insights.append({
                "habit": predictor,
                "average_synergy": round(avg_synergy, 2),
                "top_impact_target": best_target,
                "correlation": best_corr,
                "prob_boost_percent": prob_boost,
                "is_keystone": avg_synergy > 0.25 or best_corr > 0.40
            })

        insights.sort(key=lambda x: x["average_synergy"], reverse=True)
        return insights

    def compute_habit_streaks_and_health(self) -> Dict[str, Dict[str, Any]]:
        habits = self.db.get_user_habits(self.user_id)
        if not habits:
            return {}

        df = self.build_time_series_dataframe()
        results = {}

        for h in habits:
            h_id = h["habit_id"]
            name = h["name"]

            if df.empty or name not in df.columns:
                results[h_id] = {
                    "name": name, "category": h.get("category", "General"),
                    "current_streak": 0, "longest_streak": 0,
                    "rate_7d": 0.0, "rate_30d": 0.0,
                    "health_score": 10, "status": "At Risk"
                }
                continue

            series = df[name].sort_index()
            last_7_days = series.iloc[-7:] if len(series) >= 7 else series
            last_30_days = series.iloc[-30:] if len(series) >= 30 else series

            rate_7d = round(float(last_7_days.mean()) * 100, 1)
            rate_30d = round(float(last_30_days.mean()) * 100, 1)

            values = series.tolist()
            current_streak, longest_streak, temp_streak = 0, 0, 0
            grace_used = False

            for val in values:
                if val == 1:
                    temp_streak += 1
                    longest_streak = max(longest_streak, temp_streak)
                else:
                    temp_streak = 0

            reversed_vals = list(reversed(values))
            for i, val in enumerate(reversed_vals):
                if val == 1:
                    current_streak += 1
                elif not grace_used and i > 0 and i < len(reversed_vals) - 1 and reversed_vals[i + 1] == 1:
                    grace_used = True
                else:
                    break

            streak_factor = min(100.0, (current_streak / 21.0) * 100.0)
            health_score = int(round((0.40 * rate_30d) + (0.30 * streak_factor) + (0.30 * rate_7d)))
            health_score = max(0, min(100, health_score))

            status = "Thriving" if health_score >= 80 else "Consistent" if health_score >= 50 else "At Risk"

            results[h_id] = {
                "name": name, "category": h.get("category", "General"),
                "current_streak": current_streak, "longest_streak": longest_streak,
                "rate_7d": rate_7d, "rate_30d": rate_30d,
                "health_score": health_score, "status": status
            }

        return results

    def generate_heatmap_figure(self, matrix_type: str = "same_day") -> Optional[str]:
        df = self.build_time_series_dataframe()
        if df.empty or len(df.columns) < 2:
            return None

        if matrix_type == "lag1":
            matrix = self.calculate_lag1_predictive_correlation(df)
            title = "Habit Synergy: Next-Day Impact Matrix (Lag-1 Analysis)"
        else:
            matrix = self.calculate_same_day_correlation(df)
            title = "Habit Synergy: Same-Day Co-occurrence Matrix"

        if matrix.empty:
            return None

        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(matrix, annot=True, fmt=".2f", cmap="vlag", vmin=-1.0, vmax=1.0, center=0.0, square=True, ax=ax)
        ax.set_title(title, fontsize=12, pad=15, fontweight="bold")
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.yticks(rotation=0, fontsize=10)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=150)
        plt.close(fig)
        buf.seek(0)
        encoded = base64.b64encode(buf.read()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"