"""
FastAPI Web Application Controller.
Coordinates Authentication, Habit Management, Statistical Synergy Engine, 
and Gamification Leaderboards over HTTP.
"""

import os
from datetime import datetime, date
from typing import Dict, Any, Optional

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from pydantic import BaseModel

from habit_tracker.storage.db import DataManager
from habit_tracker.storage.exceptions import HabitTrackerException
from habit_tracker.engine.auth import AuthService
from habit_tracker.engine.analytics import HabitSynergyAnalyzer
from habit_tracker.engine.social import SocialEngine
from habit_tracker.engine.seeder import DemoDataSeeder
from habit_tracker.engine.reporter import DiagnosticReportGenerator
from habit_tracker.models.habit import BinaryHabit, NumericHabit

app = FastAPI(title="Habit Synergy & Gamification Platform", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
INDEX_HTML = os.path.join(TEMPLATES_DIR, "index.html")

db = DataManager()
auth_service = AuthService(
    db,
    smtp_sender="cs25b1008@iiitr.ac.in",
    smtp_password="zucs ficm ngjs defz"
)
social_engine = SocialEngine(db)

# Auto-seed 15 students if database is currently blank
if len(db.get_all_users()) == 0:
    DemoDataSeeder(db).seed_complete_demo_environment()


# ==================== Web Route Handlers ====================

@app.get("/")
async def serve_index():
    """Serve single-page web dashboard interface directly."""
    if not os.path.exists(INDEX_HTML):
        raise HTTPException(status_code=404, detail="index.html not found in templates folder.")
    return FileResponse(INDEX_HTML)


@app.get("/api/users")
async def api_get_all_users():
    """Retrieve roster of registered students for quick demo switching."""
    if len(db.get_all_users()) == 0:
        DemoDataSeeder(db).seed_complete_demo_environment()

    users_dict = db.get_all_users()
    users_list = [
        {
            "user_id": u["user_id"],
            "email": u["email"],
            "display_name": u.get("display_name", "Student"),
            "avatar": u.get("avatar", "👤"),
            "all_time_points": u.get("all_time_points", 0)
        }
        for u in users_dict.values()
    ]
    users_list.sort(key=lambda x: (x["user_id"] != "usr_aryan", x["display_name"]))
    return {"users": users_list}


# ==================== Authentication API ====================

@app.post("/api/auth/register")
async def api_register(request: Request):
    """Direct JSON parsing endpoint - 100% immune to 422 Unprocessable Content."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    email = str(body.get("email", "")).strip()
    password = str(body.get("password", "")).strip()
    display_name = str(body.get("display_name", "") or body.get("name", "")).strip()

    if not email:
        raise HTTPException(status_code=400, detail="Email address is required.")
    if not password:
        raise HTTPException(status_code=400, detail="Password is required.")

    try:
        user = auth_service.register_user(email, password, display_name)
        return {"status": "ok", "user": user.to_dict()}
    except HabitTrackerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
async def api_login(request: Request):
    """Direct JSON parsing login endpoint."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    email = str(body.get("email", "")).strip()
    password = str(body.get("password", "")).strip()

    if not email or not password:
        raise HTTPException(status_code=400, detail="Please enter both email and password.")

    if len(db.get_all_users()) == 0:
        DemoDataSeeder(db).seed_complete_demo_environment()

    try:
        user = auth_service.authenticate_user(email, password)
        return {"status": "ok", "user": user.to_dict()}
    except HabitTrackerException as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.post("/api/auth/send-otp")
async def api_send_otp(request: Request):
    """Dispatches 4-digit verification code to user."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    email = str(body.get("email", "")).strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email address is required.")

    try:
        auth_service.generate_and_send_otp(email)
        return {"status": "ok", "message": "Verification code dispatched."}
    except HabitTrackerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/reset-password")
async def api_reset_password(request: Request):
    """Verifies 4-digit OTP and updates password."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body.")

    email = str(body.get("email", "")).strip()
    otp = str(body.get("otp", "")).strip()
    new_password = str(body.get("new_password", "")).strip()

    if not email or not otp or not new_password:
        raise HTTPException(status_code=400, detail="All fields are required.")

    try:
        auth_service.verify_otp_and_reset_password(email, otp, new_password)
        return {"status": "ok", "message": "Password reset successfully."}
    except HabitTrackerException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Habit Management API ====================

@app.get("/api/habits")
async def api_get_habits(user_id: str, date: str):
    habits = db.get_user_habits(user_id)
    logs = db.get_user_logs(user_id)
    
    day_logs = {
        row["habit_id"]: {
            "value": float(row["value"]),
            "completed": row["completed"] == "1"
        }
        for row in logs if row.get("date") == date
    }

    analyzer = HabitSynergyAnalyzer(db, user_id)
    streaks_health = analyzer.compute_habit_streaks_and_health()

    return {
        "habits": habits,
        "logs": day_logs,
        "streaks_health": streaks_health
    }


@app.post("/api/habits")
async def api_create_habit(request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    name = body.get("name")
    category = body.get("category", "General")
    htype = body.get("type", "binary")
    target_value = float(body.get("target_value", 0.0))
    unit = body.get("unit", "")
    operator = body.get("operator", ">=")
    is_public = bool(body.get("is_public", True))

    habit_id = f"hab_{os.urandom(4).hex()}"
    if htype == "numeric":
        habit = NumericHabit(
            habit_id=habit_id,
            user_id=user_id,
            name=name,
            target_value=target_value,
            unit=unit,
            operator=operator,
            category=category,
            is_public=is_public
        )
    else:
        habit = BinaryHabit(
            habit_id=habit_id,
            user_id=user_id,
            name=name,
            category=category,
            is_public=is_public
        )

    db.save_habit(habit.to_dict())
    return {"status": "ok", "habit": habit.to_dict()}


@app.post("/api/habits/log")
async def api_log_habit(request: Request):
    body = await request.json()
    user_id = body.get("user_id")
    habit_id = body.get("habit_id")
    date_str = body.get("date")
    val = float(body.get("value", 0.0))

    all_habits = {h["habit_id"]: h for h in db.get_user_habits(user_id)}
    if habit_id not in all_habits:
        raise HTTPException(status_code=404, detail="Habit not found")

    h_data = all_habits[habit_id]
    completed = False

    if h_data.get("type") == "numeric":
        target = float(h_data.get("target_value", 0.0))
        op = h_data.get("operator", ">=")
        completed = (val >= target) if op == ">=" else (val <= target)
    else:
        completed = val > 0.0

    db.log_activity(date_str, user_id, habit_id, val, completed)
    return {"status": "ok", "completed": completed}


# ==================== Synergy & Analytics API ====================

@app.get("/api/synergy")
async def api_get_synergy(user_id: str):
    analyzer = HabitSynergyAnalyzer(db, user_id)
    keystones = analyzer.detect_keystone_habits()
    lag1_img = analyzer.generate_heatmap_figure(matrix_type="lag1")
    sameday_img = analyzer.generate_heatmap_figure(matrix_type="same_day")

    return {
        "keystones": keystones,
        "lag1_heatmap": lag1_img,
        "sameday_heatmap": sameday_img
    }


# ==================== Social & Gamification API ====================

@app.get("/api/leaderboard")
async def api_get_leaderboard(user_id: str, scope: str = "global", timeframe: str = "momentum"):
    members = social_engine.get_leaderboard(user_id, board_type=scope, timeframe=timeframe)
    return {"members": members}


@app.get("/api/duels")
async def api_get_duels(user_id: str):
    duels = social_engine.get_user_duels(user_id)
    synced = [social_engine.sync_duel_progress(d["challenge_id"]).to_dict() for d in duels]
    return {"duels": synced}


@app.post("/api/duels")
async def api_create_duel(request: Request):
    body = await request.json()
    duel = social_engine.create_duel(
        challenger_id=body.get("challenger_id"),
        opponent_id=body.get("opponent_id"),
        habit_name=body.get("habit_name"),
        duration_days=int(body.get("duration_days", 7))
    )
    return {"status": "ok", "duel": duel.to_dict()}


# ==================== Diagnostic Report API ====================

@app.get("/api/report")
async def api_get_report(user_id: str):
    reporter = DiagnosticReportGenerator(db, user_id)
    md = reporter.generate_markdown_report()
    return {"report_content": md}


@app.get("/api/report/download")
async def api_download_report(user_id: str = "usr_aryan"):
    reporter = DiagnosticReportGenerator(db, user_id)
    md = reporter.generate_markdown_report()
    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=habit_diagnostic_report_{user_id}.md"}
    )


# ==================== Seed Demo API ====================

@app.post("/api/seed-demo")
async def api_seed_demo():
    seeder = DemoDataSeeder(db)
    result = seeder.seed_complete_demo_environment()
    return {"status": "ok", "details": result}