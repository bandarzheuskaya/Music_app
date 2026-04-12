import os
import re
import socket
import threading
from urllib.parse import urlparse, parse_qs

from database import get_all_tracks, get_track_by_id, add_track

HOST = "127.0.0.2"
PORT = 8080
BUFFER_SIZE = 4096
UPLOAD_DIR = "uploads"


def ensure_uploads_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)


def sanitize_filename(filename):
    filename = os.path.basename(filename)
    filename = filename.replace("\\", "_").replace("/", "_")
    return filename


def make_unique_filename(filename):
    filename = sanitize_filename(filename)
    base, ext = os.path.splitext(filename)
    candidate = filename
    counter = 1

    while os.path.exists(os.path.join(UPLOAD_DIR, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1

    return candidate


def build_html_page():
    tracks = get_all_tracks()

    html = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Музыкальный веб-сервис</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f3f4f6;
            margin: 0;
            padding: 0;
        }

        .container {
            width: 900px;
            margin: 30px auto;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0, 0, 0, 0.08);
        }

        h1, h2 {
            margin-top: 0;
        }

        .upload-form {
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 25px;
            background: #f9fafb;
        }

        .upload-form label {
            display: block;
            margin-bottom: 12px;
        }

        .upload-form input[type="text"],
        .upload-form input[type="file"] {
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            box-sizing: border-box;
        }

        .upload-form button {
            padding: 10px 16px;
            cursor: pointer;
        }

        .track {
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }

        .artist {
            color: #6b7280;
            margin-top: 4px;
            margin-bottom: 10px;
        }

        audio {
            width: 100%;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Музыкальный веб-сервис</h1>
        <p>Хранение и потоковое воспроизведение музыки</p>

        <div class="upload-form">
            <h2>Загрузка трека</h2>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <label>
                    Название трека:
                    <input type="text" name="title" required>
                </label>

                <label>
                    Исполнитель:
                    <input type="text" name="artist" required>
                </label>

                <label>
                    MP3-файл:
                    <input type="file" name="file" accept=".mp3,audio/mpeg" required>
                </label>

                <button type="submit">Загрузить</button>
            </form>
        </div>

        <h2>Список треков</h2>
"""

    if tracks:
        for track_id, title, artist, filename in tracks:
            html += f"""
        <div class="track">
            <div><strong>{title}</strong></div>
            <div class="artist">{artist}</div>
            <audio controls>
                <source src="/stream?id={track_id}" type="audio/mpeg">
                Ваш браузер не поддерживает воспроизведение аудио.
            </audio>
        </div>
"""
    else:
        html += "<p>Треки пока отсутствуют.</p>"

    html += """
    </div>
</body>
</html>
"""
    return html


def send_response(client_socket, status_code, status_text, content_type, body_bytes, extra_headers=""):
    headers = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"{extra_headers}"
        f"Connection: close\r\n"
        f"\r\n"
    )
    client_socket.sendall(headers.encode("utf-8") + body_bytes)


def send_redirect(client_socket, location):
    headers = (
        "HTTP/1.1 303 See Other\r\n"
        f"Location: {location}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "\r\n"
    )
    client_socket.sendall(headers.encode("utf-8"))


def send_404(client_socket):
    body = b"<h1>404 Not Found</h1>"
    send_response(client_socket, 404, "Not Found", "text/html; charset=utf-8", body)


def send_400(client_socket, message):
    body = f"<h1>400 Bad Request</h1><pre>{message}</pre>".encode("utf-8")
    send_response(client_socket, 400, "Bad Request", "text/html; charset=utf-8", body)


def send_500(client_socket, error_text):
    body = f"<h1>500 Internal Server Error</h1><pre>{error_text}</pre>".encode("utf-8")
    send_response(client_socket, 500, "Internal Server Error", "text/html; charset=utf-8", body)


def handle_index(client_socket):
    html = build_html_page()
    send_response(client_socket, 200, "OK", "text/html; charset=utf-8", html.encode("utf-8"))


def handle_stream(client_socket, query_params):
    if "id" not in query_params:
        send_404(client_socket)
        return

    try:
        track_id = int(query_params["id"][0])
    except ValueError:
        send_404(client_socket)
        return

    track = get_track_by_id(track_id)
    if track is None:
        send_404(client_socket)
        return

    _, title, artist, filename = track
    file_path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(file_path):
        send_404(client_socket)
        return

    file_size = os.path.getsize(file_path)

    headers = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: audio/mpeg\r\n"
        f"Content-Length: {file_size}\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    client_socket.sendall(headers.encode("utf-8"))

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(BUFFER_SIZE)
            if not chunk:
                break
            client_socket.sendall(chunk)


def parse_request_headers(header_bytes):
    text = header_bytes.decode("utf-8", errors="ignore")
    lines = text.split("\r\n")

    if not lines or not lines[0]:
        return None, None, None, {}

    request_line = lines[0]
    parts = request_line.split()

    if len(parts) != 3:
        return None, None, None, {}

    method, path, version = parts
    headers = {}

    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key.lower()] = value

    return method, path, version, headers


def receive_http_request(client_socket):
    data = b""

    while b"\r\n\r\n" not in data:
        chunk = client_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        data += chunk

    if b"\r\n\r\n" not in data:
        return None, None, None, {}, b""

    header_part, body_part = data.split(b"\r\n\r\n", 1)
    method, path, version, headers = parse_request_headers(header_part)

    content_length = int(headers.get("content-length", "0"))

    while len(body_part) < content_length:
        chunk = client_socket.recv(BUFFER_SIZE)
        if not chunk:
            break
        body_part += chunk

    return method, path, version, headers, body_part


def extract_boundary(content_type):
    match = re.search(r"boundary=(.+)", content_type)
    if not match:
        return None
    return match.group(1)


def parse_multipart_form_data(body, boundary):
    result = {}
    boundary_bytes = ("--" + boundary).encode("utf-8")
    parts = body.split(boundary_bytes)

    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue

        if b"\r\n\r\n" not in part:
            continue

        headers_block, content = part.split(b"\r\n\r\n", 1)
        header_text = headers_block.decode("utf-8", errors="ignore")

        content = content.rstrip(b"\r\n")

        disposition_match = re.search(
            r'Content-Disposition: form-data; name="([^"]+)"(?:; filename="([^"]+)")?',
            header_text,
            re.IGNORECASE
        )

        if not disposition_match:
            continue

        field_name = disposition_match.group(1)
        filename = disposition_match.group(2)

        if filename is not None:
            result[field_name] = {
                "filename": filename,
                "content": content
            }
        else:
            result[field_name] = content.decode("utf-8", errors="ignore")

    return result


def handle_upload(client_socket, headers, body):
    content_type = headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        send_400(client_socket, "Ожидался multipart/form-data")
        return

    boundary = extract_boundary(content_type)
    if not boundary:
        send_400(client_socket, "Не найден boundary")
        return

    form_data = parse_multipart_form_data(body, boundary)

    title = form_data.get("title", "").strip()
    artist = form_data.get("artist", "").strip()
    file_data = form_data.get("file")

    if not title or not artist or not file_data:
        send_400(client_socket, "Не заполнены обязательные поля")
        return

    original_filename = file_data["filename"]
    file_content = file_data["content"]

    if not original_filename.lower().endswith(".mp3"):
        send_400(client_socket, "Разрешены только MP3-файлы")
        return

    saved_filename = make_unique_filename(original_filename)
    file_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(file_path, "wb") as f:
        f.write(file_content)

    add_track(title, artist, saved_filename)
    send_redirect(client_socket, "/")


def handle_client(client_socket):
    try:
        method, path, version, headers, body = receive_http_request(client_socket)

        if method is None or path is None:
            send_404(client_socket)
            return

        parsed_url = urlparse(path)

        if method == "GET" and parsed_url.path == "/":
            handle_index(client_socket)

        elif method == "GET" and parsed_url.path == "/stream":
            query_params = parse_qs(parsed_url.query)
            handle_stream(client_socket, query_params)

        elif method == "POST" and parsed_url.path == "/upload":
            handle_upload(client_socket, headers, body)

        else:
            send_404(client_socket)

    except Exception as e:
        send_500(client_socket, str(e))
    finally:
        client_socket.close()


def start_server():
    ensure_uploads_dir()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(10)

    print(f"Сервер запущен: http://{HOST}:{PORT}")

    while True:
        client_socket, client_address = server_socket.accept()
        print(f"Подключение от {client_address}")

        client_thread = threading.Thread(
            target=handle_client,
            args=(client_socket,)
        )
        client_thread.daemon = True
        client_thread.start()


if __name__ == "__main__":
    start_server()