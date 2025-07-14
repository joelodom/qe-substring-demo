#!/usr/bin/env python3
from flask import Flask, request, send_from_directory, redirect, url_for, jsonify
from pymongo import MongoClient
import os

# Tuneables
MONGO_URI = 'mongodb://localhost:27017/'
PORT = 3141

# Probably don't tune
DATABASE = "substringHospital"
COLLECTION = "patients"

# Flask app to serve static files and handle MongoDB operations
app = Flask(__name__, static_folder='.', static_url_path='')

# Connect to local MongoDB
client = MongoClient(MONGO_URI)
db = client[DATABASE]
patients = db[COLLECTION]

# Prevent caching for all responses
def nocache(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response
app.after_request(nocache)

# Serve HTML and CSS
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/styles.css')
def css():
    return send_from_directory('.', 'styles.css')

# Handle new patient submissions
@app.route('/add-patient', methods=['POST'])
def add_patient():
    data = {
        'firstName': request.form.get('firstName', '').strip(),
        'lastName': request.form.get('lastName', '').strip(),
        'dateOfBirth': request.form.get('dateOfBirth', '').strip(),
        'zipCode': request.form.get('zipCode', '').strip()
    }

    # Basic validation
    if not all(data.values()):
        return 'Missing fields', 400
    
    # Insert into MongoDB
    patients.insert_one(data)
    return redirect(url_for('index'))

# API endpoint to search patients
@app.route('/search', methods=['GET'])
def search():
    query = {}
    if request.args.get('firstName'):
        query['firstName'] = {'$regex': request.args['firstName'], '$options': 'i'}
    if request.args.get('lastName'):
        query['lastName'] = {'$regex': request.args['lastName'], '$options': 'i'}
    if request.args.get('yearOfBirth'):
        year = request.args['yearOfBirth']
        query['dateOfBirth'] = {'$regex': f'^{year}'}
    if request.args.get('zipCode'):
        query['zipCode'] = request.args['zipCode']
    results = list(patients.find(query, {'_id': 0}))
    return jsonify(results)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', PORT))
    app.run(host='0.0.0.0', port=port, debug=True)
