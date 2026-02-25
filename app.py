from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_session import Session
import time
import random
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = "simai_secret"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# -----------------------------
# FILTROS DE TEMPLATE
# -----------------------------
@app.template_filter('format_date')
def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')

@app.template_filter('format_datetime')
def format_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

# -----------------------------
# BASE DE DADOS EM MEMÓRIA
# -----------------------------
infractions = []
payments = []
notifications = []

# -----------------------------
# FUNÇÃO DE ADMIN
# -----------------------------
def is_admin():
    return session.get("username") == "admin"

# -----------------------------------
# FUNÇÃO FAKE PARA SIMULAR API DETRAN
# -----------------------------------
def simulate_detran_api(plate):
    if random.random() < 0.1:
        return None

    return [{
        "id": random.randint(1000, 9999),
        "plate": plate,
        "description": "Excesso de velocidade",
        "points": 7,
        "timestamp": int(time.time())
    }]

# -----------------------------
# GERENCIAMENTO DE USUÁRIOS
# -----------------------------
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, "r") as f:
        return json.load(f).get("users", [])

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump({"users": users}, f, indent=4)

def get_user(username):
    users = load_users()
    return next((u for u in users if u["username"] == username), None)

def add_user(username, password):
    users = load_users()
    if any(u["username"] == username for u in users):
        return False
    users.append({"username": username, "password": password})
    save_users(users)
    return True

def update_password(username, new_password):
    users = load_users()
    for user in users:
        if user["username"] == username:
            user["password"] = new_password
            save_users(users)
            return True
    return False

# -----------------------------
# AUTENTICAÇÃO
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user")
        pwd = request.form.get("password")

        found = get_user(user)
        if found and found["password"] == pwd:
            session["logged"] = True
            session["username"] = user
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Usuário ou senha inválidos.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("user")
        pwd = request.form.get("password")
        confirm = request.form.get("confirm_password")

        if pwd != confirm:
            return render_template("register.html", error="As senhas não coincidem.")

        if add_user(user, pwd):
            return redirect(url_for("login"))

        return render_template("register.html", error="Usuário já existe.")
    return render_template("register.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        user = request.form.get("user")
        new_pwd = request.form.get("new_password")

        if update_password(user, new_pwd):
            return redirect(url_for("login"))

        return render_template("forgot_password.html", error="Usuário não encontrado.")
    return render_template("forgot_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# DECORATOR LOGIN
# -----------------------------
def login_required(route):
    def wrapper(*args, **kwargs):
        if not session.get("logged"):
            return redirect(url_for("login"))
        return route(*args, **kwargs)
    wrapper.__name__ = route.__name__
    return wrapper

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "total_infractions": len(infractions),
        "total_payments": len(payments),
        "total_notifications": len(notifications)
    }
    return render_template("dashboard.html", **stats)

# -----------------------------
# SIMULAR INFRAÇÃO (AUTOMÁTICA)
# -----------------------------
@app.route("/simulate/new_infraction", methods=["POST"])
@login_required
def simulate_new_infraction():
    plate = request.form.get("plate").upper()
    api_result = simulate_detran_api(plate)

    if api_result is None:
        return jsonify({"error": "Falha na API DETRAN"}), 500

    for inf in api_result:
        inf["id"] = random.randint(100000, 999999)
        infractions.append(inf)

        notifications.append({
            "to_user": session.get("username"),  # dono da infração
            "plate": plate,
            "message": "Nova infração registrada!",
            "timestamp": time.time()
            })


    return jsonify({"success": True})

# -----------------------------
# ADMIN → ENVIAR NOTIFICAÇÃO
# -----------------------------
@app.route("/admin/send_notification", methods=["POST"])
@login_required
def admin_send_notification():
    if session.get("username") != "admin":
        return jsonify({"error": "Acesso negado"}), 403

    to_user = request.form.get("to_user")
    plate = request.form.get("plate")
    message = request.form.get("message")

    notifications.append({
        "to_user": to_user,
        "plate": plate,
        "message": message,
        "timestamp": time.time()
    })

    return jsonify({"success": True})

# -----------------------------
# NOTIFICAÇÕES EM TEMPO REAL
# -----------------------------
@app.route("/api/notifications/check")
@login_required
def check_notifications():
    since = request.args.get("since", 0, type=float)
    user = session.get("username")

    new_notifs = []

    for n in notifications:
        if n["timestamp"] > since:
            # Se não tiver destinatário, é global
            if "to_user" not in n or n["to_user"] is None:
                new_notifs.append(n)
            # Se tiver, só envia ao usuário correto
            elif n["to_user"] == user:
                new_notifs.append(n)

    return jsonify(new_notifs)

# -----------------------------
# LISTAGENS
# -----------------------------
@app.route("/infractions")
@login_required
def list_infractions():
    return render_template("infractions.html", infractions=infractions, query=None)

@app.route("/payments")
@login_required
def list_payments():
    return render_template("payments.html", payments=payments)

@app.route("/")
def home():
    return redirect(url_for("dashboard")) if session.get("logged") else redirect(url_for("login"))

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
