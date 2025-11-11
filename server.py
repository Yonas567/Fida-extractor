import http.server
import socketserver
import tempfile
import json
import os
# Lazy import to avoid loading heavy dependencies at startup
parse_id_card = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'ok', 'service': 'fida-extractor'}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/parse':
            try:
                # Lazy import - only load heavy dependencies when actually needed
                global parse_id_card
                if parse_id_card is None:
                    from main import parse_id_card
                
                content_length = int(self.headers['Content-Length'])
                pdf_data = self.rfile.read(content_length)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(pdf_data)
                    pdf_path = tmp.name
                
                try:
                    result = parse_id_card(pdf_path)
                    response = json.dumps(result, ensure_ascii=False)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response.encode('utf-8'))
                finally:
                    os.unlink(pdf_path)
                    for f in os.listdir('.'):
                        if f.startswith('extracted_'):
                            try:
                                os.unlink(f)
                            except:
                                pass
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    

if __name__ == '__main__':
    try:
        PORT = int(os.environ.get('PORT', 8000))
        print(f"Server Starting...")
        print(f"Port: {PORT}")
        print(f"Endpoint: POST /parse")
        print(f"Health check: GET /health")
        
        # Bind to all interfaces (0.0.0.0) so Render can detect it
        with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
            print(f"Server successfully started on port {PORT}")
            print(f"Ready to accept requests...")
            httpd.serve_forever()
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise