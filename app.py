
from flask import Flask, render_template, request, redirect
import sqlite3

app = Flask(__name__)

def create_database():
    conn = sqlite3.connect("expenses.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            type TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
create_database()

@app.route("/")
def home():
    conn = sqlite3.connect("expenses.db")
    conn.row_factory = sqlite3.Row

    expenses = conn.execute(
        "SELECT * FROM expenses ORDER BY id DESC"
    ).fetchall()

    income = conn.execute(
        "SELECT SUM(amount) FROM expenses WHERE type='Income'"
    ).fetchone()[0] or 0

    expense = conn.execute(
        "SELECT SUM(amount) FROM expenses WHERE type='Expense'"
    ).fetchone()[0] or 0

    category_data = conn.execute("""
        SELECT category, SUM(amount) AS total
        FROM expenses
        WHERE type = 'Expense'
        GROUP BY category
    """).fetchall()

    category_data = [dict(row) for row in category_data]

    conn.close()

    balance = income - expense

    return render_template(
        "index.html",
        expenses=expenses,
        income=income,
        expense=expense,
        balance=balance,
        category_data=category_data
    )

@app.route("/add", methods=["POST"])
def add():
    title = request.form["title"]
    amount = float(request.form["amount"])
    category = request.form["category"]
    transaction_type = request.form["type"]

    conn = sqlite3.connect("expenses.db")
    conn.execute(
        "INSERT INTO expenses (title, amount, category, type) VALUES (?, ?, ?, ?)",
        (title, amount, category, transaction_type)
    )
    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete/<int:id>")
def delete(id):
    conn = sqlite3.connect("expenses.db")
    conn.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    create_database()
    app.run(debug=True)
