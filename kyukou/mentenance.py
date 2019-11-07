
from db import get_collection
from bson import ObjectId

lectures = get_collection('lectures')


object_id = "5dad557d9602fe4cba91dcfe"
class_nums = ["21016229"]


lectures.update({"_id": ObjectId(object_id)}, {"$set": {"class_nums": class_nums}})
