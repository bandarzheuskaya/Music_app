import service.database as db

from service.file_service import remove_unused_cover_file
from service.permissions import require_auth, require_admin, can_modify_track
from service.utils import (
    build_error_response,
    build_json_response,
    log_info,
    send_response,
)


def handle_delete_cover(client_socket, entity_type, entity_id, current_user):
    if entity_type in ("album", "artist"):
        if not require_admin(client_socket, current_user):
            return

    if entity_type == "track":
        if not require_auth(client_socket, current_user):
            return

    if entity_type == "track":
        row = db.get_track_by_id(entity_id)

        if not row:
            send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
            return

        if not can_modify_track(current_user, row):
            send_response(
                client_socket,
                build_error_response(403, "Forbidden", "You cannot delete this cover"),
            )
            return

        cover_path = row[11]
        cover_hash = row[12]
        delete_db_cover = db.delete_track_cover

    elif entity_type == "album":
        row = db.get_album_by_id(entity_id)

        if not row:
            send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
            return

        cover_path = row[5]
        cover_hash = row[6]
        delete_db_cover = db.delete_album_cover

    elif entity_type == "artist":
        row = db.get_artist_by_id(entity_id)

        if not row:
            send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
            return

        cover_path = row[3]
        cover_hash = row[4]
        delete_db_cover = db.delete_artist_cover

    else:
        send_response(client_socket, build_error_response(400, "Bad Request", "Invalid cover type"))
        return

    delete_db_cover(entity_id)

    remove_unused_cover_file(cover_path, cover_hash)

    log_info(f"Cover deleted: {entity_type}/{entity_id}, user={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Cover deleted",
        "type": entity_type,
        "id": entity_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))