from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import chess
from flask import Flask, g, jsonify, redirect, render_template, request, session, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "training.db"
EXERCISES_PATH = BASE_DIR / "exercises.json"
SECRET_KEY = "dev-secret-change-me"

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY


@dataclass
class Exercise:
    id: str
    title: str
    fen: str
    solution: list[str]
    description: str = ""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_: Any) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def load_exercises() -> list[Exercise]:
    raw = json.loads(EXERCISES_PATH.read_text(encoding="utf-8"))
    return [Exercise(**item) for item in raw]


def get_exercise_by_id(exercise_id: str) -> Exercise | None:
    for exercise in load_exercises():
        if exercise.id == exercise_id:
            return exercise
    return None


def init_db() -> None:
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            exercise_id TEXT NOT NULL,
            started_at REAL NOT NULL,
            finished_at REAL,
            duration_seconds REAL,
            wrong_moves_count INTEGER NOT NULL DEFAULT 0,
            success INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS session_reports (
            session_id TEXT PRIMARY KEY,
            started_at REAL NOT NULL,
            finished_at REAL,
            duration_seconds REAL,
            total_exercises INTEGER NOT NULL,
            completed_exercises INTEGER NOT NULL DEFAULT 0,
            successful_exercises INTEGER NOT NULL DEFAULT 0,
            total_wrong_moves INTEGER NOT NULL DEFAULT 0
        );
        """
    )
    db.commit()
    db.close()


def reset_training_session() -> None:
    exercises = load_exercises()
    session_id = str(uuid4())
    started_at = time.time()

    session["training"] = {
        "session_id": session_id,
        "session_started_at": started_at,
        "exercise_index": 0,
        "current_attempt_started_at": started_at,
        "wrong_moves_count": 0,
        "completed": False,
    }

    db = get_db()
    db.execute(
        """
        INSERT OR REPLACE INTO session_reports (
            session_id, started_at, total_exercises, completed_exercises,
            successful_exercises, total_wrong_moves
        ) VALUES (?, ?, ?, 0, 0, 0)
        """,
        (session_id, started_at, len(exercises)),
    )
    db.commit()


def get_training_state() -> dict[str, Any]:
    if "training" not in session:
        reset_training_session()
    return session["training"]


def enrich_attempts_with_history(conn, attempts, current_session_id):
    """Add previous-history stats to current session attempts."""
    enriched = []

    for row in attempts:
        exercise_id = row["exercise_id"]

        history = conn.execute(
            """
            SELECT
                MIN(duration_seconds) AS best_previous_time,
                AVG(duration_seconds) AS avg_previous_time,
                COUNT(*) AS trained_before_count
            FROM attempts
            WHERE exercise_id = ?
              AND session_id <> ?
            """,
            (exercise_id, current_session_id),
        ).fetchone()

        item = dict(row)
        item["best_previous_time"] = history["best_previous_time"]
        item["avg_previous_time"] = history["avg_previous_time"]
        item["trained_before_count"] = history["trained_before_count"] or 0
        enriched.append(item)

    return enriched


def board_after_auto_replies(exercise: Exercise, user_progress: int) -> tuple[chess.Board, int, bool]:
    board = chess.Board(exercise.fen)
    total_moves = len(exercise.solution)
    replayed = 0
    while replayed < user_progress:
        board.push(chess.Move.from_uci(exercise.solution[replayed]))
        replayed += 1
        if replayed < total_moves:
            board.push(chess.Move.from_uci(exercise.solution[replayed]))
            replayed += 1
    is_finished = replayed >= total_moves
    return board, replayed, is_finished


def current_exercise_payload() -> dict[str, Any]:
    state = get_training_state()
    exercises = load_exercises()

    if state["exercise_index"] >= len(exercises):
        state["completed"] = True
        session.modified = True
        return {"completed": True, "report_url": url_for("report")}

    exercise = exercises[state["exercise_index"]]
    progress = state.get("progress", 0)
    board, replayed, is_finished = board_after_auto_replies(exercise, progress)
    state["progress"] = replayed
    session.modified = True

    if is_finished:
        finalize_current_exercise(success=True)
        return current_exercise_payload()

    return {
        "completed": False,
        "exercise": {
            "id": exercise.id,
            "title": exercise.title,
            "description": exercise.description,
            "fen": board.fen(),
            "move_number": board.fullmove_number,
            "turn": "white" if board.turn == chess.WHITE else "black",
            "index": state["exercise_index"] + 1,
            "total": len(exercises),
            "wrong_moves_count": state.get("wrong_moves_count", 0),
        },
    }


def finalize_current_exercise(success: bool) -> None:
    state = get_training_state()
    exercises = load_exercises()
    if state["exercise_index"] >= len(exercises):
        return

    exercise = exercises[state["exercise_index"]]
    now = time.time()
    duration = now - state["current_attempt_started_at"]
    wrong_moves = int(state.get("wrong_moves_count", 0))
    session_id = state["session_id"]

    db = get_db()
    db.execute(
        """
        INSERT INTO attempts (
            session_id, exercise_id, started_at, finished_at,
            duration_seconds, wrong_moves_count, success
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            exercise.id,
            state["current_attempt_started_at"],
            now,
            duration,
            wrong_moves,
            int(success),
        ),
    )

    db.execute(
        """
        UPDATE session_reports
        SET completed_exercises = completed_exercises + 1,
            successful_exercises = successful_exercises + ?,
            total_wrong_moves = total_wrong_moves + ?
        WHERE session_id = ?
        """,
        (int(success), wrong_moves, session_id),
    )
    db.commit()

    state["exercise_index"] += 1
    state["progress"] = 0
    state["wrong_moves_count"] = 0
    state["current_attempt_started_at"] = now
    session.modified = True


def finalize_session_report() -> sqlite3.Row:
    state = get_training_state()
    session_id = state["session_id"]
    now = time.time()
    db = get_db()
    db.execute(
        """
        UPDATE session_reports
        SET finished_at = ?, duration_seconds = ?
        WHERE session_id = ?
        """,
        (now, now - state["session_started_at"], session_id),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM session_reports WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    return row


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/start", methods=["POST"])
def start() -> Any:
    reset_training_session()
    return redirect(url_for("trainer"))

@app.route("/trainer")
def trainer() -> str:
    return render_template("trainer.html")


@app.route("/api/current")
def api_current() -> Any:
    return jsonify(current_exercise_payload())


@app.route("/api/move", methods=["POST"])
def api_move() -> Any:
    payload = request.get_json(force=True)
    user_move = payload.get("move", "").strip()

    state = get_training_state()
    exercises = load_exercises()

    if state["exercise_index"] >= len(exercises):
        return jsonify({"completed": True, "report_url": url_for("report")})

    exercise = exercises[state["exercise_index"]]
    progress = int(state.get("progress", 0))
    board, replayed, is_finished = board_after_auto_replies(exercise, progress)

    if is_finished:
        finalize_current_exercise(success=True)
        return jsonify(current_exercise_payload())

    try:
        move = chess.Move.from_uci(user_move)
    except ValueError:
        return jsonify({"status": "invalid_format", "message": "Formato inválido. Use UCI, ex.: e2e4"}), 400

    if move not in board.legal_moves:
        return jsonify({"status": "illegal", "message": "Lance ilegal nesta posição."}), 400

    expected = exercise.solution[replayed]
    if user_move != expected:
        state["wrong_moves_count"] = int(state.get("wrong_moves_count", 0)) + 1
        session.modified = True
        return jsonify(
            {
                "status": "wrong",
                "message": "Lance legal, mas não é o lance da linha treinada.",
                "wrong_moves_count": state["wrong_moves_count"],
            }
        )

    board.push(move)
    replayed += 1

    auto_reply = None
    if replayed < len(exercise.solution):
        reply = chess.Move.from_uci(exercise.solution[replayed])
        board.push(reply)
        auto_reply = exercise.solution[replayed]
        replayed += 1

    state["progress"] = replayed
    session.modified = True

    if replayed >= len(exercise.solution):
        finalize_current_exercise(success=True)
        next_payload = current_exercise_payload()
        return jsonify(
            {
                "status": "solved",
                "message": "Exercício concluído.",
                "auto_reply": auto_reply,
                "next": next_payload,
            }
        )

    return jsonify(
        {
            "status": "correct",
            "message": "Lance correto.",
            "auto_reply": auto_reply,
            "fen": board.fen(),
            "wrong_moves_count": state.get("wrong_moves_count", 0),
        }
    )


#@app.route("/report")
#def report() -> str:
#    report_row = finalize_session_report()
#    session_id = report_row["session_id"]
#    attempts = get_db().execute(
#        "SELECT * FROM attempts WHERE session_id = ? ORDER BY id",
#        (session_id,),
#    ).fetchall()
#    return render_template("report.html", report=report_row, attempts=attempts)
@app.route("/report")
def report() -> str:
    report_row = finalize_session_report()
    session_id = report_row["session_id"]

    conn = get_db()

    attempts = conn.execute(
        "SELECT * FROM attempts WHERE session_id = ? ORDER BY id",
        (session_id,),
    ).fetchall()

    attempts = enrich_attempts_with_history(conn, attempts, session_id)

    return render_template("report.html", report=report_row, attempts=attempts)


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
