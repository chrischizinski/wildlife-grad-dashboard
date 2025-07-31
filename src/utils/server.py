#!/usr/bin/env python3
import http.server
import os
import socketserver


def start_server():
    os.chdir("/Users/cchizinski2/Dev/wildlife-grad/dashboard")

    # Find an available port
    for port in range(8000, 8100):
        try:
            with socketserver.TCPServer(
                ("", port), http.server.SimpleHTTPRequestHandler
            ) as httpd:
                print(f"Server started at http://localhost:{port}")
                print(
                    f"Dashboard available at http://localhost:{port}/pages/enhanced_index.html"
                )
                print("Press Ctrl+C to stop the server")
                httpd.serve_forever()
        except OSError:
            continue

    print("No available ports found")


if __name__ == "__main__":
    start_server()
