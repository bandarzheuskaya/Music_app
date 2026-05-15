from service.utils import build_error_response, send_response


def require_auth(client_socket, current_user):
    if current_user:
        return True

    send_response(
        client_socket,
        build_error_response(401, "Unauthorized", "Authentication required"),
    )
    return False


def require_admin(client_socket, current_user):
    if current_user and current_user.get("role") == "admin":
        return True

    send_response(
        client_socket,
        build_error_response(403, "Forbidden", "Admin access required"),
    )
    return False


def can_view_track(current_user, track):
    if not track:
        return False

    track_user_id = track[1]

    if track_user_id is None:
        return True

    if not current_user:
        return False

    if current_user.get("role") == "admin":
        return True

    return track_user_id == current_user["id"]


def can_modify_track(current_user, track):
    if not current_user or not track:
        return False

    track_user_id = track[1]

    if track_user_id is None:
        return current_user.get("role") == "admin"

    return track_user_id == current_user["id"]