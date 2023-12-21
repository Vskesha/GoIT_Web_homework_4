import mimetypes
import urllib.parse
import json
import logging
import socket
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


BASE_DIR = Path()
BUFFER_SIZE = 1024
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


class MySimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        route = urllib.parse.urlparse(self.path)
        match route.path:
            case '/':
                self.send_html('index.html')
            case '/message':
                self.send_html('message.html')
            case _:
                file = BASE_DIR.joinpath(route.path[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html('error.html', 404)

    def do_POST(self):
        size = self.headers.get('Content-Length')
        data = self.rfile.read(int(size))

        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client_socket.sendto(data, (SOCKET_HOST, SOCKET_PORT))
        client_socket.close()

        self.send_response(302)
        self.send_header('Location', '/')
        self.end_headers()

    def send_html(self, filename, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())

    def send_static(self, filename, status_code=200):
        self.send_response(status_code)
        mime_type, *_ = mimetypes.guess_type(filename)
        self.send_header('Content-Type', mime_type or 'text/plain')
        self.end_headers()
        with open(filename, 'rb') as file:
            self.wfile.write(file.read())


def save_data(data):
    parse_data = urllib.parse.unquote_plus(data.decode())
    try:
        parse_dict = {key: value for key, value in [el.split('=') for el in parse_data.split('&')]}
        parse_dict = {str(datetime.now()): parse_dict}
        whole_data = {}
        if Path('storage/data.json').exists():
            with open('storage/data.json', 'r', encoding='utf-8') as file:
                whole_data = json.load(file)
        whole_data.update(parse_dict)
        with open('storage/data.json', 'w', encoding='utf-8') as file:
            json.dump(whole_data, file, ensure_ascii=False, indent=4)
    except ValueError as err:
        logging.error(err)
    except OSError as err:
        logging.error(err)


def run_socket_server(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))
    logging.info("Starting socket server")
    try:
        while True:
            msg, address = server_socket.recvfrom(BUFFER_SIZE)
            logging.info(f"Socket received {address}: {msg}")
            save_data(msg)
    except KeyboardInterrupt:
        pass
    finally:
        server_socket.close()


def run_http_server(host, port):
    address = (host, port)
    server_http = HTTPServer(address, MySimpleHTTPRequestHandler)
    logging.info("Starting http server")
    try:
        server_http.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server_http.server_close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='%(threadName)s %(message)s')

    http_server = Thread(target=run_http_server, args=(HTTP_HOST, HTTP_PORT))
    http_server.start()

    socket_server = Thread(target=run_socket_server, args=(SOCKET_HOST, SOCKET_PORT))
    socket_server.start()
