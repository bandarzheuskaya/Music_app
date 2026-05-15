import service.database as db

from service.permissions import require_auth, can_view_track
from service.serializers import playlist_to_dict, track_to_dict
from service.utils import (
    build_empty_response,
    build_error_response,
    build_json_response,
    parse_json_body,
    send_response,
)


def handle_get_playlists(client_socket, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlists = db.get_playlists(current_user["id"])

    payload = {
        "status": "success",
        "playlists": [playlist_to_dict(playlist) for playlist in playlists],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_create_playlist(client_socket, headers, body, current_user):
    if not require_auth(client_socket, current_user):
        return

    content_type = headers.get("content-type", "")

    if "application/json" not in content_type:
        send_response(client_socket, build_error_response(415, "Unsupported Media Type", "Expected application/json"))
        return

    try:
        data = parse_json_body(body)
    except Exception:
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid JSON"))
        return

    title = str(data.get("title", "")).strip()

    if not title:
        send_response(client_socket, build_error_response(400, "Bad Request", "Playlist title is required"))
        return

    if len(title) > 255:
        send_response(client_socket, build_error_response(400, "Bad Request", "Playlist title is too long"))
        return

    playlist_id = db.create_playlist(current_user["id"], title)

    payload = {
        "status": "success",
        "message": "Playlist created",
        "playlist_id": playlist_id,
    }

    send_response(client_socket, build_json_response(201, "Created", payload))


def handle_get_playlist(client_socket, playlist_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlist = db.get_playlist_by_id(playlist_id)

    if not playlist:
        send_response(client_socket, build_error_response(404, "Not Found", "Playlist not found"))
        return

    if playlist[1] != current_user["id"]:
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    tracks = db.get_playlist_tracks(playlist_id)

    payload = {
        "status": "success",
        "playlist": playlist_to_dict(playlist),
        "tracks": [track_to_dict(track) for track in tracks if can_view_track(current_user, track)],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_update_playlist(client_socket, playlist_id, headers, body, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlist = db.get_playlist_by_id(playlist_id)

    if not playlist:
        send_response(client_socket, build_error_response(404, "Not Found", "Playlist not found"))
        return

    if playlist[1] != current_user["id"]:
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    content_type = headers.get("content-type", "")

    if "application/json" not in content_type:
        send_response(client_socket, build_error_response(415, "Unsupported Media Type", "Expected application/json"))
        return

    try:
        data = parse_json_body(body)
    except Exception:
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid JSON"))
        return

    title = str(data.get("title", "")).strip()

    if not title:
        send_response(client_socket, build_error_response(400, "Bad Request", "Playlist title is required"))
        return

    if len(title) > 255:
        send_response(client_socket, build_error_response(400, "Bad Request", "Playlist title is too long"))
        return

    db.update_playlist(playlist_id, title)

    payload = {
        "status": "success",
        "message": "Playlist updated",
        "playlist_id": playlist_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_delete_playlist(client_socket, playlist_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlist = db.get_playlist_by_id(playlist_id)

    if not playlist:
        send_response(client_socket, build_error_response(404, "Not Found", "Playlist not found"))
        return

    if playlist[1] != current_user["id"]:
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    db.delete_playlist(playlist_id)

    send_response(client_socket, build_empty_response(204, "No Content"))


def handle_add_track_to_playlist(client_socket, playlist_id, track_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlist = db.get_playlist_by_id(playlist_id)

    if not playlist:
        send_response(client_socket, build_error_response(404, "Not Found", "Playlist not found"))
        return

    if playlist[1] != current_user["id"]:
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    db.add_track_to_playlist(playlist_id, track_id)

    payload = {
        "status": "success",
        "message": "Track added to playlist",
        "playlist_id": playlist_id,
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_remove_track_from_playlist(client_socket, playlist_id, track_id, current_user):
    if not require_auth(client_socket, current_user):
        return

    playlist = db.get_playlist_by_id(playlist_id)

    if not playlist:
        send_response(client_socket, build_error_response(404, "Not Found", "Playlist not found"))
        return

    if playlist[1] != current_user["id"]:
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    db.remove_track_from_playlist(playlist_id, track_id)

    payload = {
        "status": "success",
        "message": "Track removed from playlist",
        "playlist_id": playlist_id,
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))