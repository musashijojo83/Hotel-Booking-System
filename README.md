# Hotel Booking System (Python / Flask version)
IFN636 Assessment - Hotel Room Booking System, converted from Node.js + Express to Python + Flask.

## Deployment URL
- **Live Demo URL:** _to be updated after EC2 deployment_
- **EC2 Instance Name/ID:** _to be updated_
- **Tagged Release:** _to be updated_

## Architecture Summary
Server-rendered web application for guests (search / book / cancel rooms) and hotel admins (manage bookings and room types).
- **Frontend:** Jinja2 templates (`templates/`) + CSS (`static/style.css`) + a tiny JS file (`static/main.js`).
- **Backend:** Python 3 + Flask, split into Blueprints: `guest_routes` (guest pages), `admin_routes` (admin pages, session login) and `api_routes` (JSON API, JWT login).
- **Database:** MongoDB Atlas via PyMongo. Collections: `rooms`, `bookings`, `admins`, `counters`.
- **Cloud Infrastructure:** AWS EC2 (Ubuntu) - deployment steps to be added in the CI/CD step.

## Project Structure
```
app.py              Flask app factory + entry point
config.py           MongoDB connection (reads .env)
models/             Database functions (room.py, booking.py, admin.py)
routes/             guest_routes.py / admin_routes.py / api_routes.py
services/           New functionality for Assessment 2 (see below)
templates/          Jinja2 HTML pages
static/             style.css, main.js, img/ (room photos)
tests/              pytest Functional Tests (uses mongomock, no real DB needed)
postman/            Postman collection + environments for API Testing
```

## Setup
Requires Python 3.10+ and a MongoDB Atlas connection string.
```bash
python -m venv venv
venv\Scripts\activate            # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env           # Windows   (Mac/Linux: cp .env.example .env)
```
Then edit `.env` and fill in `MONGO_URI`, `DB_NAME` and `SECRET_KEY`. Never commit `.env`.

## Run
```bash
python app.py
```
Open http://localhost:5000. On first start the 6 default rooms are inserted if the `rooms` collection is empty.

## Main Pages
| URL | Who | What |
|---|---|---|
| `/` | Guest | Search rooms by dates / name, book |
| `/book/<room_id>` | Guest | Booking form |
| `/my-bookings` | Guest | Find a booking by Booking ID + phone, view, cancel |
| `/admin/login`, `/admin/register` | Admin | Account access |
| `/admin/dashboard` | Admin | Counts + shortcuts |
| `/admin/bookings` | Admin | Confirm / cancel bookings |
| `/admin/rooms` | Admin | Add / edit / delete room types |
| `/api/...` | Any client | JSON API (admin endpoints need `Authorization: Bearer <token>`) |

## Functional Testing (pytest)
```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```
Tests use `mongomock` so they run without a real MongoDB connection — safe to run in CI/CD.
Covers: Factory Pattern pricing calculations, Singleton identity, Adapter channel dispatch,
and the full API flow (create booking → confirm → notification sent) with pass/fail assertions.

## API Testing (Postman)
1. Open Postman → Import → select both files in `postman/`:
   - `Hotel_Booking_System.postman_collection.json`
   - `Local.postman_environment.json` (for `python app.py` on your own machine) or
     `EC2.postman_environment.json` (edit `base_url` to your EC2 Public IP first)
2. Select the environment in the top-right dropdown.
3. Run folders top-to-bottom: **Auth → Rooms → Bookings → Pricing → Notification Settings**
   (Login saves the JWT automatically; Create Room / Create Booking save their IDs automatically
   for later requests — same pattern as Tutorial 10).
4. Each folder includes at least one deliberate error-case request (missing fields, wrong
   password, double-booking, unknown pricing type, no token) so the collection demonstrates
   both success and error-handling evidence for the rubric.

## Known Limitations
- No real payment gateway; confirmation email / SMS text is display-only.
- Admin registration is open to anyone (carried over from the original design).
- No CSRF protection on forms.
- Automated CI/CD is out of scope for this step; manual deployment to EC2.