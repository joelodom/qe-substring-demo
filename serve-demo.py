#!/usr/bin/env python3
import http.server
import socketserver
import os

# Simple HTTP server to serve files from the current directory
# Place your HTML (patient_form.html) and styles.css in the same folder as this script.

PORT = 8000

# Serve files relative to the script's directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

Handler = http.server.SimpleHTTPRequestHandler

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"Serving HTTP on localhost port {PORT} (http://localhost:{PORT}/) ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()
