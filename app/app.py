"""Task Manager - Flask app: login, CRUD, REST API, metrics, JSON logs."""
import json
import logging
import os
import sys
import time
from functools import wraps

from flask import Flask, jsonify, redirect, render_template, request, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

db = SQLAlchemy()
REQS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LAT = Histogram("http_request_duration_seconds", "Request latency", ["endpoint"])


class JsonFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({"ts": self.formatTime(record), "level": record.levelname,
                           "logger": record.name, "msg": record.getMessage()})


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    done = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "description": self.description, "done": self.done}


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if "uid" not in session:
            if request.path.startswith("/api/"):
                return jsonify(error="authentication required"), 401
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-me"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///tasks.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if config:
        app.config.update(config)

    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    app.logger.handlers = [h]
    app.logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    db.init_app(app)

    with app.app_context():
        db.create_all()
        admin = os.getenv("ADMIN_USER")
        if admin and not User.query.filter_by(username=admin).first():
            db.session.add(User(username=admin, password_hash=generate_password_hash(os.getenv("ADMIN_PASSWORD", "admin"))))
            db.session.commit()

    @app.before_request
    def _start():
        request._t = time.time()

    @app.after_request
    def _metrics(resp):
        ep = request.endpoint or "unknown"
        REQS.labels(request.method, ep, resp.status_code).inc()
        LAT.labels(ep).observe(time.time() - getattr(request, "_t", time.time()))
        app.logger.info("%s %s %s", request.method, request.path, resp.status_code)
        return resp

    @app.errorhandler(Exception)
    def _err(e):
        code = e.code if isinstance(e, HTTPException) else 500
        if code == 500:
            app.logger.exception("unhandled error")
        if request.path.startswith("/api/") or code == 500:
            return jsonify(error=getattr(e, "description", "internal error")), code
        return render_template("error.html", code=code), code

    # ---- ops endpoints ----
    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/readyz")
    def readyz():
        db.session.execute(db.text("SELECT 1"))
        return jsonify(status="ready")

    @app.get("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    @app.get("/version")
    def version():
        return jsonify(version=os.getenv("APP_VERSION", "dev"), color=os.getenv("DEPLOY_COLOR", "n/a"))

    # ---- auth ----
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            u, p = request.form.get("username", "").strip(), request.form.get("password", "")
            if not u or len(p) < 4:
                flash("Username required and password must be 4+ chars")
            elif User.query.filter_by(username=u).first():
                flash("Username already taken")
            else:
                db.session.add(User(username=u, password_hash=generate_password_hash(p)))
                db.session.commit()
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            data = request.get_json(silent=True) or request.form
            user = User.query.filter_by(username=data.get("username", "")).first()
            if user and check_password_hash(user.password_hash, data.get("password", "")):
                session["uid"] = user.id
                if request.is_json:
                    return jsonify(message="logged in")
                return redirect(url_for("index"))
            if request.is_json:
                return jsonify(error="invalid credentials"), 401
            flash("Invalid credentials")
        return render_template("login.html")

    @app.get("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    # ---- web UI ----
    @app.get("/")
    @login_required
    def index():
        tasks = Task.query.filter_by(user_id=session["uid"]).order_by(Task.id.desc()).all()
        return render_template("tasks.html", tasks=tasks)

    @app.post("/tasks/add")
    @login_required
    def add_ui():
        t = request.form.get("title", "").strip()
        if t:
            db.session.add(Task(title=t, description=request.form.get("description", ""), user_id=session["uid"]))
            db.session.commit()
        return redirect(url_for("index"))

    @app.post("/tasks/<int:tid>/toggle")
    @login_required
    def toggle_ui(tid):
        t = Task.query.filter_by(id=tid, user_id=session["uid"]).first_or_404()
        t.done = not t.done
        db.session.commit()
        return redirect(url_for("index"))

    @app.post("/tasks/<int:tid>/delete")
    @login_required
    def delete_ui(tid):
        t = Task.query.filter_by(id=tid, user_id=session["uid"]).first_or_404()
        db.session.delete(t)
        db.session.commit()
        return redirect(url_for("index"))

    # ---- REST API ----
    @app.get("/api/tasks")
    @login_required
    def api_list():
        return jsonify([t.to_dict() for t in Task.query.filter_by(user_id=session["uid"])])

    @app.post("/api/tasks")
    @login_required
    def api_create():
        d = request.get_json(silent=True) or {}
        if not str(d.get("title", "")).strip():
            return jsonify(error="title is required"), 400
        t = Task(title=d["title"].strip(), description=d.get("description", ""), user_id=session["uid"])
        db.session.add(t)
        db.session.commit()
        return jsonify(t.to_dict()), 201

    @app.get("/api/tasks/<int:tid>")
    @login_required
    def api_get(tid):
        return jsonify(Task.query.filter_by(id=tid, user_id=session["uid"]).first_or_404().to_dict())

    @app.put("/api/tasks/<int:tid>")
    @login_required
    def api_update(tid):
        t = Task.query.filter_by(id=tid, user_id=session["uid"]).first_or_404()
        d = request.get_json(silent=True) or {}
        t.title = d.get("title", t.title)
        t.description = d.get("description", t.description)
        t.done = bool(d.get("done", t.done))
        db.session.commit()
        return jsonify(t.to_dict())

    @app.delete("/api/tasks/<int:tid>")
    @login_required
    def api_delete(tid):
        t = Task.query.filter_by(id=tid, user_id=session["uid"]).first_or_404()
        db.session.delete(t)
        db.session.commit()
        return "", 204

    return app


app = create_app() if os.getenv("FLASK_RUN_FROM_CLI") != "1" and __name__ != "__main__" and os.getenv("NO_AUTO_APP") != "1" else None

if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
