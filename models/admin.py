from werkzeug.security import generate_password_hash, check_password_hash
#generate_password_hash: make the password an irreversible hash
#check_password_hash: verify if the password matches the hash
#werkzeug.security is the default scrypt algorithm, every time the password generated is different, so it will not result in the same hash
from config import db #Sharing one database object
from models.utils import to_object_id #The function to transfer string to ObjectId

admins_collection = db["admins"] #To access the "admins" collection, which is a MongoDB collection


def create_admin(username, password, email=None, name=None):
    hashed_password = generate_password_hash(password) #To hash the password, make it irreversible
    admin_doc = { #The document to be inserted(username, password, email, name)
        "username": username,
        "password": hashed_password,
        "email": email,
        "name": name,
    }
    result = admins_collection.insert_one(admin_doc) #Write in MongoDB
    return str(result.inserted_id) #Return the _id transfer to string


def verify_admin(username, password):
    #verify by username(preserved for old system login)
    admin = admins_collection.find_one({"username": username})
    if admin and check_password_hash(admin["password"], password):
        return admin
    return None


def verify_admin_by_email(email, password):
    #verify by email(Jinja login page and API login share this function)
    admin = admins_collection.find_one({"email": email}) #Find the records that matches the email, if not found then return None
    if admin and check_password_hash(admin["password"], password):
        return admin #Check the record and password, should be both verify then return the admin document, otherwise return None(login fail)
    return None


def get_admin_by_email(email): #Only check whether exists, verify the email is duplicate when register
    return admins_collection.find_one({"email": email})


def get_admin_by_id(admin_id): #Use to_object_id to transfer, if cannot transfer then return None
    oid = to_object_id(admin_id)
    if oid is None:
        return None
    return admins_collection.find_one({"_id": oid}) #If can transfer then return the find_one({"_id": oid})
    #Only API token_required(api_routes.py) will use
