import re #For Guest to search
from config import db
from models.utils import to_object_id

rooms_collection = db["rooms"] #Two collections: "rooms" and "bookings"
bookings_collection = db["bookings"] #Using to check Bookings and view rooms whether has active booking

ACTIVE_STATUSES = ["Pending", "Confirmed"]  # This two status are counted as "active"
DEFAULT_IMG = "img/Hotel Single Room.jpg" #If the path is None, then use the default image
#Using in admin_routes, api+routes, app.py

#6 default rooms, price using number(show A$ and /night by aud filter)
DEFAULT_ROOMS = [
    {"room_type": "Standard Single Room", "price": 45.0, "description": "Free Wi-Fi, Single Bed, Air Conditioning", "img": "img/Hotel Single Room.jpg"},
    {"room_type": "Double Room", "price": 90.0, "description": "Free Wi-Fi, Queen Bed, Breakfast included, City View", "img": "img/Double Room.jpg"},
    {"room_type": "Executive Room", "price": 120.0, "description": "Free Wi-Fi, King Bed, Ocean View, Free Parking & Breakfast", "img": "img/Excutive Room.jpg"},
    {"room_type": "Standard Single Room", "price": 45.0, "description": "Free Wi-Fi, Single Bed, Garden View", "img": "img/Single Room2.jpg"},
    {"room_type": "Double Room", "price": 90.0, "description": "Free Wi-Fi, Double Bed, Work Desk", "img": "img/Double Room2.jpg"},
    {"room_type": "Executive Room", "price": 120.0, "description": "Free Wi-Fi, King Bed, Balcony, VIP Lounge Access", "img": "img/Excutive Room2.jpg"},
]


def seed_default_rooms():
    #Compare to the initializeRooms(): if the database is empty, then insert the 6 default rooms
    if rooms_collection.count_documents({}) == 0:
        rooms_collection.insert_many([dict(r) for r in DEFAULT_ROOMS]) #dict is copy one, to avoid Pymongo write back the _id
        print("Default rooms inserted into MongoDB")
    else:
        print(f"Rooms already exist: {rooms_collection.count_documents({})}")


def get_all_rooms(): #According the _id by small to large(ObjectId has the time that build), transfer ObjectId to None when fail, view when success
    return list(rooms_collection.find().sort("_id", 1))


def get_room_by_id(room_id):
    oid = to_object_id(room_id)
    if oid is None:
        return None
    return rooms_collection.find_one({"_id": oid})


def _type_filter(room_type):
    #Room searching: Do not compare the upper and lower case, part of comparison, to avoid user enter speacial character cause error
    if room_type:
        return {"room_type": {"$regex": re.escape(room_type), "$options": "i"}}
    return {}


def get_booked_room_ids(check_in, check_out):
    #Return in the period of [check_in, check_out] that has been booked room_id collection
    return set(bookings_collection.distinct("room_id", {
        "status": {"$in": ACTIVE_STATUSES},
        "check_in": {"$lt": check_out},
        "check_out": {"$gt": check_in},
    }))


def get_rooms_with_availability(check_in=None, check_out=None, room_type=None):
    #The homepage use: return all rooms with availability, every room has an "available" field
    #If no check_in or check_out dates, then all rooms are available
    rooms = list(rooms_collection.find(_type_filter(room_type)).sort("_id", 1))
    booked = get_booked_room_ids(check_in, check_out) if (check_in and check_out) else set()
    for room in rooms:
        room["available"] = str(room["_id"]) not in booked
    return rooms


def search_available_rooms(check_in, check_out, room_type=None):
    #API use: only return the rooms that are not been booked
    return [r for r in get_rooms_with_availability(check_in, check_out, room_type) if r["available"]]


def has_conflicting_booking(room_id, check_in, check_out):
    #Check if the room has Pending/Confirmed booking in the period[check_in, check_out)]
    #The order check_in < new check_out, and check_out > new check_in
    #This is the standard "two date intervals overlap" check(date is YYYY-MM-DD string, can directly compare)
    conflict = bookings_collection.find_one({
        "room_id": room_id,
        "status": {"$in": ACTIVE_STATUSES},
        "check_in": {"$lt": check_out},
        "check_out": {"$gt": check_in},
    })
    return conflict is not None


def room_has_active_booking(room_id):
    #Check before delete rooms: if the room has active pending or confirmed, will reject delete
    return bookings_collection.find_one({
        "room_id": str(room_id), #bookings to find the room type, and the status is under active, then return True
        "status": {"$in": ACTIVE_STATUSES}, #room_is is string, booking.py is exist by str(room["_id"])
    }) is not None


def add_room(room_data):
    #insert_one will return _id in dict(pymongo common traps)
    #copy one to avoid caller room_data has been modified fields
    result = rooms_collection.insert_one(dict(room_data))
    return str(result.inserted_id)


def update_room(room_id, update_data):
    oid = to_object_id(room_id)
    if oid is not None:
        rooms_collection.update_one({"_id": oid}, {"$set": update_data})
        #$set:Only change the field that return, others will not update

def delete_room(room_id):
    oid = to_object_id(room_id)
    if oid is not None:
        rooms_collection.delete_one({"_id": oid})
