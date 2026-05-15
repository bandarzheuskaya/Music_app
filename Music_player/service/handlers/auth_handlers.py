import psycopg

import service.auth as auth
import service.database as db

from service.utils import (
    build_error_response,
    build_json_response,
    build_response,
    build_delete_cookie_header,
    build_set_cookie_header,
    json_dumps,
    log_info,
    parse_cookies,
    parse_json_body,
    send_response,
)


def handle_register(client_socket, headers, body):
    content_type = headers.get("content-type", "")

    if "application/json" not in content_type:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", "Expected application/json"),
        )
        return

    try:
        data = parse_json_body(body)
    except Exception:
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid JSON"))
        return

    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))

    if not auth.validate_username(username):
        send_response(
            client_socket,
            build_error_response(
                400,
                "Bad Request",
                "Username must contain 3-30 latin letters, digits or underscores",
            ),
        )
        return

    if not auth.validate_email(email):
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid email"))
        return

    if not auth.validate_password(password):
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Password must contain 8-72 characters"),
        )
        return

    if db.get_user_by_username(username):
        send_response(client_socket, build_error_response(409, "Conflict", "Username already exists"))
        return

    if db.get_user_by_email(email):
        send_response(client_socket, build_error_response(409, "Conflict", "Email already exists"))
        return

    password_hash = auth.hash_password(password)

    try:
        user_id = db.create_user(username, email, password_hash, role="user")
    except psycopg.errors.UniqueViolation:
        send_response(client_socket, build_error_response(409, "Conflict", "User already exists"))
        return

    log_info(f"User registered: {username}")

    payload = {
        "status": "success",
        "message": "User registered",
        "user_id": user_id,
    }

    send_response(client_socket, build_json_response(201, "Created", payload))


def handle_login(client_socket, headers, body):
    content_type = headers.get("content-type", "")

    if "application/json" not in content_type:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", "Expected application/json"),
        )
        return

    try:
        data = parse_json_body(body)
    except Exception:
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid JSON"))
        return

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Username and password are required"),
        )
        return

    user_row = db.get_user_by_login(username)

    if not user_row:
        send_response(client_socket, build_error_response(401, "Unauthorized", "Invalid username or password"))
        return

    user = auth.user_to_dict(user_row)

    if not auth.check_password(password, user["password_hash"]):
        send_response(client_socket, build_error_response(401, "Unauthorized", "Invalid username or password"))
        return

    session_token = auth.create_user_session(user["id"])

    cookie_header = build_set_cookie_header(
        "session_token",
        session_token,
        max_age=60 * 60 * 24 * 7
    )

    log_info(f"User logged in: {user['username']}")

    payload = {
        "status": "success",
        "message": "Logged in",
        "user": auth.public_user_to_dict(user),
    }

    response = build_response(
        200,
        "OK",
        body=json_dumps(payload),
        content_type="application/json; charset=utf-8",
        extra_headers={
            "Set-Cookie": cookie_header
        }
    )

    send_response(client_socket, response)


def handle_logout(client_socket, headers):
    cookies = parse_cookies(headers)
    session_token = cookies.get("session_token")

    if session_token:
        db.delete_session(session_token)

    cookie_header = build_delete_cookie_header("session_token")

    payload = {
        "status": "success",
        "message": "Logged out",
    }

    response = build_response(
        200,
        "OK",
        body=json_dumps(payload),
        content_type="application/json; charset=utf-8",
        extra_headers={
            "Set-Cookie": cookie_header
        }
    )

    send_response(client_socket, response)


def handle_me(client_socket, headers):
    current_user = auth.get_current_user(headers)

    if not current_user:
        payload = {
            "status": "success",
            "user": None,
        }
        send_response(client_socket, build_json_response(200, "OK", payload))
        return

    payload = {
        "status": "success",
        "user": auth.public_user_to_dict(current_user),
    }

    send_response(client_socket, build_json_response(200, "OK", payload))