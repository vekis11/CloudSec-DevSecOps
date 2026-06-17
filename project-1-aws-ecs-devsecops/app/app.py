"""
Sample Flask API for DevSecOps practice.
Contains intentional patterns that SAST/SCA tools should flag in CI.
"""
import os
import subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)

# Intentional: hardcoded secret for Gitleaks/Semgrep demos (never do this in production)
DEMO_API_KEY = "sk-live-demo-key-replace-in-production"

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "service": "ecs-devsecops-demo"})

@app.route("/api/info")
def info():
    return jsonify({
        "version": os.getenv("APP_VERSION", "1.0.0"),
        "environment": os.getenv("ENVIRONMENT", "dev"),
    })

@app.route("/api/echo", methods=["POST"])
def echo():
    data = request.get_json(silent=True) or {}
    # Intentional: command injection pattern for Semgrep demo
    user_input = data.get("cmd", "")
    if user_input and os.getenv("ENABLE_UNSAFE_DEMO") == "true":
        output = subprocess.check_output(user_input, shell=True, text=True)
        return jsonify({"output": output})
    return jsonify({"echo": data})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
