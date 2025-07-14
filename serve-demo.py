#!/usr/bin/env python3
import http.server
import socketserver
import os

# Simple multi-threaded HTTP server with address reuse
# Place patient_form.html and styles.css in the same folder as this script.

PORT = 8000

# Change working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ThreadingMixIn to handle each request in a separate thread
class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

Handler = http.server.SimpleHTTPRequestHandler

with ThreadingTCPServer(("", PORT), Handler) as httpd:
    print(f"Serving HTTP on localhost port {PORT} (http://localhost:{PORT}/) ...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()
