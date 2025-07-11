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

# CRYPT_SHARED_LIB = "/Users/joel.odom/mongo-crypt-8.1.0/lib/mongo_crypt_v1.dylib"

AUTO_ENCRYPTION_OPTS = AutoEncryptionOpts(
    KMS_CREDS,
    KEY_VAULT_NAMESPACE,
    # crypt_shared_lib_path=CRYPT_SHARED_LIB
)

ENCRYPTED_CLIENT = MongoClient(
    MONGO_URI, auto_encryption_opts=AUTO_ENCRYPTION_OPTS)

ENCRYPTED_FIELDS_MAP = {
    "fields": [
        {
            "path": "patientRecord.ssn",
            "bsonType": "string",
            "queries": [{"queryType": "equality"}] # queryable
        },
        {
            "path": "patientRecord.billing", # encrypted, not queryable
            "bsonType": "object",
        }
    ]
}

CLIENT_ENCRYPTION = ClientEncryption(
    kms_providers=KMS_CREDS,
    key_vault_namespace=KEY_VAULT_NAMESPACE,
    key_vault_client=ENCRYPTED_CLIENT,
    codec_options=CodecOptions(uuid_representation=STANDARD)
)

MASTER_KEY_CREDS = {} # no creds because using a local key CMK

if "--create-collection" in sys.argv:
    print("Creating collection...")
    CLIENT_ENCRYPTION.create_encrypted_collection(
        ENCRYPTED_CLIENT[DB_NAME],
        COLL_NAME,
        ENCRYPTED_FIELDS_MAP,
        KEY_PROVIDER,
        MASTER_KEY_CREDS,
    )

# At this point in working through the quick start to build this code, I could
# see the new encrypted collection in Atlas. w00t!
#
# But....  I can't run it twice without getting an exception, so commenting it out for now.
#

SECRET_SSN = f"{random.randint(0, 999999999):09d}"

PATIENT_DOC = {
    "patientName": "Jon Doe",
    "patientId": 12345678,
    "patientRecord": {
        "ssn": SECRET_SSN,
        "billing": {
            "type": "Visa",
            "number": "4111111111111111",
        },
    },
}

encrypted_collection = ENCRYPTED_CLIENT[DB_NAME][COLL_NAME]
result = encrypted_collection.insert_one(PATIENT_DOC)
print(f"One record inserted: {result.inserted_id}")
print()

# At this point in working through the quick start, I can see reconds appear

find_result = encrypted_collection.find_one({
    "patientRecord.ssn": SECRET_SSN
})

print(find_result)
print()
