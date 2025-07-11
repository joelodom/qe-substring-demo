#
# https://chatgpt.com/c/68701de3-a0a0-8004-bc96-4e3bf23c2801 is my scratchpad
#

from pymongo.encryption_options import AutoEncryptionOpts
from pymongo import MongoClient
import os
from pymongo.encryption import ClientEncryption
from bson.codec_options import CodecOptions
from bson.binary import STANDARD
import random
import sys
from datetime import datetime
from pprint import pprint

KEY_PROVIDER = "local"

MONGO_URI = "mongodb://localhost:27017/"

KEY_VAULT_DB = "encryption"
KEY_VAULT_COLL = "__keyVault"
KEY_VAULT_NAMESPACE = f"{KEY_VAULT_DB}.{KEY_VAULT_COLL}"

DB_NAME = "medicalRecords"
COLL_NAME = "patients"

# 96 random hardcoded bytes, because it's only an example
MASTER_KEY = "V2hlbiB0aGUgY2F0J3MgYXdheSwgdGhlIG1pY2Ugd2lsbCBwbGF5LCBidXQgd2hlbiB0aGUgZG9nIGlzIGFyb3VuZCwgdGhlIGNhdCBiZWNvbWVzIGEgbmluamEuLi4u"

KMS_CREDS = {
    "local": {
        "key": MASTER_KEY
    },
}

CRYPT_SHARED_LIB = "/Users/joel.odom/mongo_crypt_shared_v1-8.2.0-alpha-2632-g9217e56/lib/mongo_crypt_v1.dylib"
os.environ["MONGOCRYPT_SHARED_LIB_PATH"] = CRYPT_SHARED_LIB

AUTO_ENCRYPTION_OPTS = AutoEncryptionOpts(
    KMS_CREDS,
    KEY_VAULT_NAMESPACE,
    crypt_shared_lib_path=CRYPT_SHARED_LIB
)

ENCRYPTED_CLIENT = MongoClient(
    MONGO_URI, auto_encryption_opts=AUTO_ENCRYPTION_OPTS)

if "--destroy-database" in sys.argv:
    print("Destroying database...")
    print()
    ENCRYPTED_CLIENT.drop_database(DB_NAME)
    # This SHOULD drop the key vault here, but it doesn't matter for demo
    exit()

ENCRYPTED_FIELDS_MAP = {
    "fields": [
        {
            "path": "patientRecord.ssn",
            "bsonType": "string",
            "queries": [ {"queryType": "equality"} ]  # equality queryable
        },
        {
            "path": "patientRecord.billing",   # encrypted, not queryable
            "bsonType": "object",
        },
        {
            "path": "patientRecord.dob",
            "bsonType": "date",
            "queries": [ {
                "queryType": "range",  # range queryable
                "min": datetime(1900, 1, 1),
                "max": datetime(2099, 12, 31)
            } ]
        },
        {
            "path": "patientNotes",
            "bsonType": "string",
            "queries": [ {
                "queryType": "substringPreview",
                "strMinQueryLength": 3,
                "strMaxQueryLength": 8,
                "caseSensitive": False,
                "diacriticSensitive": False,
                "strMaxLength": 60
            } ]
        },
    ]
}

CLIENT_ENCRYPTION = ClientEncryption(
    kms_providers=KMS_CREDS,
    key_vault_namespace=KEY_VAULT_NAMESPACE,
    key_vault_client=ENCRYPTED_CLIENT,
    codec_options=CodecOptions(uuid_representation=STANDARD)
)

MASTER_KEY_CREDS = {}  # no creds because using a local key CMK

if "--create-collection" in sys.argv:
    print("Creating collection...")
    CLIENT_ENCRYPTION.create_encrypted_collection(
        ENCRYPTED_CLIENT[DB_NAME],
        COLL_NAME,
        ENCRYPTED_FIELDS_MAP,
        KEY_PROVIDER,
        MASTER_KEY_CREDS,
    )

#
# Insert random records
#

RECORDS_TO_INSERT = 100

encrypted_collection = ENCRYPTED_CLIENT[DB_NAME][COLL_NAME]
docs = []

for i in range(0, RECORDS_TO_INSERT):
    SSN = f"{random.randint(0, 999999999):09d}"
    CARD_NUMBER = f"4{random.randint(0, 999999999999999):09d}"

    YEAR = random.randint(1900, 2099)
    MONTH = random.randint(1, 12)
    DAY = random.randint(1, 28)

    PATIENT_DOC = {
        "patientName": "Jon Doe",
        "patientId": 12345678,
        "patientRecord": {
            "ssn": SSN,
            "billing": {
                "type": "Visa",
                "number": CARD_NUMBER
            },
            "dob": datetime(YEAR, MONTH, DAY)
        },
        "patientNotes": f"These are notes for patient with SSN {SSN}."
    }

    docs.append(PATIENT_DOC)

result = encrypted_collection.insert_many(docs)
#print(f"{len(docs)} records inserted: {result.inserted_ids}")
print(f"{len(docs)} records inserted.")
print()


#
# Equalty query
#

print(f"Looking for one record with SSN {SSN}.")

QUERY = { "patientRecord.ssn": SSN }

find_result = encrypted_collection.find_one(
    QUERY,
    projection={"__safeContent__": 0, "_id": 0}
)

pprint(find_result)
print()

#
# Range query
#

print(f"Looking for one record with DOB in the year {YEAR}.")

QUERY = {
    "patientRecord.dob": {
        "$gte": datetime(YEAR, 1, 1),
        "$lte": datetime(YEAR, 12, 31)
    }
}

find_result = encrypted_collection.find_one(
    QUERY,
    projection={"__safeContent__": 0, "_id": 0}
)

pprint(find_result)
print()

#
# Substring search
#

PARTIAL_SSN = SSN[-4:]
print(f"Looking records with partial SSN matching {PARTIAL_SSN} in notes.")


PIPELINE = [
    {
        "$match": {
            "$expr": {
                "$encStrContains": {
                    "input": "$patientNotes",
                    "substring": PARTIAL_SSN
                }
            }
        }
    },
    {
        "$project": { "__safeContent__": 0, "_id": 0 }
    }
]

cursor = encrypted_collection.aggregate(PIPELINE)

for doc in cursor:
    pprint(doc)
