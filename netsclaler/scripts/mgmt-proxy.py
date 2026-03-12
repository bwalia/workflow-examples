#!/usr/bin/env python3
"""HTTP reverse proxy to expose NetScaler CPX management UI.

The CPX management UI (Apache httpd) on port 80 only accepts localhost
connections because the packet engine intercepts external traffic to the NSIP.
This proxy listens on port 9999 (not intercepted by the packet engine)
and forwards requests to localhost:80.
"""
import http.client
import http.server
import socketserver


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def _proxy(self):
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 80, timeout=30)
            body = None
            if "Content-Length" in self.headers:
                body = self.rfile.read(int(self.headers["Content-Length"]))

            # Forward headers, replacing Host
            headers = {}
            for h in self.headers:
                if h.lower() != "host":
                    headers[h] = self.headers[h]
            headers["Host"] = "127.0.0.1"

            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()

            self.send_response_only(resp.status)
            # Forward response headers
            for h, v in resp.getheaders():
                # Skip hop-by-hop headers
                if h.lower() in ("transfer-encoding", "connection", "keep-alive"):
                    continue
                self.send_header(h, v)

            # Read full response body and set Content-Length
            data = resp.read()
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
            conn.close()
        except Exception as e:
            try:
                self.send_response(502)
                self.send_header("Content-Length", "0")
                self.end_headers()
            except Exception:
                pass

    def log_message(self, format, *args):
        pass

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_PATCH = _proxy
    do_OPTIONS = _proxy


if __name__ == "__main__":
    ThreadedTCPServer.allow_reuse_address = True
    httpd = ThreadedTCPServer(("0.0.0.0", 9999), ProxyHandler)
    httpd.serve_forever()
