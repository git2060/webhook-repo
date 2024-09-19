from flask_pymongo import PyMongo
from flask import Flask


# Setup MongoDB here
# mongo = PyMongo(uri="mongodb://localhost:27017/db-gihub")
def connect():
    app=Flask(__name__)
    app.config["MONGO_URI"] = "mongodb://localhost:27017/db-events"
    # Initialize PyMongo
    mongo = PyMongo(app)
    return mongo


