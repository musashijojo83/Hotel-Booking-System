from datetime import datetime, date, timezone
from pymongo import ReturnDocument
from config import db
from models.utils import to_object_id
from models.room import get_room_by_id, has_conflicting_booking
from services.pricing import calculate_total_price, DEFAULT_PRICING_RULE
from services.notification_channels import NotificationService #models relies services layer, that is the reason why update_booking_status can send the notification directly

bookings_collection = db["bookings"] #Two collections: "rooms" and "bookings"
counters_collection = db["counters"]

ACTIVE_STATUSES = ["Pending", "Confirmed"]


#Validate by dates
def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def validate_dates(check_in, check_out):
    #Check if the check_in and check_out dates are valid
    #If error, return the error message
    if not check_in or not check_out:
        return "Please select both Check-in and Check-out dates."
    start, end = _parse_date(check_in), _parse_date(check_out)
    if start is None or end is None:
        return "Invalid date format."
    if start < date.today():
        return "Check-in date cannot be in the past."
    if end <= start:
        return "Check-out date must be later than Check-in date."
    return None


def count_nights(check_in, check_out):
    return (_parse_date(check_out) - _parse_date(check_in)).days


#Booking ID number
def _next_booking_no():
    #Compare to the original BK-1、BK-2...
    #Use counters collection {_id=booking_no} document automatically +1{$inc:{seq:1}}
    #Two people can't get the same number
    doc = counters_collection.find_one_and_update(
        {"_id": "booking_no"},
        {"$inc": {"seq": 1}},
        upsert=True, #If not exist, create
        return_document=ReturnDocument.AFTER, #Return the updated value
    )
    return doc["seq"]


#Build a new booking
def create_booking(booking_data):
    booking_data = dict(booking_data)
    booking_data["booking_no"] = _next_booking_no()
    booking_data["status"] = "Pending" #Default status as Pending(Admin can see the booking as Pending at first)
    booking_data["created_at"] = datetime.now(timezone.utc) #Write in the timezone that it build
    result = bookings_collection.insert_one(booking_data)
    return str(result.inserted_id)


def book_room(room_id, guest_name, guest_email, guest_phone, check_in, check_out,
              pricing_type=DEFAULT_PRICING_RULE):
    #The whole process of booking by Guest(web form or API shared)
    #The request fill in field: dates, check the existing room, check the date conflict, apply the pricing rule, write in
    #return (booking_id, error_message)
    #If success, error_message is None
    #pricing_type: "standard" / "weekend" / "long_stay"(see services/pricing.py)
    if not all([guest_name, guest_email, guest_phone]):
        return None, "Please fill in the completed booking information!"

    error = validate_dates(check_in, check_out)
    if error:
        return None, error

    room = get_room_by_id(room_id)
    if not room:
        return None, "Room not found."

    if has_conflicting_booking(str(room["_id"]), check_in, check_out):
        return None, "This room is already booked for the selected dates!"

    nights = count_nights(check_in, check_out)

    #Factory Pattern： According to the pricing_type, use the corresponding pricing rule(see services/pricing.py)
    try:
        total_price = calculate_total_price(room["price"], nights, pricing_type)
    except ValueError as exc:
        return None, str(exc)

    booking_id = create_booking({
        "room_id": str(room["_id"]),
        #Room types, prices, and images are stored immediately, if the room type is changed or deleted, the order content before will not change
        "room_type": room["room_type"],
        "price": room["price"],
        "img": room.get("img"),
        "guest_name": guest_name.strip(),
        "guest_email": guest_email.strip(),
        "guest_phone": guest_phone.strip(),
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "pricing_type": pricing_type,
        "total_price": total_price,
    })
    return booking_id, None


#View all bookings
def get_booking_by_id(booking_id):
    oid = to_object_id(booking_id)
    if oid is None:
        return None
    return bookings_collection.find_one({"_id": oid})

#View all bookings by same room type
def get_booking_by_no_and_phone(booking_no, phone):
    #Guest check their own booking: Booking ID（BK-12 or 12 is ok）+ phone number
    #Two conditions must match
    cleaned = str(booking_no).strip().upper().replace("BK-", "")
    if not cleaned.isdigit():
        return None
    return bookings_collection.find_one({
        "booking_no": int(cleaned),
        "guest_phone": str(phone).strip(),
    })


def get_bookings_by_guest(email, phone):
    #API use: email + phone, two conditions must match, to avoid open others' bookings
    return list(bookings_collection.find({
        "guest_email": email,
        "guest_phone": phone,
    }))


#According the _id by small to large
def get_all_bookings():
    return list(bookings_collection.find().sort("booking_no", 1))


#Upate booking status
def update_booking_status(booking_id, new_status, notify=True):
    #Update booking status, and notify Guest by NotificationService(By default)
    #notify=False preserved for test or batch job, to avoid triggering notification when testing
    oid = to_object_id(booking_id)
    if oid is None: #Transfer to ObjectId, if fail, end
        return

    bookings_collection.update_one({"_id": oid}, {"$set": {"status": new_status}})
    #update_one: status change to new_status
    if notify:
        booking = bookings_collection.find_one({"_id": oid})
        if booking: #notify is True(default), read the booking, then NotificationService().notify_status_change(booking, new_status)
            NotificationService().notify_status_change(booking, new_status)
        #Every time the status change, the notification will be sent(Admin confirm, Admin cancel, Guest cancel)
        

def cancel_booking(booking_id, cancelled_by="Guest"): #The string shows depends on cancelled by whom
    new_status = "Cancelled by Guest" if cancelled_by == "Guest" else "Cancelled by Admin"
    update_booking_status(booking_id, new_status)
    #Only API(api_routes.py) and Guest(guest_routes.py) will use
    #Admin(admin_routes.py) will directly call update_booking_status