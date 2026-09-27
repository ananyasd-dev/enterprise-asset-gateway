import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DEFAULT_SECRET_KEY = "enterprise-asset-gateway-key-2026"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Only require HTTPS for the session cookie once this is actually served
    # over HTTPS (set SESSION_COOKIE_SECURE=1). Forcing it on by default
    # would silently break login over plain HTTP on a local network.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    # Overridable so tests (and anyone else) can point this at an isolated
    # file instead of sharing the real dev/demo database.
    DATABASE = os.environ.get(
    "DATABASE_PATH", os.path.join(BASE_DIR, "instance", "mock_assets.db")
    )
