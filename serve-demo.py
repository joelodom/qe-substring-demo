#!/usr/bin/env python3
import os
import json
from flask import Flask, request, send_from_directory, redirect, url_for, jsonify, abort
from pymongo import MongoClient

# Configuration (env vars overridable)
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'substringHospital')
COLLECTION = os.environ.get('COLLECTION', 'patients')
PORT = int(os.environ.get('PORT', 3141))
SAMPLE_FILE = os.environ.get('SAMPLE_FILE', 'sample-data.json')

# Flask and Mongo setup
app = Flask(__name__, static_folder='.', static_url_path='')
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
patients = db[COLLECTION]

# Disable caching for all responses
def nocache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.after_request(nocache)

# Serve static HTML and CSS
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def serve_css():
    return send_from_directory('.', 'styles.css')

# Serve sample data JSON
@app.route('/sample-data', methods=['GET'])
def sample_data():
    try:
        with open(SAMPLE_FILE, 'r') as f:
            data = json.load(f)
    except Exception as e:
        abort(500, description=f'Error reading sample data: {e}')
    return jsonify(data)

# Load sample data into DB
@app.route('/load-sample', methods=['POST'])
def load_sample():
    try:
        with open(SAMPLE_FILE, 'r') as f:
            docs = json.load(f)
        if not isinstance(docs, list):
            raise ValueError('Sample data must be a JSON array')
    except Exception as e:
        return f'Error reading sample file: {e}', 500
    # Replace existing
    patients.delete_many({})
    patients.insert_many(docs)
    return 'Sample data loaded', 200

# Add patient endpoint
@app.route('/add-patient', methods=['POST'])
def add_patient():
    data = {
        'firstName': request.form.get('firstName', '').strip(),
        'lastName': request.form.get('lastName', '').strip(),
        'dateOfBirth': request.form.get('dateOfBirth', '').strip(),
        'zipCode': request.form.get('zipCode', '').strip(),
        'notes': request.form.get('notes', '').strip()
    }
    # Validate required fields
    if not all([data['firstName'], data['lastName'], data['dateOfBirth'], data['zipCode']]):
        return 'Missing required fields', 400
    patients.insert_one(data)
    return redirect(url_for('index'))

# Search endpoint
@app.route('/search', methods=['GET'])
def search():
    query = {}
    v = request.args.get('firstName', '').strip()
    if len(v) >= 3:
        query['firstName'] = {'$regex': v, '$options': 'i'}
    v = request.args.get('lastName', '').strip()
    if len(v) >= 3:
        query['lastName'] = {'$regex': v, '$options': 'i'}
    v = request.args.get('yearOfBirth', '').strip()
    if v.isdigit() and len(v) == 4:
        query['dateOfBirth'] = {'$regex': f'^{v}'}
    v = request.args.get('zipCode', '').strip()
    if len(v) == 5:
        query['zipCode'] = v
    v = request.args.get('notes', '').strip()
    if len(v) >= 3:
        query['notes'] = {'$regex': v, '$options': 'i'}
    results = list(patients.find(query, {'_id': 0}))
    return jsonify(results)

# Destroy database endpoint
@app.route('/destroy-db', methods=['POST'])
def destroy_db():
    client.drop_database(DB_NAME)
    return 'Database dropped', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT, debug=True)
