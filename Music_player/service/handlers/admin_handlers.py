import service.database as db

from service.permissions import require_admin
from service.serializers import track_to_dict, user_to_admin_dict
from service.utils import (
    build_error_response,
    build_json_response,
    parse_json_body,
    send_response,
)


def handle_admin_get_users(client_socket, current_user):
    if not require_admin(client_socket, current_user):
        return

    users = db.get_all_users()

    payload = {
        "status": "success",
        "users": [user_to_admin_dict(user) for user in users],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_admin_update_user_role(
    client_socket,
    user_id,
    headers,
    body,
    current_user
):
    if not require_admin(client_socket, current_user):
        return

    try:
        data = parse_json_body(body)
    except Exception:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Invalid JSON"),
        )
        return

    role = str(data.get("role", "")).strip()

    if role not in ("user", "admin"):
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Invalid role"),
        )
        return

    db.update_user_role(user_id, role)

    payload = {
        "status": "success",
        "message": "Role updated",
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_admin_get_user_tracks(client_socket, user_id, current_user):
    if not require_admin(client_socket, current_user):
        return

    tracks = db.get_user_tracks(user_id)

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_admin_delete_user_track(
    client_socket,
    user_id,
    track_id,
    current_user
):
    if not require_admin(client_socket, current_user):
        return

    track = db.get_track_by_id(track_id)

    if not track:
        send_response(
            client_socket,
            build_error_response(404, "Not Found", "Track not found"),
        )
        return

    db.delete_track(track_id)

    db.create_notification(
        user_id,
        f'Ваш трек "{track[4]}" был удалён администратором'
    )

    payload = {
        "status": "success",
        "message": "Track deleted",
    }

    send_response(client_socket, build_json_response(200, "OK", payload))