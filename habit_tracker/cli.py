"""
Interactive Rich Terminal Interface (CLI Mode).
Satisfies Course Requirement #1 (Control Flow) and #3 (Data Structures).
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from habit_tracker.storage.db import DataManager
from habit_tracker.engine.analytics import HabitSynergyAnalyzer
from habit_tracker.engine.social import SocialEngine
from habit_tracker.engine.seeder import DemoDataSeeder

console = Console()
db = DataManager()
social = SocialEngine(db)


def display_banner():
    console.print(
        Panel.fit(
            "[bold cyan]🔥 Habit Synergy & Gamification Platform[/bold cyan]\n"
            "[yellow]CS213-Python Course Project[/yellow] | Terminal Interface",
            border_style="cyan"
        )
    )


def show_habits_table(user_id: str):
    analyzer = HabitSynergyAnalyzer(db, user_id)
    streaks = analyzer.compute_habit_streaks_and_health()

    table = Table(title="Daily Habits & Health Scorecard", border_style="blue")
    table.add_column("Habit", style="white", no_wrap=True)
    table.add_column("Category", style="cyan")
    table.add_column("Streak", style="green")
    table.add_column("7D Rate", style="magenta")
    table.add_column("30D Rate", style="yellow")
    table.add_column("Health Score", style="bold green")
    table.add_column("Status", style="bold")

    for h_id, m in streaks.items():
        status_color = "green" if m["status"] == "Thriving" else "yellow" if m["status"] == "Consistent" else "red"
        table.add_row(
            m["name"],
            m["category"],
            f"{m['current_streak']} days",
            f"{m['rate_7d']}%",
            f"{m['rate_30d']}%",
            f"{m['health_score']}/100",
            f"[{status_color}]{m['status']}[/{status_color}]"
        )

    console.print(table)


def show_leaderboard(user_id: str):
    members = social.get_leaderboard(user_id, board_type="friends", timeframe="momentum")

    table = Table(title="Friends Circle Leaderboard (14-Day Momentum)", border_style="yellow")
    table.add_column("Rank", style="bold yellow")
    table.add_column("Member", style="white")
    table.add_column("14-Day Points", style="bold green")

    for m in members:
        is_you = " [bold cyan](You)[/bold cyan]" if m["is_current_user"] else ""
        table.add_row(m["badge"], f"{m['avatar']} {m['display_name']}{is_you}", f"{m['score']} pts")

    console.print(table)


def run_cli():
    display_banner()
    user_id = "usr_aryan"

    while True:
        console.print("\n[bold]Main Menu:[/bold]")
        console.print("1. View Daily Habits & Health Scorecard")
        console.print("2. View Friends Leaderboard")
        console.print("3. View Keystone Habits & Synergy Insights")
        console.print("4. Seed Demo Data (15 Students)")
        console.print("5. Exit")

        choice = Prompt.ask("Select an option", choices=["1", "2", "3", "4", "5"], default="1")

        if choice == "1":
            show_habits_table(user_id)
        elif choice == "2":
            show_leaderboard(user_id)
        elif choice == "3":
            analyzer = HabitSynergyAnalyzer(db, user_id)
            keystones = analyzer.detect_keystone_habits()
            if keystones:
                top = keystones[0]
                console.print(
                    Panel(
                        f"[bold green]🏆 Primary Keystone Habit:[/bold green] {top['habit']}\n"
                        f"Completing this increases probability of completing [bold]{top['top_impact_target']}[/bold] by [bold cyan]+{top['prob_boost_percent']}%[/bold cyan] on subsequent days.",
                        title="Statistical Discovery",
                        border_style="green"
                    )
                )
            else:
                console.print("[yellow]No logs found. Run option 4 first.[/yellow]")
        elif choice == "4":
            seeder = DemoDataSeeder(db)
            seeder.seed_complete_demo_environment()
            console.print("[bold green]✓ 15 students & 25 days of data seeded![/bold green]")
        elif choice == "5":
            console.print("[cyan]Goodbye![/cyan]")
            break


if __name__ == "__main__":
    run_cli()