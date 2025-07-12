from flask import Flask, request, render_template, redirect, url_for, session, jsonify, Response
from flask_pymongo import PyMongo
from bson import ObjectId
from datetime import datetime
import json
import csv

app = Flask(__name__)
app.secret_key = "supersecretkey"

# MongoDB config
app.config["MONGO_URI"] = "mongodb://localhost:27017/webhook_db"
mongo = PyMongo(app)

# Home redirect to login
@app.route("/")
def home():
    return redirect(url_for("login"))

# Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = mongo.db.users.find_one({"username": username})
        if existing_user:
            return "Username already exists. Try another."

        mongo.db.users.insert_one({"username": username, "password": password})
        session["username"] = username
        return redirect(url_for("dashboard"))

    return render_template("signup.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = mongo.db.users.find_one({"username": username, "password": password})
        if user:
            session["username"] = username
            return redirect(url_for("dashboard"))
        else:
            return "Invalid credentials."
    return render_template("login.html")

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", username=session["username"])

# ✅ Webhook endpoint (fixed)
@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        # Log raw data
        raw_data = request.data
        print("=== RAW DATA RECEIVED ===")
        print(raw_data)

        # Try to parse JSON
        data = request.get_json(force=True)
        if not data:
            return "No JSON received", 400

        data["timestamp"] = datetime.utcnow()
        mongo.db.webhooks.insert_one(data)
        return "Webhook received!", 200

    except Exception as e:
        return f"Error: {str(e)}", 500

# View stored webhooks
@app.route("/view")
def view_data():
    if "username" not in session:
        return redirect(url_for("login"))

    webhooks = list(mongo.db.webhooks.find())
    for doc in webhooks:
        if "timestamp" not in doc:
            doc["timestamp"] = None
    return render_template("view.html", data=webhooks)

# Delete webhook by ID
@app.route("/delete/<id>", methods=["POST"])
def delete_webhook(id):
    mongo.db.webhooks.delete_one({"_id": ObjectId(id)})
    return "", 204

# Export as CSV
@app.route("/export")
def export_csv():
    webhooks = mongo.db.webhooks.find()
    def generate():
        yield "ID,Payload,Timestamp\n"
        for doc in webhooks:
            payload = json.dumps(doc, default=str)
            timestamp = doc.get("timestamp").strftime("%Y-%m-%d %H:%M:%S") if doc.get("timestamp") else ""
            yield f"{str(doc.get('_id'))},{payload},{timestamp}\n"
    return Response(generate(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=webhooks.csv"})

# API endpoint for dashboard chart data
@app.route("/api/stats")
def api_stats():
    pipeline = [
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    stats = list(mongo.db.webhooks.aggregate(pipeline))
    return jsonify(stats)

if __name__ == "__main__":
    app.run(debug=True)
