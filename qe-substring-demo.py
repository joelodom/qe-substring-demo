#
# https://chatgpt.com/c/68701de3-a0a0-8004-bc96-4e3bf23c2801 is my scratchpad
#

from pymongo import MongoClient

# 1. Connect to local MongoDB
client = MongoClient("mongodb://localhost:27017/")

# 2. Select (or create) a database and collection
db = client["demo_db"]
collection = db["people"]

# 3. Insert a document with a string field
person = {"name": "Alice", "age": 30}
insert_result = collection.insert_one(person)
print(f"Inserted document _id: {insert_result.inserted_id}")

# 4. Query the collection by that string field
query = {"name": "Alice"}
found = collection.find_one(query)

if found:
    print("Found document:")
    print(found)
else:
    print("No document found with that name.")
