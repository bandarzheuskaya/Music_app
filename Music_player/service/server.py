import socket
import threading

from service.routes import dispatch_request
from service.settings import BUFFER_SIZE, HOST, PORT, UPLOAD_DIR, COVER_DIR

try:
    from service.settings import KEEP_ALIVE_ENABLED, KEEP_ALIVE_TIMEOUT, KEEP_ALIVE_MAX_REQUESTS
except ImportError:
    KEEP_ALIVE_ENABLED = True
    KEEP_ALIVE_TIMEOUT = 5
    KEEP_ALIVE_MAX_REQUESTS = 100
from service.utils import (
    CLIENT_DISCONNECT_ERRORS,
    build_error_response,
    log_error,
    log_info,
    parse_path,
    receive_http_request,
    send_response,
    set_response_connection,
    setup_logging
)


def ensure_storage_dirs():
    import os

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(COVER_DIR, exist_ok=True)


def is_stream_request(method, path_only):
    return method == "GET" and path_only.startswith("/api/tracks/") and path_only.endswith("/stream")


def should_keep_connection_alive(version, headers, request_number, force_close=False):
    if not KEEP_ALIVE_ENABLED or force_close:
        return False

    connection_header = headers.get("connection", "").lower()

    if "close" in connection_header:
        return False

    if version == "HTTP/1.0" and "keep-alive" not in connection_header:
        return False

    if KEEP_ALIVE_MAX_REQUESTS and request_number >= KEEP_ALIVE_MAX_REQUESTS:
        return False

    return True


def handle_client(client_socket):
    request_number = 0

    if KEEP_ALIVE_ENABLED:
        client_socket.settimeout(KEEP_ALIVE_TIMEOUT)

    try:
        while True:
            try:
                method, path, version, headers, body = receive_http_request(client_socket, BUFFER_SIZE)
            except socket.timeout:
                log_info("Keep-alive connection timeout")
                break

            if body is None:
                break

            if method is None or path is None:
                set_response_connection("close")
                send_response(client_socket, build_error_response(400, "Bad Request", "Invalid HTTP request"))
                break

            request_number += 1
            path_only, query_params = parse_path(path)

            log_info(f"{method} {path_only}")

            force_close = is_stream_request(method, path_only)
            keep_alive = should_keep_connection_alive(
                version,
                headers,
                request_number,
                force_close=force_close,
            )

            if keep_alive:
                set_response_connection(
                    "keep-alive",
                    timeout=KEEP_ALIVE_TIMEOUT,
                    max_requests=KEEP_ALIVE_MAX_REQUESTS,
                )
            else:
                set_response_connection("close")

            try:
                dispatch_request(client_socket, method, path_only, query_params, headers, body)
            except Exception as e:
                log_error(f"Request handling error: {e}")

                try:
                    set_response_connection("close")
                    send_response(client_socket, build_error_response(500, "Internal Server Error", str(e)))
                except CLIENT_DISCONNECT_ERRORS:
                    pass

                break

            if not keep_alive:
                break

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
