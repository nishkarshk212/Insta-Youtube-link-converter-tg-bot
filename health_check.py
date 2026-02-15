import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Healthy')
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server():
    # Start a simple health check server on port 10000
    server = HTTPServer(('0.0.0.0', 10000), HealthCheckHandler)
    server.serve_forever()

if __name__ == '__main__':
    # Start health check server in background
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    print('Health check server started on port 10000')