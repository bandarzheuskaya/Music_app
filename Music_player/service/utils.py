import json
import os
import re
import hashlib
import logging
import threading
import time
import time

from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlparse

from service.settings import LOG_FILE

try:
    from service.settings import ALLOWED_ORIGINS
except ImportError:
    ALLOWED_ORIGINS = []


CLIENT_DISCONNECT_ERRORS = (
    BrokenPipeError,
    ConnectionResetError,
    ConnectionAbortedError
)


_request_context = threading.local()


def set_request_origin(headers):
    _request_context.origin = headers.get("origin")


def get_cors_origin():
    origin = getattr(_request_context, "origin", None)

    if not origin:
        return None

    if ALLOWED_ORIGINS and origin in ALLOWED_ORIGINS:
        return origin

    if origin.endswith(":5500"):
        return origin

    return None


def sanitize_filename(filename):
    filename = os.path.basename(filename)
    filename = filename.replace("\\", "_").replace("/", "_")
    return filename


def make_unique_filename(upload_dir, filename):
    filename = sanitize_filename(filename)
    base, ext = os.path.splitext(filename)

    candidate = filename
    counter = 1

    while os.path.exists(os.path.join(upload_dir, candidate)):
        candidate = f"{base}_{counter}{ext}"
        counter += 1

    return candidate


def json_dumps(data):
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def build_response(
    status_code,
    reason,
    body=b"",
    content_type="application/json; charset=utf-8",
    extra_headers=None
):
    if extra_headers is None:
        extra_headers = {}

    cors_origin = get_cors_origin()

    headers = {
        "Content-Type": content_type,
        "Content-Length": str(len(body)),
        "Connection": "close",
        "Access-Control-Allow-Origin": cors_origin or "null",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400"
    }

    headers.update(extra_headers)

    response = f"HTTP/1.1 {status_code} {reason}\r\n"

    for key, value in headers.items():
        response += f"{key}: {value}\r\n"

    response += "\r\n"

    return response.encode("utf-8") + body


def build_json_response(status_code, reason, payload):
    body = json_dumps(payload)

    return build_response(
        status_code,
        reason,
        body,
        "application/json; charset=utf-8"
    )


def build_empty_response(status_code, reason, extra_headers=None):
    return build_response(
        status_code,
        reason,
        b"",
        "text/plain; charset=utf-8",
        extra_headers
    )


def send_response(client_socket, response_bytes):
    try:
        client_socket.sendall(response_bytes)
    except CLIENT_DISCONNECT_ERRORS:
        pass


def build_error_response(status_code, reason, message):
    return build_json_response(status_code, reason, {
        "status": "error",
        "message": message
    })


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


def receive_http_request(client_socket, buffer_size):
    data = b""

    while b"\r\n\r\n" not in data:
        chunk = client_socket.recv(buffer_size)

        if not chunk:
            break

        data += chunk

    if b"\r\n\r\n" not in data:
        return None, None, None, {}, b""

    header_part, body_part = data.split(b"\r\n\r\n", 1)

    method, path, version, headers = parse_request_headers(header_part)

    set_request_origin(headers)

    content_length = int(headers.get("content-length", "0"))

    while len(body_part) < content_length:
        chunk = client_socket.recv(buffer_size)

        if not chunk:
            break

        body_part += chunk

    return method, path, version, headers, body_part


def parse_json_body(body):
    if not body:
        return {}

    return json.loads(body.decode("utf-8"))


def parse_urlencoded_form(body):
    form_text = body.decode("utf-8", errors="ignore")

    parsed = parse_qs(form_text)

    result = {}

    for key, value in parsed.items():
        result[key] = value[0] if value else ""

    return result


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


def parse_path(path):
    parsed_url = urlparse(path)

    return parsed_url.path, parse_qs(parsed_url.query)


def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8"
    )


def log_info(message):
    logging.info(message)


def log_error(message):
    logging.error(message)


def parse_cookies(headers):
    raw_cookie = headers.get("cookie", "")

    cookie = SimpleCookie()
    cookie.load(raw_cookie)

    result = {}

    for key, morsel in cookie.items():
        result[key] = morsel.value

    return result


def build_set_cookie_header(name, value, max_age=None):
    parts = [
        f"{name}={value}",
        "Path=/",
        "HttpOnly",
        "SameSite=Lax"
    ]

    if max_age is not None:
        parts.append(f"Max-Age={max_age}")

    return "; ".join(parts)


def build_delete_cookie_header(name):
    return f"{name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"


def calculate_bytes_hash(data):
    return hashlib.sha256(data).hexdigest()


def calculate_file_hash(file_path):
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def is_valid_image_signature(filename, content):
    lower = filename.lower()

    if lower.endswith((".jpg", ".jpeg")):
        return content.startswith(b"\xff\xd8\xff")

    if lower.endswith(".png"):
        return content.startswith(b"\x89PNG\r\n\x1a\n")

    if lower.endswith(".webp"):
        return (
            len(content) >= 12
            and content[:4] == b"RIFF"
            and content[8:12] == b"WEBP"
        )

    return False


def is_valid_mp3_signature(content):
    if content.startswith(b"ID3"):
        return True

    if len(content) >= 2:
        first = content[0]
        second = content[1]

        return first == 0xFF and (second & 0xE0) == 0xE0

    return False


def is_valid_wav_signature(content):
    return (
        len(content) >= 12
        and content[:4] == b"RIFF"
        and content[8:12] == b"WAVE"
    )


def get_file_extension(filename):
    return os.path.splitext(filename.lower())[1]


def validate_cover_file(filename, content, max_size):
    allowed_ext = (".jpg", ".jpeg", ".png", ".webp")

    if not filename:
        return False, "Cover filename is required"

    if not filename.lower().endswith(allowed_ext):
        return False, "Cover image must be JPG, PNG or WEBP"

    if len(content) > max_size:
        return False, "Cover image is too large"

    if not is_valid_image_signature(filename, content):
        return False, "Invalid image file signature"

    return True, ""


def validate_audio_file(filename, content, max_size):
    if not filename:
        return False, "Audio filename is required"

    extension = get_file_extension(filename)

    allowed_extensions = (".mp3", ".wav")

    if extension not in allowed_extensions:
        return False, "Only MP3 and WAV files are supported"

    if len(content) > max_size:
        return False, "Audio file is too large"

    if extension == ".mp3":
        if not is_valid_mp3_signature(content):
            return False, "Invalid MP3 file signature"

    elif extension == ".wav":
        if not is_valid_wav_signature(content):
            return False, "Invalid WAV file signature"

    return True, ""


def safe_remove_file(file_path):
    if not file_path:
        return

    abs_path = os.path.abspath(file_path)

    if not os.path.exists(abs_path):
        return

    for attempt in range(10):
        try:
            os.remove(abs_path)
            return
        except OSError as e:
            if attempt == 9:
                log_error(f"Failed to remove file {abs_path}: {e}")
                return

            time.sleep(0.5)
