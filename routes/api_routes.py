import os #read SECRET_KEY
import jwt #PyJWT set, signature and verification token
from datetime import datetime, timedelta, timezone #calculation token time expiration
from functools import wraps
from flask import Blueprint, request, jsonify #jsonify convert dict to json

from models.admin import create_admin, verify_admin_by_email, get_admin_by_email, get_admin_by_id
from models.room import (
    get_all_rooms, get_room_by_id, search_available_rooms,
    add_room, update_room, delete_room, room_has_active_booking, DEFAULT_IMG,
)
from models.booking import (
    book_room, get_booking_by_id, get_bookings_by_guest,
    get_all_bookings, update_booking_status, cancel_booking,
)

api_bp = Blueprint("api", __name__) #name "api", apply.py add /api prefix


#JWT Tools Functions
def generate_token(admin_id):
    #signed token, payload contains admin_id and expiration(Now+24h)
    #exp is the standard field of JWT, functions will be automatically expired
    #after expiration, jwt.decode will automatically throw ExpiredSignatureError
    payload = {
        "admin_id": admin_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key") #The key used to read, same as the key used in session(SECRET_KEY)
    return jwt.encode(payload, secret_key, algorithm="HS256") #Signed token String


def decode_token(token): #Validate signed and expiration time, if one is invalid, will throw exception
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key")
    return jwt.decode(token, secret_key, algorithms=["HS256"])


def token_required(view_func):
    #Middleware: use in login API route
    #Check Authorization: Bearer <token> header, pass if valid
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "") #read Authorization header, if none, return ""
        if not auth_header.startswith("Bearer "): #Should start with "Bearer "
            return jsonify({"message": "Missing or invalid Authorization header"}), 401
            #Or then return 401 Json
        token = auth_header.split(" ", 1)[1] #Access the token after space
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError: #If token is expired, back 401
            return jsonify({"message": "Token expired"}), 401
        except jwt.InvalidTokenError: #Other invalid token, back 401
            return jsonify({"message": "Invalid token"}), 401

        admin = get_admin_by_id(payload.get("admin_id")) #use admin_id in the token to find 
        if not admin: #If not found, such as account been deleted, back 401
            return jsonify({"message": "Admin not found"}), 401

        request.current_admin = admin #Admin document will be stored in request
        return view_func(*args, **kwargs) #The function that been protect use profile()
    return wrapper #Pass then use the original function

#Auth Register
@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {} #silent=True means if the request from Json is not valid, return None, and or{] will be empty dict
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    #Access three fields
    if not all([name, email, password]): #If any field is empty, back 400
        return jsonify({"message": "name, email and password are required"}), 400
    if get_admin_by_email(email): #If the email is already registered, back 409
        return jsonify({"message": "User already exists"}), 409

    #Create
    admin_id = create_admin(username=email, password=password, email=email, name=name)
    return jsonify({"id": admin_id, "name": name, "email": email, "token": generate_token(admin_id)}), 201
    #Return 201, the content include id, name, email and token(did not send password)

#Auth Login
@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    admin = verify_admin_by_email(data.get("email"), data.get("password"))
    if not admin: #If verify fail, back 401
        return jsonify({"message": "Invalid email or password"}), 401

    return jsonify({ #Return 200 and token, if success
        "id": str(admin["_id"]),
        "name": admin.get("name"),
        "email": admin.get("email"),
        "token": generate_token(str(admin["_id"])),
    }), 200 #Postman login request will store the token to variable to give the back request use

#Auth Profile
@api_bp.route("/auth/profile", methods=["GET"])
@token_required
def profile(): #needs token, return current admin id, name, email that login
    admin = request.current_admin
    return jsonify({"id": str(admin["_id"]), "name": admin.get("name"), "email": admin.get("email")}), 200


#Room list
@api_bp.route("/rooms", methods=["GET"])
def list_rooms():
    #Public, no need to login(Guest can also use to check rooms)
    #If check_in/check_out, return available rooms
    #If not, return all rooms
    check_in = request.args.get("check_in")
    check_out = request.args.get("check_out")
    room_type = request.args.get("room_type")

    if check_in and check_out:
        rooms = search_available_rooms(check_in, check_out, room_type)
    else:
        rooms = get_all_rooms()
    return jsonify([serialize_room(r) for r in rooms]), 200
    #Use serialize_room() to format the room to Json format

#Room create
@api_bp.route("/rooms", methods=["POST"])
@token_required
def create_room(): #need token, access room_type and price
    data = request.get_json(silent=True) or {}
    room_type, price = data.get("room_type"), data.get("price")

    if not room_type or price is None: #If non, back 400(price is None means if fill in price is 0, will not be represented as no fill)
        return jsonify({"message": "room_type and price are required"}), 400
    try:
        price = float(price)
    except (TypeError, ValueError): #If fail, back 400
        return jsonify({"message": "price must be a number"}), 400

    room_data = { #consist the data
        "room_type": room_type,
        "price": price,
        "description": data.get("description", ""),
        "img": data.get("img") or DEFAULT_IMG,
    }
    room_id = add_room(room_data) #write in database
    return jsonify({"id": room_id, **room_data}), 201 #Return 201, the content include id, room_type, price, description and img

#Room update
@api_bp.route("/rooms/<room_id>", methods=["PUT"]) #PUT can update only some fields, otherwise will use the old one
@token_required
def update_room_api(room_id): #name add _api is because the same name will not covered 
    data = request.get_json(silent=True) or {}
    room = get_room_by_id(room_id)
    if not room: #If not found, back 404
        return jsonify({"message": "Room not found"}), 404

    try:
        price = float(data.get("price", room.get("price")))
    except (TypeError, ValueError): #If fail, back 400
        return jsonify({"message": "price must be a number"}), 400

    update_data = {
        "room_type": data.get("room_type", room.get("room_type")), #If not fill in, use the old one
        "price": price,
        "description": data.get("description", room.get("description")),
        "img": data.get("img", room.get("img")),
    }
    update_room(room_id, update_data) #write in database
    return jsonify({"id": room_id, **update_data}), 200 #Return 200, the content include id, room_type, price, description and img

#Room delete
@api_bp.route("/rooms/<room_id>", methods=["DELETE"]) #DELETE method 
@token_required
def delete_room_api(room_id):
    if not get_room_by_id(room_id): #If not found, back 404
        return jsonify({"message": "Room not found"}), 404
    if room_has_active_booking(room_id): #If the room has active pending or confirmed, back 409
        return jsonify({"message": "Cannot delete a room type with active bookings"}), 409

    delete_room(room_id) #write in database
    return jsonify({"message": "Room deleted"}), 200 #Return 200


#Bookings
@api_bp.route("/bookings", methods=["GET"])
@token_required
def list_bookings():
    #need token, Admin use: return all bookings
    return jsonify([serialize_booking(b) for b in get_all_bookings()]), 200

@api_bp.route("/bookings/<booking_id>/confirm", methods=["PUT"])
@token_required
def confirm_booking_api(booking_id): #When found the booking, change the status as Confirmed(trigger notification)
    if not get_booking_by_id(booking_id): #If not found, back 404
        return jsonify({"message": "Booking not found"}), 404
    update_booking_status(booking_id, "Confirmed") #write in database
    return jsonify(serialize_booking(get_booking_by_id(booking_id))), 200 #Return 200


@api_bp.route("/bookings/<booking_id>/cancel", methods=["PUT"])
def cancel_booking_api(booking_id):
    #Guest and Admin use: using the cancelled_by in body to distinguish
    #Are not required to login(compare to the design of Guest can cancel booking without login)
    if not get_booking_by_id(booking_id):
        return jsonify({"message": "Booking not found"}), 404
    data = request.get_json(silent=True) or {}
    cancel_booking(booking_id, cancelled_by=data.get("cancelled_by", "Guest"))
    return jsonify(serialize_booking(get_booking_by_id(booking_id))), 200

#Serialization tool: Convert MongoDB ObjectId/datetime to a string; otherwise, jsonify will throw errors
def serialize_room(room): #MongoDB id is ObjectId, transfer it to string
    room = dict(room) #copy first, to avoid rewrite the old data
    room["_id"] = str(room["_id"])
    return room


def serialize_booking(booking): #MongoDB created_at is datetime, transfer it to string
    booking = dict(booking)
    booking["_id"] = str(booking["_id"])
    if "created_at" in booking:
        booking["created_at"] = booking["created_at"].isoformat()
    return booking
