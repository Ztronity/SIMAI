from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_session import Session
from functools import wraps
from datetime import datetime
import time, random, json, os

app = Flask(__name__)
app.secret_key = "simai_secret"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# -----------------------------
# BASE DE DADOS EM MEMÓRIA
# -----------------------------
infractions = []
payments = []
notifications = []

# =====================================================
# PERSISTÊNCIA EM JSON (SIMULA BANCO DE DADOS)
# =====================================================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

USERS_FILE = f"{DATA_DIR}/users.json"
INFRACTIONS_FILE = f"{DATA_DIR}/infractions.json"
NOTIFICATIONS_FILE = f"{DATA_DIR}/notifications.json"

def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

users = load_json(USERS_FILE, [])
infractions = load_json(INFRACTIONS_FILE, [])
notifications = load_json(NOTIFICATIONS_FILE, [])

# =====================================================
# FILTROS DE DATA (CORRIGE ERRO DO JINJA)
# =====================================================
@app.template_filter("format_date")
def format_date(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y")

@app.template_filter("format_datetime")
def format_datetime(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

# =====================================================
# DECORATORS DE SEGURANÇA
# =====================================================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            return "Acesso negado", 403
        return f(*args, **kwargs)
    return wrapper

# =====================================================
# USUÁRIOS
# =====================================================
def get_user(username):
    return next((u for u in users if u["username"] == username), None)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["user"].lower()
        password = request.form["password"]

        if get_user(username):
            return render_template("register.html", error="Usuário já existe")

        role = "admin" if username == "admin" else "user"

        users.append({
            "username": username,
            "password": password,
            "role": role
        })
        save_json(USERS_FILE, users)
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["user"].lower()
        password = request.form["password"]

        user = get_user(username)
        if user and user["password"] == password:
            session["logged"] = True
            session["username"] = username
            session["role"] = user["role"]
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Credenciais inválidas")

    return render_template("login.html")

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username")
        new_password = request.form.get("new_password")

        if not username or not new_password:
            return render_template(
                "forgot_password.html",
                error="Preencha todos os campos."
            )

        username = username.lower()
        users = load_users()
        updated = False

        for user in users:
            if user["username"] == username:
                user["password"] = new_password
                updated = True
                break

        if not updated:
            return render_template(
                "forgot_password.html",
                error="Usuário não encontrado."
            )

        save_users(users)
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# =====================================================
# DASHBOARD
# =====================================================
@app.route("/dashboard")
@login_required
def dashboard():
    if session["role"] == "admin":
        return render_template(
            "dashboard_admin.html",
            total_users=len(users),
            total_infractions=len(infractions),
            total_notifications=len(notifications)
        )

    user = session["username"]
    user_infractions = [i for i in infractions if i["owner"] == user]

    return render_template(
        "dashboard.html",
        total_infractions=len(user_infractions),
        total_notifications=len([n for n in notifications if n["to_user"] == user]),
        total_payments=0
    )

# =====================================================
# ADMIN → ENVIAR INFRAÇÃO
# =====================================================
@app.route("/admin/send_infraction", methods=["POST"])
@login_required
@admin_required
def send_infraction():
    data = request.json
    target_user = data["to_user"].lower()
    plate = data["plate"].upper()

    if not get_user(target_user):
        return jsonify({"error": "Usuário não encontrado"}), 400

    inf = {
        "id": random.randint(100000, 999999),
        "plate": plate,
        "description": "Excesso de velocidade",
        "timestamp": time.time(),
        "owner": target_user
    }
    infractions.append(inf)
    save_json(INFRACTIONS_FILE, infractions)

    notifications.append({
        "to_user": target_user,
        "message": f"🚨 Infração registrada para o veículo {plate}",
        "timestamp": time.time()
    })
    save_json(NOTIFICATIONS_FILE, notifications)

    return jsonify({"success": True})

# =====================================================
# LISTAR INFRAÇÕES DO USUÁRIO
# =====================================================
@app.route("/infractions")
@login_required
def list_infractions():
    user = session["username"]
    user_infractions = [i for i in infractions if i["owner"] == user]
    return render_template("infractions.html", infractions=user_infractions)

# =====================================================
# API DE NOTIFICAÇÕES (POLLING)
# =====================================================
@app.route("/api/notifications/check")
@login_required
def check_notifications():
    since = float(request.args.get("since", 0))
    user = session["username"]

    result = [
        n for n in notifications
        if n["to_user"] == user and n["timestamp"] > since
    ]
    return jsonify(result)

# =====================================================
# PAGAMENTOS
# =====================================================
@app.route("/payments")
@login_required
def payments_page():
    return render_template("payments.html", payments=payments)

# =====================================================
# HOME
# =====================================================
@app.route("/")
def home():
    return redirect(url_for("dashboard") if session.get("logged") else url_for("login"))

# =====================================================
# START
# =====================================================
if __name__ == "__main__":
    app.run(debug=True)
