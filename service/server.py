import socket
import threading

from service.routes import dispatch_request
from service.settings import BUFFER_SIZE, HOST, PORT, UPLOAD_DIR, COVER_DIR
from service.utils import (
    CLIENT_DISCONNECT_ERRORS,
    build_error_response,
    log_error,
    log_info,
    parse_path,
    receive_http_request,
    send_response,
    setup_logging
)


def ensure_storage_dirs():
    import os

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(COVER_DIR, exist_ok=True)


def handle_client(client_socket):
    try:
        method, path, version, headers, body = receive_http_request(client_socket, BUFFER_SIZE)

        if method is None or path is None:
            send_response(client_socket, build_error_response(400, "Bad Request", "Invalid HTTP request"))
            return

        path_only, query_params = parse_path(path)

        log_info(f"{method} {path_only}")

        dispatch_request(client_socket, method, path_only, query_params, headers, body)

    except CLIENT_DISCONNECT_ERRORS:
        log_info("Client disconnected")
    except Exception as e:
        log_error(f"Request handling error: {e}")

        try:
            send_response(client_socket, build_error_response(500, "Internal Server Error", str(e)))
        except CLIENT_DISCONNECT_ERRORS:
            pass
    finally:
        try:
            client_socket.close()
        except OSError:
            pass


def start_server():
    setup_logging()
    ensure_storage_dirs()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    log_info(f"Service started at http://{HOST}:{PORT}")
    print(f"Service started at http://{HOST}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()

        log_info(f"Connection from {client_address}")

        client_thread = threading.Thread(target=handle_client, args=(client_socket,))
        client_thread.daemon = True
        client_thread.start()