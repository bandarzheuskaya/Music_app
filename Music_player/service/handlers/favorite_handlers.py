import service.database as db

from service.permissions import require_auth, can_view_track
from service.serializers import track_to_dict
from service.utils import (
    build_error_response,
    build_json_response,
    send_response,
)


def handle_get_favorites(client_socket, current_user):
    if not require_auth(client_socket, current_user):
        return

    tracks = db.get_favorite_tracks(current_user["id"])

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_add_favorite(client_socket, track_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    db.add_to_favorites(current_user["id"], track_id)

    payload = {
        "status": "success",
        "message": "Track added to favorites",
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_remove_favorite(client_socket, track_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    db.remove_from_favorites(current_user["id"], track_id)

    payload = {
        "status": "success",
        "message": "Track removed from favorites",
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))