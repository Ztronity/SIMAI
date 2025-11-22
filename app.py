from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_session import Session
import time
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "simai_secret"
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.template_filter('format_date')
def format_date(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y')

@app.template_filter('format_datetime')
def format_datetime(timestamp):
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

# -----------------------------
# BASE DE DADOS EM MEMÓRIA
# -----------------------------
infractions = []     # Lista de infrações
payments = []         # Histórico de pagamentos
notifications = []    # Notificações enviadas


# -----------------------------------
# FUNÇÃO FAKE PARA SIMULAR API DETRAN
# -----------------------------------
def simulate_detran_api(plate):
    """Simula busca de infrações na API do DETRAN."""
    if random.random() < 0.1:   # 10% chance de falhar
        return None  # Falha da API

    # Simulação de retorno
    return [
        {
            "id": random.randint(1000, 9999),
            "plate": plate,
            "description": "Excesso de velocidade",
            "points": 7,
            "timestamp": int(time.time())
        }
    ]


# --------------------------
# ROTAS DE AUTENTICAÇÃO
# --------------------------
import json
import os

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


# --------------------------
# ROTAS DE AUTENTICAÇÃO
# --------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_input = request.form.get("user")
        pwd_input = request.form.get("password")

        user = get_user(user_input)

        if user and user["password"] == pwd_input:
            session["logged"] = True
            session["username"] = user_input
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Usuário ou senha inválidos.")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("user")
        pwd = request.form.get("password")
        confirm_pwd = request.form.get("confirm_password")

        if pwd != confirm_pwd:
            return render_template("register.html", error="As senhas não coincidem.")

        if add_user(user, pwd):
            return redirect(url_for("login"))
        else:
            return render_template("register.html", error="Usuário já existe.")

    return render_template("register.html")


@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        user = request.form.get("user")
        new_pwd = request.form.get("new_password")
        
        if update_password(user, new_pwd):
             return redirect(url_for("login"))
        else:
             return render_template("forgot_password.html", error="Usuário não encontrado.")

    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------
# CHECAR LOGIN NAS ROTAS
# -------------------------
def login_required(route_func):
    def wrapper(*args, **kwargs):
        if not session.get("logged"):
            return redirect(url_for("login"))
        return route_func(*args, **kwargs)
    wrapper.__name__ = route_func.__name__
    return wrapper


# -------------------------
# DASHBOARD
# -------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    stats = {
        "total_infractions": len(infractions),
        "total_payments": len(payments),
        "total_notifications": len(notifications)
    }
    return render_template("dashboard.html", stats=stats)


# -----------------------------------
# CONSULTA DE INFRAÇÕES POR PLACA
# -----------------------------------
@app.route("/search_plate", methods=["POST"])
@login_required
def search_plate():
    plate = request.form.get("plate")

    filtered = [i for i in infractions if i["plate"] == plate.upper()]

    return render_template("infractions.html", infractions=filtered, query=plate)


# -------------------------
# ADICIONAR INFRAÇÃO FAKE
# -------------------------
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
            "plate": plate,
            "message": "Nova infração registrada!",
            "timestamp": time.time()
        })

    return jsonify({"success": True})


# -------------------------
# HISTÓRICO DE PAGAMENTOS
# -------------------------
@app.route("/pay/<int:inf_id>", methods=["POST"])
@login_required
def pay(inf_id):
    found = next((i for i in infractions if i["id"] == inf_id), None)

    if not found:
        return jsonify({"error": "Infração não encontrada"}), 404

    payments.append({
        "infraction_id": inf_id,
        "plate": found["plate"],
        "timestamp": time.time()
    })

    return jsonify({"success": True})


# ----------------------------
# LISTAR INFRAÇÕES
# ----------------------------
@app.route("/infractions")
@login_required
def list_infractions():
    return render_template("infractions.html", infractions=infractions, query=None)


# -------------------------
# LISTAR PAGAMENTOS
# -------------------------
@app.route("/payments")
@login_required
def list_payments():
    return render_template("payments.html", payments=payments)


# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    if not session.get("logged"):
        return redirect(url_for("login"))
    return redirect(url_for("dashboard"))


# -------------------------
# API NOTIFICAÇÕES (POLLING)
# -------------------------
@app.route("/api/notifications/check")
@login_required
def check_notifications():
    since = request.args.get("since", 0, type=float)
    # Retorna notificações mais recentes que o timestamp fornecido
    new_notifs = [n for n in notifications if n["timestamp"] > since]
    return jsonify(new_notifs)


# -------------------------
# RODAR O SERVIDOR
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
