import os
from flask import Flask
import pymongo

from dotenv import load_dotenv 

load_dotenv()

# MongoDB URI from environment variable
db_url = os.getenv('MONGO_URI')

# Connect to MongoDB
client = pymongo.MongoClient(db_url)

# Access the database
db = client['user_db']

# Access the 'products' database
product_db = client['products_db']

