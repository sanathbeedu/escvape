import threading
import time
import webbrowser

import requests
import uvicorn

from api_server import app


def _start_api_server() -> None:
    """Start FastAPI server (runs in background thread)."""
    # Disable HTTP access logs to avoid noisy per-request INFO lines in the desktop app
    config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="info", access_log=False)
    server = uvicorn.Server(config)
    server.run()


def _wait_for_server(timeout: float = 30.0) -> bool:
    """Wait until the API server responds on /health or timeout."""
    deadline = time.time() + timeout
    url = "http://127.0.0.1:8000/health"

    while time.time() < deadline:
        try:
            resp = requests.get(url, timeout=1.0)
            if resp.status_code == 200:
                return True
        except Exception:
            time.sleep(1.0)

    return False


def main() -> None:
    """Entry point for the macOS desktop app bundle.

    Starts the FastAPI backend on localhost and opens the web UI in the
    user's default browser.
    """
    # Start API server in background daemon thread
    server_thread = threading.Thread(target=_start_api_server, daemon=True)
    server_thread.start()

    # Wait briefly for server to be ready
    _wait_for_server()

    # Open the main web frontend in the default browser
    webbrowser.open("http://127.0.0.1:8000/")

    # Keep the launcher process alive while the server is running
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
