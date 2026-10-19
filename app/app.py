"""Tiny Flask web app used for the Week 3 Docker homework and the Week 5 CI pipeline."""

import os
import platform
import socket

from flask import Flask, jsonify

app = Flask(__name__)
APP_VERSION = os.environ.get("APP_VERSION", "1.0.0")


def greeting(name=None):
    """Return the greeting shown on the index page.

    Kept as a plain function so it can be unit tested without an HTTP request.
    """
    who = (name or "").strip()
    if not who:
        return "Hello from the DevOps Week 5 container"
    return f"Hello, {who}, from the DevOps Week 5 container"


@app.get("/")
def index():
    return jsonify(
        message=greeting(),
        version=APP_VERSION,
        hostname=socket.gethostname(),
        python=platform.python_version(),
        user=os.environ.get("USER") or f"uid {os.getuid()}",
    )


@app.get("/hello/<name>")
def hello(name):
    return jsonify(message=greeting(name))


@app.get("/healthz")
def healthz():
    # A real endpoint for the Docker HEALTHCHECK. Returns 200 when the app
    # can serve requests; anything else marks the container unhealthy.
    return jsonify(status="ok"), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
