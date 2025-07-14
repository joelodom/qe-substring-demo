#!/usr/bin/env python3
import http.server
import socketserver
import os

# Multi-threaded HTTP server with address reuse and no-cache headers
# Serves files from the directory containing this script.

PORT = 3141

# Change working directory to script location
os.chdir(os.path.dirname(os.path.abspath(__file__)))

class NoCacheHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    Extends SimpleHTTPRequestHandler to add headers that disable caching.
    """
    def end_headers(self):
        # Add no-cache headers
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

class ThreadingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

def run_server(port=PORT):
    handler = NoCacheHTTPRequestHandler
    server = ThreadingTCPServer(("", port), handler)
    print(f"Serving HTTP on port {port} (http://localhost:{port}/) with caching disabled...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nInterrupt received, shutting down server...")
    finally:
        # Properly shutdown and close
        server.shutdown()
        server.server_close()
        print("Server stopped.")

if __name__ == '__main__':
    run_server()
