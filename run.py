import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # Defaults keep local-only behaviour unchanged. Set FLASK_HOST=0.0.0.0
    # to let teammates on the same network reach the dashboard, and leave
    # FLASK_DEBUG unset (or "0") for anything other than your own machine —
    # Flask's debugger allows arbitrary code execution if it's reachable
    # from outside localhost.
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", "5001"))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host=host, port=port, debug=debug)
