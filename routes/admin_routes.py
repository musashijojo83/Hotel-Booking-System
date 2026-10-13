from functools import wraps #Used when creating decorators to "preserve the original function's name"

from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
#From Flask import Blueprint(routes), render_template(HTML), request(the input from the request), redirect(return 302), url_for(using endpoint to consist the link), session(every brower has one, signed login records), flash(the notification that only show for once), abort(stop immediately with error code)
from models.admin import verify_admin_by_email, create_admin, get_admin_by_email
#From models.admin import three functions(verification by email, create admin, and view by email)
from models.booking import get_all_bookings, update_booking_status, get_booking_by_id
#From models.booking import three functions(View all bookings, update booking status, and view one booking)
from models.room import ( #From models.room import seven functions(View all rooms, view one room, add, update, delete room, check whether booking is in progress, default image)
    get_all_rooms, get_room_by_id, add_room, update_room, delete_room,
    room_has_active_booking, DEFAULT_IMG,
)

admin_bp = Blueprint("admin", __name__)
#The first argument is the name of the blueprint, it will become the prefix for the URL rule
#url_for("admin.login")
#The variable name admin_bp is only Python variable

def login_required(view_func): #Receive a protect function
    #Only when login route can see, if no login then redirect
    @wraps(view_func) #Using this decorator to inherit the original function name, if not, the protect function name will be wrapper
    def wrapper(*args, **kwargs): #*args, **kwargs will transfer the url parameters to original function
        if not session.get("admin_logged_in"):#If no login, will not see this key, return None, then not None will build
            flash("Please log in first.", "error") #Flash an error message and redirect to login page
            return redirect(url_for("admin.login"))
        return view_func(*args, **kwargs)#If login, return the original function and return the results
    return wrapper#Decorator return the new function(after wrapping)


#Login
@admin_bp.route("/login", methods=["GET", "POST"]) #Process GET(show form) and POST(send form)
def login(): #login is endpoint name(The complete name is "admin.login"), url_for use to find this function
    if request.method == "POST": #Only when submit the form can verify
        email = request.form.get("email", "").strip() #read name="email" value in HTML, no then using empty string, .strip() remove space at the front and back
        password = request.form.get("password", "") #no .strip() cause space can also be a part of password
        admin = verify_admin_by_email(email, password) #call verify_admin_by_email, get admin document when success, None when fail
        if admin: #verify success
            session.clear()  # using clear session when login to avoid old records remain
            session["admin_logged_in"] = True #This is the key of "Already logged in"
            session["admin_name"] = admin.get("name") or email #If no name, then using email
            return redirect(url_for("admin.dashboard")) #Redirect to Admin Dashboard
        flash("Invalid email or password.", "error") #Verify fail(Whether using email or password)
    return render_template("admin_login.html") #GET or verify fail then return login page HTML

#Logout
@admin_bp.route("/logout") #This route did not write methods, so using GET, is only a link
def logout():
    session.clear() #Clear all the login records
    flash("You have been logged out.", "success") #Flash a success message
    return redirect(url_for("admin.login")) #Redirect to login page

#Register
@admin_bp.route("/register", methods=["GET", "POST"])#Process GET(show form) and POST(send form
def register():
    if request.method == "POST": #read for three required fields(name, email, password)
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not name or not email or not password: #If any field is empty, then flash an error, and direct to register page 
            flash("Name, email and password are required.", "error")#Using redirect not render because do not duplicate sending when reload page
            return redirect(url_for("admin.register"))
        if get_admin_by_email(email): #If the email is already registered, then flash an error message
            flash("This email is already registered.", "error")
            return redirect(url_for("admin.register"))
        #username field using email, to share the same admin records in API login and web login
        create_admin(username=email, password=password, email=email, name=name)
        flash("Account created successfully! Please log in.", "success")#Flash a success message
        return redirect(url_for("admin.login")) #Redirect to login page
    return render_template("admin_register.html") #GET to show register form


#Dashboard
@admin_bp.route("/dashboard") #Decorator should wrap from down to top, or it will not protect the original function, no login can also view the content
@login_required
def dashboard():
    bookings = get_all_bookings() #get all bookings(list, every booking is a dict)
    #Remove the situation that "Cancelled by Guest" , so it will not count in the total number of Booking in Dashboard
    booking_count = len([b for b in bookings if b["status"] != "Cancelled by Guest"])
    room_count = len(get_all_rooms()) #The number of room types
    return render_template("admin_dashboard.html", booking_count=booking_count, room_count=room_count)
    #The name in the left side is the name of the variable, it should be same as the admin_dashboard.html, {{booking_count}} and {{room_count}}

#Booking Management
@admin_bp.route("/bookings")
@login_required
def manage_bookings(): #View all bookings, using bookings to send to admin_bookings.html
    return render_template("admin_bookings.html", bookings=get_all_bookings())

#Confirm booking
@admin_bp.route("/bookings/<booking_id>/confirm", methods=["POST"]) #Only accept POST, paste the link will be GET and receive(405)
@login_required
def confirm_booking(booking_id): #booking_id is the variable of the link, Flask will seen as string to send to same parameter
    booking = get_booking_by_id(booking_id)
    if not booking: #using id to view booking, if no booking, then return abort(404)
        abort(404)
    if booking["status"] != "Pending": #Only Pending status can check, otherwise will flash error message
        flash("Only pending bookings can be confirmed.", "error")
    else: #Change the database, and trigger notification(models/booking.py and services/notification_config.py)
        update_booking_status(booking_id, "Confirmed")
        flash(f"Booking BK-{booking['booking_no']} confirmed.", "success") #BK-{booking['booking_no']} is the number of booking that shown
    return redirect(url_for("admin.manage_bookings")) #Redirect to booking management page whether success or fail

#Cancel booking
@admin_bp.route("/bookings/<booking_id>/cancel", methods=["POST"]) #Only accept POST, paste the link will be GET and receive(405)
@login_required
def admin_cancel_booking(booking_id):#booking_id is the variable of the link, Flask will seen as string to send to same parameter
    booking = get_booking_by_id(booking_id)
    if not booking:#using id to view booking, if no booking, then return abort(404)
        abort(404)
    if booking["status"] not in ("Pending", "Confirmed"): #Only not in Pending or confirmed status can check, otherwise will flash error message
        flash("This booking is already cancelled.", "error")
    else: #Change the database and status to Cancelled
        update_booking_status(booking_id, "Cancelled by Admin")
        flash(f"Booking BK-{booking['booking_no']} cancelled.", "success")#BK-{booking['booking_no']} is the number of booking that shown
    return redirect(url_for("admin.manage_bookings"))#Redirect to booking management page whether success or fail

# Room Types Management
def _read_room_form(): #Using _ is dedicate as the tools by itself, add and edit should read the same field and validate, so create a function to avoid rewrite
    #Read the form and validate, return room_data and error message
    room_type = request.form.get("room_type", "").strip() #read room_type and price, price are still a string now
    price_raw = request.form.get("price", "").strip()
    if not room_type or not price_raw: #If the one is empty, return None
        return None, "Room name and price are required."
    try:
        price = float(price_raw) #If cannot convert to float, will send to ValueError, and accept by except, return error message
    except ValueError:
        return None, "Price must be a number, e.g. 150."
    if price <= 0: #The price should be greater than 0
        return None, "Price must be greater than 0."
    return { #If pass the validation, return the dict,None
        "room_type": room_type,
        "price": price,
        "description": request.form.get("description", "").strip(), #description will remove the space at the front and back
        "img": request.form.get("img", "").strip() or DEFAULT_IMG, #Image will use the default image if is not fill
    }, None

#View all room types
@admin_bp.route("/rooms") 
@login_required
def manage_rooms(): 
    return render_template("admin_rooms.html", rooms=get_all_rooms())#using rooms to send to admin_rooms.html

#Add new room types
@admin_bp.route("/rooms/new", methods=["GET", "POST"]) 
@login_required
def new_room():
    if request.method == "POST": #POST: call _read_room_form to get room_data, error
        room_data, error = _read_room_form()
        if error: #If error, flash error message and render_template 400
            flash(error, "error") #Send request.form back, user do not need to fill again 
            return render_template("admin_room_form.html", room=request.form, is_edit=False), 400 #400 is HTTP status code
        add_room(room_data) #If correct, add_room(room_data) write in database
        flash("Room type added.", "success") #flash success message
        return redirect(url_for("admin.manage_rooms")) #Redirect to manage room type list page
    return render_template("admin_room_form.html", room={}, is_edit=False)
    #GET: room{}, let the room.get('room_type', '') get empty string, is_edit=False let it know is new add

#Edit room types
@admin_bp.route("/rooms/<room_id>/edit", methods=["GET", "POST"])
@login_required
def edit_room(room_id):
    room = get_room_by_id(room_id)
    if not room: #View room type and if is error, abort 404
        abort(404)
    if request.method == "POST": #POST: read the form and validate
        room_data, error = _read_room_form()
        if error: #If error, return to room{**request.form, '_id': room['_id']}
            flash(error, "error")
            return render_template( #need the room['_id'] is because should consist the action link
                "admin_room_form.html", room={**request.form, "_id": room["_id"]}, is_edit=True
            ), 400
        update_room(room_id, room_data) #success then using set to update, and flash the message and redirect
        flash("Room type updated.", "success")
        return redirect(url_for("admin.manage_rooms"))
    return render_template("admin_room_form.html", room=room, is_edit=True)
    #GET: The document of the room types return back, is_edit=True

#Delete room types
@admin_bp.route("/rooms/<room_id>/delete", methods=["POST"]) #Only accept POST
@login_required #Using route in the name is because to avoid the same name in models.room delete_room and be covered by it
def delete_room_route(room_id):
    if not get_room_by_id(room_id): #If not found, then return 404
        abort(404)
    if room_has_active_booking(room_id): #If the room has active pending or confirmed, will reject delete
        flash("Cannot delete a room type with active bookings.", "error")
    else:
        delete_room(room_id) #Otherwise, will show success and delete
        flash("Room type deleted.", "success")
    return redirect(url_for("admin.manage_rooms")) #Redirect to manage room type list
