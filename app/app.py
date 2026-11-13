import os
from datetime import datetime
from urllib.parse import quote_plus

from flask import Flask, request, jsonify
from pymongo import MongoClient
from pymongo.errors import PyMongoError

app = Flask(__name__)


def build_mongo_uri():
    
    uri = os.environ.get("MONGODB_URI")
    if uri:
        return uri

    username = os.environ.get("MONGODB_USERNAME")
    password = os.environ.get("MONGODB_PASSWORD")
    host = os.environ.get("MONGODB_HOST", "localhost")
    port = os.environ.get("MONGODB_PORT", "27017")

    if username and password:
        
        return (
            f"mongodb://{quote_plus(username)}:{quote_plus(password)}"
            f"@{host}:{port}/?authSource=admin"
        )
    return f"mongodb://{host}:{port}/"


client = MongoClient(build_mongo_uri(), serverSelectionTimeoutMS=5000)
db = client.flask_db
collection = db.data


@app.route("/")
def index():
    return f"Welcome to the Flask app! The current time is: {datetime.now()}"


@app.route("/data", methods=["GET", "POST"])
def data():
    try:
        if request.method == "POST":
            payload = request.get_json(silent=True)
            if not isinstance(payload, dict) or not payload:
                return jsonify({"error": "Send a non-empty JSON object"}), 400
            collection.insert_one(payload)
            return jsonify({"status": "Data inserted"}), 201

        documents = list(collection.find({}, {"_id": 0}))
        return jsonify(documents), 200
    except PyMongoError as exc:
        return jsonify({"error": "Database error", "detail": str(exc)}), 503


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
