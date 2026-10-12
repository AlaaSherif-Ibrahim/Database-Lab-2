"""
Lab 2: Login & To-Do Application
Flask + PyMySQL + bcrypt, MySQL database "registration".

Rules followed everywhere in this file:
  1. Passwords are stored only as bcrypt hashes.
  2. Every SQL statement uses %s placeholders; values are passed separately.
  3. user_id always comes from the session, never from a form or URL.
  4. Every form is validated on the server (the browser checks it too).
"""

import os
from functools import wraps

import bcrypt
import pymysql
from dotenv import load_dotenv
from flask import (Flask, flash, redirect, render_template, request,
                   session, url_for)

# Read DB_HOST, DB_PASSWORD, SECRET_KEY, ... from the .env file
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-only-change-me")

TITLE_MAX = 200  # same as VARCHAR(200) in the todos table


# ---------------------------------------------------------------------
# Database helper
# ---------------------------------------------------------------------
def get_db():
    """Open a new connection to the registration database."""
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "registration"),
        cursorclass=pymysql.cursors.DictCursor,  # rows come back as dicts
        autocommit=True,
    )


def login_required(view):
    """Send visitors who are not logged in to the login page (R3)."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapper


def validate_title(title):
    """Return the error message for a to-do title, or None if it is fine."""
    if title.strip() == "":
        return "Title is required"
    if len(title.strip()) > TITLE_MAX:
        return "Title is too long (200 characters at most)"
    return None


# ---------------------------------------------------------------------
# Register (R1)
# ---------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("todos"))

    errors = {}
    form = {"name": "", "email": ""}

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        form = {"name": name, "email": email}

        # Server-side checks (same rules as the JavaScript ones)
        if not name:
            errors["name"] = "Name is required"
        if not email:
            errors["email"] = "Email is required"
        if not password:
            errors["password"] = "Password is required"
        if not confirm:
            errors["confirm_password"] = "Confirm password is required"
        elif password and password != confirm:
            errors["confirm_password"] = "Passwords do not match"

        if not errors:
            # Hash the password (bcrypt, cost 12 -> "$2b$12$...")
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt(rounds=12)
            ).decode("utf-8")

            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO users (email, name, password_hash) VALUES (%s, %s, %s)",
                        (email, name, password_hash),
                    )
                    new_id = cur.lastrowid
            except pymysql.err.IntegrityError as e:
                # 1062 = duplicate entry -> the UNIQUE(email) constraint
                if e.args[0] == 1062:
                    errors["email"] = "Email Already Exists"
                else:
                    raise
            finally:
                conn.close()

            if not errors:
                # Log the new user in and go to the list
                session.clear()
                session["user_id"] = new_id
                session["name"] = name
                flash(f"Welcome, {name}! Your account was created.", "success")
                return redirect(url_for("todos"))

    return render_template("register.html", errors=errors, form=form)


# ---------------------------------------------------------------------
# Login / Logout (R2)
# ---------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("todos"))

    errors = {}
    email = ""

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email:
            errors["email"] = "Email is required"
        if not password:
            errors["password"] = "Password is required"

        if not errors:
            conn = get_db()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT user_id, name, password_hash FROM users WHERE email = %s",
                        (email,),
                    )
                    user = cur.fetchone()
            finally:
                conn.close()

            # Same message for unknown e-mail and wrong password
            if user and bcrypt.checkpw(password.encode("utf-8"),
                                       user["password_hash"].encode("utf-8")):
                session.clear()
                session["user_id"] = user["user_id"]
                session["name"] = user["name"]
                return redirect(url_for("todos"))

            errors["form"] = "Invalid email or password"

    return render_template("login.html", errors=errors, email=email)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------
# The to-do list (R3)
# ---------------------------------------------------------------------
@app.route("/")
@login_required
def todos():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT todo_id, title, is_done, created_at FROM todos "
                "WHERE user_id = %s ORDER BY todo_id DESC",
                (session["user_id"],),
            )
            items = cur.fetchall()
    finally:
        conn.close()

    # Bonus: filter (all / open / done) and open counter, done in Python
    # so the SQL stays exactly the given query.
    current_filter = request.args.get("filter", "all")
    open_count = sum(1 for t in items if not t["is_done"])
    if current_filter == "open":
        shown = [t for t in items if not t["is_done"]]
    elif current_filter == "done":
        shown = [t for t in items if t["is_done"]]
    else:
        current_filter = "all"
        shown = items

    return render_template(
        "todos.html",
        todos=shown,
        total=len(items),
        open_count=open_count,
        current_filter=current_filter,
        add_error=session.pop("add_error", None),
        add_value=session.pop("add_value", ""),
        edit_error=session.pop("edit_error", None),
    )


# ---------------------------------------------------------------------
# Add / Edit / Toggle / Delete (R4 - R7)
# ---------------------------------------------------------------------
@app.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title", "")
    error = validate_title(title)
    if error:
        # Do not touch the database; show the list again with the message
        session["add_error"] = error
        session["add_value"] = title[:TITLE_MAX + 50]
        return redirect(url_for("todos"))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO todos (user_id, title) VALUES (%s, %s)",
                (session["user_id"], title.strip()),
            )
    finally:
        conn.close()
    return redirect(url_for("todos"))


@app.route("/edit/<int:todo_id>", methods=["POST"])
@login_required
def edit(todo_id):
    title = request.form.get("title", "")
    error = validate_title(title)
    if error:
        session["edit_error"] = {"id": todo_id, "message": error}
        return redirect(url_for("todos"))

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # AND user_id = %s -> changes 0 rows if the to-do is not yours
            cur.execute(
                "UPDATE todos SET title = %s WHERE todo_id = %s AND user_id = %s",
                (title.strip(), todo_id, session["user_id"]),
            )
    finally:
        conn.close()
    return redirect(url_for("todos"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
@login_required
def toggle(todo_id):
    # The new state comes from the form: "1" = done, anything else = open
    is_done = 1 if request.form.get("is_done") == "1" else 0

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE todos SET is_done = %s WHERE todo_id = %s AND user_id = %s",
                (is_done, todo_id, session["user_id"]),
            )
    finally:
        conn.close()
    return redirect(url_for("todos", filter=request.args.get("filter", "all")))


@app.route("/delete/<int:todo_id>", methods=["POST"])
@login_required
def delete(todo_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM todos WHERE todo_id = %s AND user_id = %s",
                (todo_id, session["user_id"]),
            )
    finally:
        conn.close()
    return redirect(url_for("todos", filter=request.args.get("filter", "all")))


# ---------------------------------------------------------------------
# Friendly error pages (no stack traces for the user)
# ---------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message="This page does not exist."), 404


@app.errorhandler(405)
def not_allowed(e):
    return render_template("error.html", code=405,
                           message="That action is not allowed here."), 405


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500,
                           message="Something went wrong on our side. Please try again."), 500


@app.errorhandler(pymysql.err.OperationalError)
def db_down(e):
    return render_template("error.html", code=503,
                           message="Cannot reach the database. Is MySQL running and is .env correct?"), 503


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
