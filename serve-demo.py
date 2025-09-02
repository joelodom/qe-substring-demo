import os
import json
from flask import Flask, request, send_from_directory, redirect, url_for, jsonify, abort
from pymongo import MongoClient
from datetime import datetime
from pymongo.encryption_options import AutoEncryptionOpts
from pymongo.encryption import ClientEncryption
from bson.codec_options import CodecOptions
from bson.binary import STANDARD
from faker import Faker
import random

#
# Configuration
#

PORT = 3141
SAMPLE_FILE = 'sample-data.json'

MONGO_URI = 'mongodb://localhost:27017/'

DB = 'substringHospital'
COLLECTION = 'patients'

KEY_PROVIDER = "local"

KEY_VAULT_DB = "keyVault"
KEY_VAULT_COLL = "__keyVault"
KEY_VAULT_NAMESPACE = f"{KEY_VAULT_DB}.{KEY_VAULT_COLL}"

#
# MongoDB Setup
#

# 96 random hardcoded bytes, because it's only an example
MASTER_KEY = "V2hlbiB0aGUgY2F0J3MgYXdheSwgdGhlIG1pY2Ugd2lsbCBwbGF5LCBidXQgd2hlbiB0aGUgZG9nIGlzIGFyb3VuZCwgdGhlIGNhdCBiZWNvbWVzIGEgbmluamEuLi4u"

KMS_CREDS = {
    "local": {
        "key": MASTER_KEY
    },
}

CRYPT_SHARED_LIB = "/Users/joel.odom/Downloads/mongo_crypt_shared_v1-8.3.0-alpha0-477-g8229f2a/lib/mongo_crypt_v1.dylib"
os.environ["MONGOCRYPT_SHARED_LIB_PATH"] = CRYPT_SHARED_LIB

AUTO_ENCRYPTION_OPTS = AutoEncryptionOpts(
    KMS_CREDS,
    KEY_VAULT_NAMESPACE,
    crypt_shared_lib_path=CRYPT_SHARED_LIB
)

ENCRYPTED_CLIENT = MongoClient(
    MONGO_URI, auto_encryption_opts=AUTO_ENCRYPTION_OPTS)

# What to encrypt and with what search types
ENCRYPTED_FIELDS_MAP = {
    "fields": [
        {
            "path": "firstName",
            "bsonType": "string",
            "queries": [ {
                "queryType": "prefixPreview",  # prefix queryable
                "strMinQueryLength": 3,
                "strMaxQueryLength": 8,
                "caseSensitive": False,
                "diacriticSensitive": False,
            } ]
        },
        {
            "path": "lastName",
            "bsonType": "string",
            "queries": [ {
                "queryType": "prefixPreview",  # prefix queryable
                "strMinQueryLength": 3,
                "strMaxQueryLength": 8,
                "caseSensitive": False,
                "diacriticSensitive": False,
            } ]
        },
        {
            "path": "dateOfBirth",
            "bsonType": "date",
            "queries": [ {
                "queryType": "range",  # range queryable
                "min": datetime(1900, 1, 1),
                "max": datetime(2099, 12, 31)
            } ]
        },
        {
            "path": "zipCode",
            "bsonType": "string",
            "queries": [ {"queryType": "equality"} ]  # equality queryable
        },
        {
            "path": "notes",
            "bsonType": "string",
            "queries": [ {
                "queryType": "substringPreview",  # substring queryable
                "strMinQueryLength": 3,
                "strMaxQueryLength": 8,
                "caseSensitive": False,
                "diacriticSensitive": False,
                "strMaxLength": 300
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

#
# Flask setup
#

app = Flask(__name__, static_folder='.', static_url_path='')

# Disable caching for all responses
def nocache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.after_request(nocache)

#
# Web service endpoints
#

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def serve_css():
    return send_from_directory('.', 'styles.css')

@app.route('/sample-data', methods=['GET'])
def sample_data():
    try:
        with open(SAMPLE_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        abort(500, description=f'Error reading sample data: {e}')
    return jsonify(data)

@app.route('/load-sample', methods=['POST'])
def load_sample():
    # First destroy the old database
    destroy_db()

    #
    # Create the encrypted collection and add sample data
    #

    print("Creating collection...")
    CLIENT_ENCRYPTION.create_encrypted_collection(
        ENCRYPTED_CLIENT[DB],
        COLLECTION,
        ENCRYPTED_FIELDS_MAP,
        KEY_PROVIDER,
        MASTER_KEY_CREDS,
    )

    print("Reading sample file...")
    try:
        with open(SAMPLE_FILE, 'r') as f:
            docs = json.load(f)
        if not isinstance(docs, list):
            raise ValueError('Sample data must be a JSON array')
    except Exception as e:
        return f'Error reading sample file: {e}', 500
    
    # Replace existing
    
    print("Inserting sample data...")
    for d in docs:
        d['dateOfBirth'] = datetime.strptime(d['dateOfBirth'], "%Y-%m-%d")
    
    BATCH_SIZE = 50
    inserted = 0

    while inserted < len(docs):
        ENCRYPTED_CLIENT[DB][COLLECTION].insert_many(
            docs[inserted : inserted + BATCH_SIZE])
        inserted += BATCH_SIZE
    
    return 'Sample data loaded', 200

@app.route('/add-patient', methods=['POST'])
def add_patient():
    data = {
        'firstName': request.form.get('firstName', '').strip(),
        'lastName': request.form.get('lastName', '').strip(),
        'dateOfBirth': datetime.strptime(request.form.get('dateOfBirth', '').strip(), "%Y-%m-%d"),
        'zipCode': request.form.get('zipCode', '').strip(),
        'notes': request.form.get('notes', '').strip()
    }
    # Validate required fields
    if not all([data['firstName'], data['lastName'], data['dateOfBirth'], data['zipCode']]):
        return 'Missing required fields', 400
    ENCRYPTED_CLIENT[DB][COLLECTION].insert_one(data)
    return redirect(url_for('index'))

@app.route('/search', methods=['GET'])
def search():

    #
    # Create a compound $expr for searching
    #

    print("Searching...")

    AND = []

    firstName = request.args.get('firstName', '').strip()
    if len(firstName) >= 3:
        AND.append(
            {
                "$encStrStartsWith": {
                    "input": "$firstName",
                    "prefix": firstName
                }
            }
        )

    lastName = request.args.get('lastName', '').strip()
    if len(lastName) >= 3:
        AND.append(
            {
                "$encStrStartsWith": {
                    "input": "$lastName",
                    "prefix": lastName
                }
            }
        )

    yearOfBirth = request.args.get('yearOfBirth', '').strip()
    if yearOfBirth.isdigit() and len(yearOfBirth) == 4:
        AND.append(
            {
                "$gte": [
                    "$dateOfBirth",
                    datetime.strptime(f"{yearOfBirth}-01-01", "%Y-%m-%d")
                ]
            }
        )
        AND.append(
            {
                "$lt": [
                    "$dateOfBirth",
                    datetime.strptime(f"{int(yearOfBirth) + 1}-01-01", "%Y-%m-%d")
                ]
            }
        )
    
    zipCode = request.args.get('zipCode', '').strip()
    if len(zipCode) == 5:
        AND.append(
            {
                "$eq": [
                    "$zipCode",
                    zipCode
                ]
            }
        )

    notes = request.args.get('notes', '').strip()
    if len(notes) >= 3:
        AND.append(
            {
                "$encStrContains": {
                    "input": "$notes",
                    "substring": notes
                }
            }
        )

    if len(AND) < 1:
        return {}

    PIPELINE = [
        {
            "$match": {
                "$expr": {
                    "$and": AND
                }
            }
        },
        {
            "$project": { "_id": 0, "__safeContent__": 0 }
        }
    ]

    cursor = ENCRYPTED_CLIENT[DB][COLLECTION].aggregate(PIPELINE)
    docs = []
    for doc in cursor:
        # Reformat DOB
        doc['dateOfBirth'] = doc['dateOfBirth'].strftime("%Y-%m-%d")
        docs.append(doc)

    return jsonify(list(docs))

@app.route('/destroy-db', methods=['POST'])
def destroy_db():
    return 'Safety is in place', 500


    print("Dropping database...")
    ENCRYPTED_CLIENT.drop_database(DB)
    # TODO: Drop keyvault here BUT not if I have other demonstrations using it
    return 'Database dropped', 200

if __name__ == '__main__':
    #
    # Scratchpad code to add a bunch of fake data
    #

    ADD_FAKE_DATA = True
    added = 0

    while ADD_FAKE_DATA:
        fake = Faker()

        data = {
            'firstName': fake.first_name(),
            'lastName': fake.last_name(),
            'dateOfBirth': datetime.combine(fake.date_of_birth(), datetime.min.time()),
            'zipCode': fake.zipcode(),
            'notes': ""
        }

        ENCRYPTED_CLIENT[DB][COLLECTION].insert_one(data)

        added += 1
        print(f"Added {added} records so far.")

    else:
        app.run(host='0.0.0.0', port=PORT, debug=True)
