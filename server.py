import http.server
import socketserver
import tempfile
import json
import os
# Lazy import to avoid loading heavy dependencies at startup
parse_id_card = None

class Handler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        """Handle HEAD requests for health checks"""
        if self.path == '/health' or self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
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
                    print("Loading main module (first request)...")
                    try:
                        from main import parse_id_card
                        print("Main module loaded successfully")
                    except Exception as import_error:
                        print(f"ERROR importing main module: {import_error}")
                        import traceback
                        traceback.print_exc()
                        self.send_response(500)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': f'Failed to load parser: {str(import_error)}'}).encode('utf-8'))
                        return
                
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No content provided'}).encode('utf-8'))
                    return
                
                print(f"Reading {content_length} bytes...")
                pdf_data = self.rfile.read(content_length)
                print(f"Read {len(pdf_data)} bytes")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                    tmp.write(pdf_data)
                    pdf_path = tmp.name
                
                try:
                    print("Calling parse_id_card...")
                    result = parse_id_card(pdf_path)
                    print("Parsing completed successfully")
                    response = json.dumps(result, ensure_ascii=False)
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(response.encode('utf-8'))
                except Exception as parse_error:
                    print(f"ERROR in parse_id_card: {parse_error}")
                    import traceback
                    traceback.print_exc()
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': str(parse_error)}).encode('utf-8'))
                finally:
                    try:
                        os.unlink(pdf_path)
                    except:
                        pass
                    for f in os.listdir('.'):
                        if f.startswith('extracted_'):
                            try:
                                os.unlink(f)
                            except:
                                pass
            except Exception as e:
                print(f"ERROR in POST handler: {e}")
                import traceback
                traceback.print_exc()
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