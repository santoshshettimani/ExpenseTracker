
import os
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    session, url_for
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")


def get_db():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_database():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)

    # Add user_id to existing databases if it does not exist.
    columns = [
        row["name"]
        for row in conn.execute("PRAGMA table_info(expenses)").fetchall()
    ]

    if "user_id" not in columns:
        conn.execute("ALTER TABLE expenses ADD COLUMN user_id INTEGER")

    conn.commit()
    conn.close()


create_database()


def login_required(route):
    @wraps(route)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return route(*args, **kwargs)
    return wrapper


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "Please fill in all fields."
        elif len(password) < 8:
            error = "Password must contain at least 8 characters."
        else:
            conn = get_db()
            try:
                conn.execute(
                    "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                    (name, email, generate_password_hash(password))
                )
                conn.commit()
                user = conn.execute(
                    "SELECT id, name FROM users WHERE email = ?", (email,)
                ).fetchone()

                session.clear()
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]

                return redirect(url_for("home"))

            except sqlite3.IntegrityError:
                error = "An account with this email already exists."
            finally:
                conn.close()

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("home"))

        error = "Invalid email or password."

    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def home():
    conn = get_db()
    user_id = session["user_id"]

    expenses = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC",
        (user_id,)
    ).fetchall()

    income = conn.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND type = 'Income'",
        (user_id,)
    ).fetchone()[0] or 0

    expense = conn.execute(
        "SELECT SUM(amount) FROM expenses WHERE user_id = ? AND type = 'Expense'",
        (user_id,)
    ).fetchone()[0] or 0

    category_data = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE user_id = ? AND type = 'Expense'
        GROUP BY category
    """, (user_id,)).fetchall()

    category_data = [dict(row) for row in category_data]
    conn.close()

    balance = income - expense

    return render_template(
        "index.html",
        expenses=expenses,
        income=income,
        expense=expense,
        balance=balance,
        category_data=category_data,
        user_name=session.get("user_name")
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "").strip()
    transaction_type = request.form.get("type", "")

    try:
        amount = float(request.form.get("amount", 0))
    except ValueError:
        return redirect(url_for("home"))

    if not title or not category or amount <= 0:
        return redirect(url_for("home"))

    if transaction_type not in ["Income", "Expense"]:
        return redirect(url_for("home"))

    conn = get_db()
    conn.execute(
        """INSERT INTO expenses
        (title, amount, category, type, user_id)
        VALUES (?, ?, ?, ?, ?)""",
        (title, amount, category, transaction_type, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


@app.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    conn = get_db()
    conn.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (id, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)



