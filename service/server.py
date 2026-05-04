import os
import re
import socket
import threading
from urllib.parse import urlparse, parse_qs, unquote_plus

from database import (
    get_all_tracks,
    get_track_by_id,
    add_track,
    search_tracks,
    get_all_artists,
    delete_track,
    update_track
)

HOST = "127.0.0.2"
PORT = 8080
BUFFER_SIZE = 4096
UPLOAD_DIR = "../uploads"

CLIENT_DISCONNECT_ERRORS = (
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError
)

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


def html_escape(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_artist_datalist():
    artists = get_all_artists()
    html = '<datalist id="artists-list">'
    for artist in artists:
        html += f'<option value="{html_escape(artist)}"></option>'
    html += '</datalist>'
    return html


def build_html_page(search_query=""):
    try:
        search_query = (search_query or "").strip()

        if search_query:
            tracks = search_tracks(search_query)
        else:
            tracks = get_all_tracks()

        artists_datalist = build_artist_datalist()
        safe_query = html_escape(search_query)

        html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Музыкальный веб-сервис</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f3f4f6;
            margin: 0;
            padding: 0;
        }}

        .container {{
            width: 1000px;
            margin: 30px auto;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0, 0, 0, 0.08);
        }}

        h1, h2 {{
            margin-top: 0;
        }}

        .upload-form, .search-form {{
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 25px;
            background: #f9fafb;
        }}

        .upload-form label, .search-form label {{
            display: block;
            margin-bottom: 12px;
        }}

        .upload-form input[type="text"],
        .upload-form input[type="file"],
        .search-form input[type="text"] {{
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            box-sizing: border-box;
        }}

        .button, button {{
            display: inline-block;
            padding: 10px 16px;
            cursor: pointer;
            text-decoration: none;
            color: black;
            margin-right: 10px;
        }}

        .track {{
            border: 1px solid #d1d5db;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }}

        .artist {{
            color: #6b7280;
            margin-top: 4px;
            margin-bottom: 10px;
        }}

        .meta {{
            color: #6b7280;
            font-size: 14px;
            margin-bottom: 8px;
        }}

        .actions {{
            margin-top: 10px;
            margin-bottom: 10px;
        }}

        .actions a {{
            margin-right: 10px;
        }}

        audio {{
            width: 100%;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Музыкальный веб-сервис</h1>
        <p>Хранение и потоковое воспроизведение музыки</p>

        <div class="search-form">
            <h2>Поиск</h2>
            <form action="/" method="GET">
                <label>
                    Название или исполнитель:
                    <input type="text" name="q" value="{safe_query}" list="artists-list">
                </label>
                <button type="submit">Найти</button>
                <a class="button" href="/">Сбросить</a>
            </form>
            {artists_datalist}
        </div>

        <div class="upload-form">
            <h2>Загрузка трека</h2>
            <form action="/upload" method="POST" enctype="multipart/form-data">
                <label>
                    Название трека:
                    <input type="text" name="title" required>
                </label>

                <label>
                    Исполнитель:
                    <input type="text" name="artist" list="artists-list" required>
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

        if search_query:
            html += f'<p class="meta">Результаты поиска по запросу: <strong>{safe_query}</strong></p>'

        if tracks:
            for track_id, title, artist, filename in tracks:
                safe_title = html_escape(title)
                safe_artist = html_escape(artist)
                safe_filename = html_escape(filename)

                html += f"""
        <div class="track">
            <div><strong>{safe_title}</strong></div>
            <div class="artist">{safe_artist}</div>
            <div class="meta">Файл: {safe_filename} | ID: {track_id}</div>

            <div class="actions">
                <a class="button" href="/edit?id={track_id}">Редактировать</a>
                <a class="button" href="/delete?id={track_id}" onclick="return confirm('Удалить трек?');">Удалить</a>
            </div>

            <audio controls>
                <source src="/stream?id={track_id}" type="audio/mpeg">
                Ваш браузер не поддерживает воспроизведение аудио.
            </audio>
        </div>
"""
        else:
            html += "<p>Треки не найдены.</p>"

        html += """
    </div>
</body>
</html>
"""
        return html

    except Exception as e:
        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Ошибка</title>
</head>
<body>
    <h1>Ошибка при формировании страницы</h1>
    <pre>{html_escape(str(e))}</pre>
</body>
</html>
"""


def build_edit_page(track):
    track_id, title, artist, filename = track
    artists_datalist = build_artist_datalist()

    return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Редактирование трека</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f3f4f6;
            margin: 0;
            padding: 0;
        }}

        .container {{
            width: 700px;
            margin: 30px auto;
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 0 12px rgba(0, 0, 0, 0.08);
        }}

        label {{
            display: block;
            margin-bottom: 12px;
        }}

        input[type="text"] {{
            width: 100%;
            padding: 8px;
            margin-top: 4px;
            box-sizing: border-box;
        }}

        button, a {{
            display: inline-block;
            padding: 10px 16px;
            text-decoration: none;
            color: black;
            margin-right: 10px;
        }}

        .meta {{
            color: #6b7280;
            margin-bottom: 16px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Редактирование трека</h1>
        <div class="meta">Файл: {html_escape(filename)} | ID: {track_id}</div>

        <form action="/edit?id={track_id}" method="POST">
            <label>
                Название трека:
                <input type="text" name="title" value="{html_escape(title)}" required>
            </label>

            <label>
                Исполнитель:
                <input type="text" name="artist" value="{html_escape(artist)}" list="artists-list" required>
            </label>

            <button type="submit">Сохранить</button>
            <a href="/">Отмена</a>
        </form>

        {artists_datalist}
    </div>
</body>
</html>
"""


def send_response(client_socket, status_code, status_text, content_type, body_bytes, extra_headers=""):
    headers = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"{extra_headers}"
        f"Connection: close\r\n"
        f"\r\n"
    )

    try:
        client_socket.sendall(headers.encode("utf-8") + body_bytes)
    except CLIENT_DISCONNECT_ERRORS:
        pass

def send_redirect(client_socket, location):
    headers = (
        "HTTP/1.1 303 See Other\r\n"
        f"Location: {location}\r\n"
        "Content-Length: 0\r\n"
        "Connection: close\r\n"
        "\r\n"
    )

    try:
        client_socket.sendall(headers.encode("utf-8"))
    except CLIENT_DISCONNECT_ERRORS:
        pass


def send_404(client_socket):
    body = b"<h1>404 Not Found</h1>"
    send_response(client_socket, 404, "Not Found", "text/html; charset=utf-8", body)


def send_400(client_socket, message):
    body = f"<h1>400 Bad Request</h1><pre>{html_escape(message)}</pre>".encode("utf-8")
    send_response(client_socket, 400, "Bad Request", "text/html; charset=utf-8", body)


def send_500(client_socket, error_text):
    body = f"<h1>500 Internal Server Error</h1><pre>{html_escape(error_text)}</pre>".encode("utf-8")
    send_response(client_socket, 500, "Internal Server Error", "text/html; charset=utf-8", body)


def handle_index(client_socket, query_params):
    search_query = query_params.get("q", [""])[0]
    search_query = unquote_plus(search_query)
    html = build_html_page(search_query)
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

    _, _, _, filename = track
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

    try:
        client_socket.sendall(headers.encode("utf-8"))

        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(BUFFER_SIZE)
                if not chunk:
                    break
                client_socket.sendall(chunk)

    except CLIENT_DISCONNECT_ERRORS:
        print(f"Клиент прервал потоковую передачу трека id={track_id}")
        return


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


def parse_urlencoded_form(body):
    form_text = body.decode("utf-8", errors="ignore")
    parsed = parse_qs(form_text)
    result = {}

    for key, value in parsed.items():
        result[key] = value[0] if value else ""

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


def handle_delete(client_socket, query_params):
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

    _, _, _, filename = track
    file_path = os.path.join(UPLOAD_DIR, filename)

    delete_track(track_id)

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    send_redirect(client_socket, "/")


def handle_edit_get(client_socket, query_params):
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

    html = build_edit_page(track)
    send_response(client_socket, 200, "OK", "text/html; charset=utf-8", html.encode("utf-8"))


def handle_edit_post(client_socket, query_params, headers, body):
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

    content_type = headers.get("content-type", "")

    if "application/x-www-form-urlencoded" not in content_type:
        send_400(client_socket, "Ожидался application/x-www-form-urlencoded")
        return

    form_data = parse_urlencoded_form(body)

    title = form_data.get("title", "").strip()
    artist = form_data.get("artist", "").strip()

    if not title or not artist:
        send_400(client_socket, "Название и исполнитель обязательны")
        return

    update_track(track_id, title, artist)
    send_redirect(client_socket, "/")


def handle_client(client_socket):
    try:
        method, path, version, headers, body = receive_http_request(client_socket)

        if method is None or path is None:
            send_404(client_socket)
            return

        parsed_url = urlparse(path)
        query_params = parse_qs(parsed_url.query)

        if method == "GET" and parsed_url.path == "/":
            handle_index(client_socket, query_params)

        elif method == "GET" and parsed_url.path == "/stream":
            handle_stream(client_socket, query_params)

        elif method == "POST" and parsed_url.path == "/upload":
            handle_upload(client_socket, headers, body)

        elif method == "GET" and parsed_url.path == "/delete":
            handle_delete(client_socket, query_params)

        elif method == "GET" and parsed_url.path == "/edit":
            handle_edit_get(client_socket, query_params)

        elif method == "POST" and parsed_url.path == "/edit":
            handle_edit_post(client_socket, query_params, headers, body)

        else:
            send_404(client_socket)

    except CLIENT_DISCONNECT_ERRORS:
        print("Клиент закрыл соединение раньше завершения обработки")
    except Exception as e:
        print("Ошибка обработки запроса:", e)
        try:
            send_500(client_socket, str(e))
        except CLIENT_DISCONNECT_ERRORS:
            pass
    finally:
        try:
            client_socket.close()
        except OSError:
            pass

def start_server():
    ensure_uploads_dir()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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