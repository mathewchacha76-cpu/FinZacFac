import os
import sqlite3
import smtplib
from contextlib import closing
from datetime import datetime
from email.message import EmailMessage

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "zafac-dev-secret")
app.config["DATABASE"] = os.environ.get("DATABASE_URL", "zafac.db")
app.config["ADMIN_USERNAME"] = os.environ.get("ADMIN_USERNAME", "admin")
app.config["ADMIN_PASSWORD_HASH"] = os.environ.get("ADMIN_PASSWORD_HASH") or generate_password_hash(
    os.environ.get("ADMIN_PASSWORD", "ZafacAdmin2026!")
)
app.config["CONTACT_EMAIL"] = os.environ.get("CONTACT_EMAIL", "zafacautospares@gmail.com")
app.config["SITE_TITLE"] = "Zafac Autospares"
app.config["SITE_TAGLINE"] = "Quality motorcycle spare parts & repair services."


def get_db():
    conn = sqlite3.connect(app.config["DATABASE"])
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_db()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price TEXT NOT NULL,
                image_url TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS contact_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def seed_data():
    with closing(get_db()) as conn:
        existing = conn.execute("SELECT COUNT(*) AS count FROM products").fetchone()["count"]
        if existing == 0:
            sample_products = [
                (
                    "Brake Pad Set",
                    "Braking",
                    "Reliable replacement pads for daily commuting and rough road use.",
                    "KSh 2,800",
                    "https://images.unsplash.com/photo-1511919884226-fd3cad34687c?auto=format&fit=crop&w=800&q=80",
                ),
                (
                    "Motor Oil Filter",
                    "Engine",
                    "Durable filter designed for steady engine performance and long life.",
                    "KSh 1,200",
                    "https://images.unsplash.com/photo-1558981806-ec527fa84c39?auto=format&fit=crop&w=800&q=80",
                ),
                (
                    "Bike Chain Kit",
                    "Drive Train",
                    "Heavy-duty chain and sprocket set for smooth movement and durability.",
                    "KSh 4,500",
                    "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?auto=format&fit=crop&w=800&q=80",
                ),
            ]
            for item in sample_products:
                conn.execute(
                    """
                    INSERT INTO products (name, category, description, price, image_url, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (*item, datetime.now().isoformat()),
                )
            conn.commit()


init_db()
seed_data()


@app.route("/")
def home():
    products = get_products(limit=3)
    return render_template("index.html", products=products)


@app.route("/products")
def products():
    return render_template("products.html", products=get_products())


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


@app.route("/tips")
def tips():
    return render_template("tips.html")


@app.route("/faq")
def faq():
    return render_template("faq.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()

        if not all([name, email, phone, message]):
            flash("Please fill in all contact fields before sending your message.")
            return redirect(url_for("contact"))

        with closing(get_db()) as conn:
            conn.execute(
                """
                INSERT INTO contact_messages (name, email, phone, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, email, phone, message, datetime.now().isoformat()),
            )
            conn.commit()

        sent = send_contact_email(name, email, phone, message)
        if sent:
            flash("Thanks for reaching out. We have received your message and will get back soon.")
        else:
            flash("Your message was stored successfully. We will follow up soon.")
        return redirect(url_for("contact"))

    return render_template("contact.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == app.config["ADMIN_USERNAME"] and check_password_hash(
            app.config["ADMIN_PASSWORD_HASH"], password
        ):
            session["admin_logged_in"] = True
            return redirect(url_for("admin_products"))
        flash("Invalid admin username or password.")

    return render_template("admin_login.html")


@app.route("/admin/products")
def admin_products():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))
    return render_template("admin_products.html", products=get_products())


@app.route("/admin/products", methods=["POST"])
def add_product():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    image_url = request.form.get("image_url", "").strip()

    if not all([name, category, description, price, image_url]):
        flash("Please complete every product field before saving.")
        return redirect(url_for("admin_products"))

    with closing(get_db()) as conn:
        conn.execute(
            """
            INSERT INTO products (name, category, description, price, image_url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (name, category, description, price, image_url, datetime.now().isoformat()),
        )
        conn.commit()

    flash("Product added successfully.")
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
def delete_product(product_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    with closing(get_db()) as conn:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
    flash("Product removed.")
    return redirect(url_for("admin_products"))


@app.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    flash("You have been logged out.")
    return redirect(url_for("home"))


def get_products(limit=None):
    with closing(get_db()) as conn:
        query = "SELECT * FROM products ORDER BY created_at DESC"
        if limit:
            query += " LIMIT ?"
            return conn.execute(query, (limit,)).fetchall()
        return conn.execute(query).fetchall()


def send_contact_email(name, email, phone, message):
    recipient = app.config["CONTACT_EMAIL"]
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port = os.environ.get("SMTP_PORT")
    smtp_username = os.environ.get("SMTP_USERNAME")
    smtp_password = os.environ.get("SMTP_PASSWORD")

    if not smtp_server or not smtp_port:
        print(f"Contact email from {email}: {message}")
        return False

    msg = EmailMessage()
    msg["Subject"] = f"Website inquiry from {name}"
    msg["From"] = smtp_username or recipient
    msg["To"] = recipient
    msg.set_content(
        f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}"
    )

    try:
        with smtplib.SMTP(smtp_server, int(smtp_port)) as smtp:
            if os.environ.get("SMTP_USE_TLS") == "1":
                smtp.starttls()
            if smtp_username and smtp_password:
                smtp.login(smtp_username, smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        print(f"Email sending failed: {exc}")
        return False


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
