import os #Read environment variables
from dotenv import load_dotenv #Read .env file
from pymongo import MongoClient #MongoClient is a class that PyMongo uses to connect to MongoDB

# Read .env file and environment variables(MONGO_URI, DB_NAME)
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI") #If no setting, return None back
DB_NAME = os.getenv("DB_NAME", "hotel_booking_python") #If no setting, return "hotel_booking_python" back

#If MONGO_URI pymongo is None, will link to localhost, and return over time
#It is hard to see that .env is not set, so here directly report an error
if not MONGO_URI:
    raise RuntimeError(
        "MONGO_URI is not set. Copy .env.example to .env and fill in your MongoDB connection string."
    )

#Whole app sharing one MongoClient, do not reconnect every request
#serverSelectionTimeoutMS: If cannot connect to database within 5 seconds, report an error, and do not wait for 30 seconds
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
#Whole app using models from config import db, python will only be load in for once, so the whole system share one db
#This is why tests/conftest.py can change config.db to mongomock before import
