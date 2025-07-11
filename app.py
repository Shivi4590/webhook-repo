from flask import Flask, request, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["webhook_db"]
events = db["events"]

@app.route('/webhook', methods=['POST'])
def webhook():
    payload = request.json
    action = ""
    author = ""
    from_branch = ""
    to_branch = ""
    timestamp = datetime.utcnow().strftime("%d %B %Y - %I:%M %p UTC")

    if 'head_commit' in payload:
        action = "push"
        author = payload["head_commit"]["author"]["name"]
        to_branch = payload["ref"].split("/")[-1]

    elif 'pull_request' in payload:
        action = "pull_request"
        author = payload["pull_request"]["user"]["login"]
        from_branch = payload["pull_request"]["head"]["ref"]
        to_branch = payload["pull_request"]["base"]["ref"]

    elif payload.get('action') == 'closed' and payload.get('pull_request', {}).get('merged'):
        action = "merge"
        author = payload["pull_request"]["user"]["login"]
        from_branch = payload["pull_request"]["head"]["ref"]
        to_branch = payload["pull_request"]["base"]["ref"]

    else:
        return jsonify({"message": "Ignored event"}), 200

    data = {
        "action": action,
        "author": author,
        "from_branch": from_branch,
        "to_branch": to_branch,
        "timestamp": timestamp
    }
    events.insert_one(data)
    return jsonify({"message": "Event stored"}), 200

@app.route('/events', methods=['GET'])
def get_events():
    latest = list(events.find().sort("_id", -1).limit(10))
    for e in latest:
        e["_id"] = str(e["_id"])
    return jsonify(latest)

if __name__ == '__main__':
    app.run(port=5000)
