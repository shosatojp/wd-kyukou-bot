from pprint import pprint
from pymongo import MongoClient
import datetime


class Db:
    @classmethod
    def init(cls, url):
        cls._client = MongoClient(url)
        print(f'Connected to DB: "{url}"')
        cls._db = cls._client.kyukou
        cls._users = cls._db.users
        cls._lectures = cls._db.lectures

        print(f'----------------------------')
        print(f'Number of Users: {cls._users.count()}')
        print(f'----------------------------')

    @classmethod
    def get_users_db(cls):
        return cls._users

    @classmethod
    def get_lectures_db(cls):
        return cls._lectures
