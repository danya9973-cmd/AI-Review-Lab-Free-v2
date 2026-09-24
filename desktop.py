"""Native macOS window entry point for AI Review Lab."""

from __future__ import annotations

import os
from pathlib import Path
import sys
import threading

from dotenv import load_dotenv


APP_NAME = "AI Review Lab"
CONFIG_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
CONFIG_FILE = CONFIG_DIR / ".env"


def load_desktop_environment() -> None:
    """Load secrets from the user's private Application Support directory."""
    if CONFIG_FILE.exists():
        load_dotenv(CONFIG_FILE, override=True)
    else:
        # The build/test sandbox may deny this location. A normal desktop launch
        # prepares it via build-macos-app.command before the app starts.
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass

        # A freshly built personal app can run directly from this repository's
        # dist folder before it is moved to Applications.
        if getattr(sys, "frozen", False):
            repository_env = Path(sys.executable).resolve().parents[4] / ".env"
            if repository_env.exists():
                load_dotenv(repository_env, override=True)
        else:
            load_dotenv(Path(__file__).resolve().parent / ".env", override=True)
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PORT"] = "0"
    os.environ["DEBUG"] = "false"


def main() -> None:
    load_desktop_environment()

    from werkzeug.serving import make_server

    # Import after loading the private environment so provider clients receive keys.
    from app import app as flask_app

    server = make_server("127.0.0.1", 0, flask_app, threaded=True)
    port = server.socket.getsockname()[1]
    ready_file_value = os.getenv("AI_REVIEW_LAB_READY_FILE", "").strip()
    ready_file = Path(ready_file_value) if ready_file_value else None
    if ready_file:
        ready_file.write_text(str(port), encoding="utf-8")
    server_thread = threading.Thread(target=server.serve_forever, name="ai-review-lab-server", daemon=True)
    server_thread.start()

    try:
        if os.getenv("AI_REVIEW_LAB_HEADLESS", "0") == "1":
            threading.Event().wait()
        else:
            import webview

            webview.create_window(
                APP_NAME,
                f"http://127.0.0.1:{port}",
                width=1180,
                height=820,
                min_size=(760, 640),
                background_color="#f4f1ea",
                text_select=True,
            )
            webview.start(debug=False)
    finally:
        server.shutdown()
        server.server_close()
        if ready_file:
            ready_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
