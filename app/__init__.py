from flask import Flask, render_template, session
import os

from config import Config, DEFAULT_SECRET_KEY
from app.database import init_app as init_database

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(Config)
    # Config.DATABASE is fixed at import time, which happens once per
    # process — re-read the env var here so tests (which set it fresh per
    # run) actually get an isolated database instead of the class-body value.
    app.config["DATABASE"] = os.environ.get("DATABASE_PATH", app.config["DATABASE"])

    if app.config["SECRET_KEY"] == DEFAULT_SECRET_KEY:
        app.logger.warning(
            "SECRET_KEY is still the built-in default — set the SECRET_KEY "
            "environment variable before deploying this anywhere but your own machine."
        )

    from app.routes.auth_routes import auth_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.employee_routes import employee_bp
    from app.routes.assets_routes import assets_bp
    from app.routes.dashboard_routes import dashboard_bp
    from app.routes.license_routes import licenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(assets_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(licenses_bp)
    init_database(app)

    @app.route("/")
    def index():
        user = session.get("user")
        if not user:
            return render_template("login.html")
        if user["role"] == "ADMIN":
            return render_template("admin_dashboard.html", user=user)
        return render_template("employee_dashboard.html", user=user)

    return app
