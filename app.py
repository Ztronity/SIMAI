from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from flask_session import Session
import time, random, json, os
from datetime import datetime
from functools import wraps

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

# -----------------------------
# USUÁRIOS (JSON)
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
    return next((u for u in load_users() if u["username"] == username), None)

# -----------------------------
# LOGIN REQUIRED
# -----------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logged"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# -----------------------------
# AUTENTICAÇÃO
# -----------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user").lower()
        pwd = request.form.get("password")

        u = get_user(user)
        if u and u["password"] == pwd:
            session["logged"] = True
            session["username"] = user
            return redirect("/dashboard")

        return render_template("login.html", error="Credenciais inválidas")

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get("user").lower()
        pwd = request.form.get("password")

        users = load_users()
        if get_user(user):
            return render_template("register.html", error="Usuário já existe")

        users.append({"username": user, "password": pwd})
        save_users(users)
        return redirect("/login")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        total_infractions=len(infractions),
        total_notifications=len(notifications),
        total_payments=len(payments),
    )

# -----------------------------
# LISTAGENS
# -----------------------------
@app.route("/infractions")
@login_required
def list_infractions():
    return render_template("infractions.html", infractions=infractions)

@app.route("/payments")
@login_required
def list_payments():
    return render_template("payments.html", payments=payments)

# -----------------------------
# ADMIN → ENVIAR INFRAÇÃO
# -----------------------------
@app.route("/admin/send_infraction", methods=["POST"])
@login_required
def send_infraction():
    data = request.json
    plate = data["plate"].upper()
    target_user = data["to_user"].lower()

    inf = {
        "id": random.randint(100000, 999999),
        "plate": plate,
        "description": "Excesso de velocidade",
        "timestamp": time.time()
    }
    infractions.append(inf)

    notifications.append({
        "to_user": target_user,
        "message": f"🚨 Infração registrada para o veículo {plate}",
        "timestamp": time.time()
    })

    return jsonify({"success": True})

# -----------------------------
# API DE NOTIFICAÇÕES (POLLING)
# -----------------------------
@app.route("/api/notifications/check")
@login_required
def check_notifications():
    since = float(request.args.get("since", 0))
    user = session["username"].lower()

    result = [
        n for n in notifications
        if n["to_user"] == user and n["timestamp"] > since
    ]

    return jsonify(result)

# -----------------------------
# FILTROS DE DATA
# -----------------------------
@app.template_filter("format_datetime")
def format_datetime(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")

@app.template_filter("format_date")
def format_date(ts):
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y")

# -----------------------------
# START
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
