import os # noqa

from pymongo import MongoClient # noqa

from pdstelegrambot.settings.base import *  # noqa

DEBUG = True

ALLOWED_HOSTS.append("pdstelegrambot.herokuapp.com")

mongodb_user = os.getenv("MONGO_USER")
mongodb_password = os.getenv("MONGO_PASSWORD")
mongodb_host = os.getenv("MONGO_HOST")
MONGO_CLIENT = MongoClient(
    f"mongodb://{mongodb_user}:{mongodb_password}@{mongodb_host}?ssl=true&ssl_cert_reqs=CERT_NONE"
)
MONGO_DB = MONGO_CLIENT.pdstelegrambot
