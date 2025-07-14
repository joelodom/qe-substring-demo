#!/usr/bin/env python3
from flask import Flask, request, send_from_directory, redirect, url_for, jsonify
from pymongo import MongoClient
import os

# Configuration
db_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
db_name = os.environ.get('DB_NAME', 'substringHospital')
collection_name = os.environ.get('COLLECTION', 'patients')
port = int(os.environ.get('PORT', 3141))

# Initialize Flask and MongoDB
app = Flask(__name__, static_folder='.', static_url_path='')
client = MongoClient(db_uri)
db = client[db_name]
patients = db[collection_name]

# Disable caching on responses
def nocache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.after_request(nocache)

# Serve static files
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def css():
    return send_from_directory('.', 'styles.css')

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
    if v := request.args.get('firstName'):
        if len(v) >= 3:
            query['firstName'] = {'$regex': v, '$options': 'i'}
    if v := request.args.get('lastName'):
        if len(v) >= 3:
            query['lastName'] = {'$regex': v, '$options': 'i'}
    if v := request.args.get('yearOfBirth'):
        if v.isdigit() and len(v) == 4:
            query['dateOfBirth'] = {'$regex': f'^{v}'}
    if v := request.args.get('zipCode'):
        if len(v) == 5:
            query['zipCode'] = v
    if v := request.args.get('notes'):
        if len(v) >= 3:
            query['notes'] = {'$regex': v, '$options': 'i'}
    results = list(patients.find(query, {'_id': 0}))
    return jsonify(results)

# Destroy database endpoint
@app.route('/destroy-db', methods=['POST'])
def destroy_db():
    # Drop the entire database
    client.drop_database(db_name)
    return 'Database dropped', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=port, debug=True)
