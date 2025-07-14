# Springfield General Hospital Patient Search

**A simple hospital customer service web application** built with Flask and MongoDB that lets you add new patients, search existing records, and manage sample data. This application demonstrates
Queryable Encrypton substring, prefix, range and equality searches in the same application.

## Features

- **Add Patient**: Enter first name, last name, date of birth, ZIP code, and freeform notes (up to 300 characters).
- **Search Patients**: Live search by first or last name (≥3 letters), year of birth, ZIP code, or keyword in notes.
- **Admin Tools**:
  - **Destroy Database**: Drop the entire MongoDB database after confirmation.
  - **Load Sample Data**: Bulk-load a predefined set of Simpsons-themed sample records from `sample-data.json`.
