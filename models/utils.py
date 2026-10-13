from bson.objectid import ObjectId #from bson(PyMongo) import ObjectId(_id class in MongoDB) and InvalidId(error message when the format is wrong)
from bson.errors import InvalidId


def to_object_id(value):
    #Transfer string to ObjectId, if the format is wrong, return None, avoid 500 error
    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None
