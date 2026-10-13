import os #using for reading environment variables
from datetime import date #For generate today's date

from flask import Flask, render_template, url_for #import flask for the whole system to use, render_template for 404 page, url_for for consist the image link

from models.room import seed_default_rooms, DEFAULT_IMG #From model import default rooms and image when starting
from routes.guest_routes import guest_bp #import three blueprints(guest_bp, admin_bp, api_bp)
from routes.admin_routes import admin_bp #The router is a box for collect different routes
from routes.api_routes import api_bp


def create_app(): #Using Application Factory Pattern to create the app, when testing can rebuild a new one
    app = Flask(__name__) #__name__ let flask know where the project file is, so can automatically find the templates/ and static/
    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key") #session(log in situation) is existing in cookies
    #use this secret key, others can not access admin_logged_in
    #The default value is dev-secret-key, if not set in environment variable
    app.register_blueprint(guest_bp) #Register the three blueprints
    app.register_blueprint(admin_bp, url_prefix="/admin") #admin_bp add url_prefix(/admin) at the front of the url link
    app.register_blueprint(api_bp, url_prefix="/api") #api_bp add url_prefix(/api) at the front of the url link

    # Jinja Tools（Call in template）----------

    @app.template_filter("aud") #Jinja filter-- aud
    def aud(value):
        #Format aud filter, ex: 45.0 to A$45 ; 99.5 to A$99.50
        try:
            number = float(value) #If the value is not a number, then return the value originally
        except (TypeError, ValueError):
            return value
        return f"A${number:,.0f}" if number == int(number) else f"A${number:,.2f}"
        #If the value is an integer, then it will not have a decimal point
    @app.template_filter("img_src") 
    def img_src(path):
        #Database store 'img/xxx.jpg', transfer to /static/img/xxx.jpg, if is http link then use directly
        path = path or DEFAULT_IMG #If the path is None, then use the default image
        if path.startswith(("http://", "https://")):
            return path
        return url_for("static", filename=path.lstrip("/"))

    @app.template_filter("status_class")
    def status_class(status): #Jinja filter-- status_class, transfer status to CSS class(Confirmed / Pending / Cancelled)
        if status == "Confirmed": #Compare to admin booing lists, style.css
            return "status-confirmed"
        if status == "Pending":
            return "status-pending"
        return "status-cancelled"

    @app.context_processor
    def inject_today():
        #Let the min attribute of the date input tag can block the past date, and using today as default
        return {"today": date.today().isoformat()}

    @app.errorhandler(404) #Error handler, 404 means page not found 
    def not_found(_error):
        return render_template("error.html", message="Page not found."), 404

    #Compare to server.js initializeRooms() ; If the rooms collection is empty, then insert the default rooms when starting
    try:
        seed_default_rooms()
    except Exception as exc:  # When disconnect the database, the app can still running and print the error message
        print(f"Failed to initialize rooms: {exc}")

    return app


app = create_app() #Create the app, flask run, gunicorn app will find this variable

if __name__ == "__main__": #Only use when run python app.py
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=True)
    #host="127.0.0.1": only allow local connection
    #port set the environment variable PORT, if not set, use default
    #debug=True: system using auto restart, but do not open debug mode in public server