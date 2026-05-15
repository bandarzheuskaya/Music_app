import os

import service.database as db

from service.settings import MAX_COVER_SIZE
from service.permissions import require_admin
from service.serializers import (
    track_to_dict,
    album_to_dict,
    artist_to_dict,
)
from service.file_service import (
    save_or_reuse_cover_file,
    remove_unused_cover_file,
    get_image_content_type,
)
from service.utils import (
    build_error_response,
    build_json_response,
    build_response,
    extract_boundary,
    parse_json_body,
    parse_multipart_form_data,
    send_response,
    log_info,
    validate_cover_file,
)


def send_cover_file(client_socket, cover_path, not_found_message):
    if not cover_path:
        send_response(client_socket, build_error_response(404, "Not Found", not_found_message))
        return

    abs_path = os.path.abspath(cover_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Cover file not found"))
        return

    content_type = get_image_content_type(abs_path)

    with open(abs_path, "rb") as f:
        body = f.read()

    response = build_response(200, "OK", body=body, content_type=content_type)
    send_response(client_socket, response)


def handle_get_artists(client_socket):
    artists = db.get_all_artists()

    payload = {
        "status": "success",
        "artists": artists,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_artist(client_socket, artist_id):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    payload = {
        "status": "success",
        "artist": artist_to_dict(artist),
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_artist_tracks(client_socket, artist_id):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    tracks = db.get_tracks_by_artist_id(artist_id)

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_artist_albums(client_socket, artist_id):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    albums = db.get_albums_by_artist(artist_id)

    payload = {
        "status": "success",
        "albums": [album_to_dict(album) for album in albums],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_albums(client_socket, query_params):
    artist_name = query_params.get("artist", [""])[0].strip()

    if not artist_name:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Query parameter 'artist' is required"),
        )
        return

    artist = db.get_artist_by_name(artist_name)

    if not artist:
        payload = {
            "status": "success",
            "albums": [],
        }
        send_response(client_socket, build_json_response(200, "OK", payload))
        return

    artist_id = artist[0]
    albums = db.get_albums_by_artist(artist_id)

    payload = {
        "status": "success",
        "albums": [album_to_dict(album) for album in albums],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_album(client_socket, album_id):
    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    payload = {
        "status": "success",
        "album": album_to_dict(album),
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_album_tracks(client_socket, album_id):
    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    tracks = db.get_tracks_by_album_id(album_id)

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_create_album(client_socket, headers, body, current_user):
    if not require_admin(client_socket, current_user):
        return

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

    artist_name = str(data.get("artist", "")).strip()
    title = str(data.get("title", "")).strip()
    year_raw = data.get("year")

    if not artist_name or not title:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Fields artist and title are required"),
        )
        return

    year = None

    if year_raw not in (None, "", "null"):
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            send_response(
                client_socket,
                build_error_response(400, "Bad Request", "Year must be an integer"),
            )
            return

    artist_id = db.create_artist(artist_name)
    album_id = db.create_album(artist_id, title, year=year)

    log_info(f"Album created: {title}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Album created",
        "album_id": album_id,
    }

    send_response(client_socket, build_json_response(201, "Created", payload))


def handle_update_album(client_socket, album_id, headers, body, current_user):
    if not require_admin(client_socket, current_user):
        return

    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

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

    title = str(data.get("title", "")).strip()
    year_raw = data.get("year")

    if not title:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Field title is required"),
        )
        return

    year = None

    if year_raw not in (None, "", "null"):
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            send_response(
                client_socket,
                build_error_response(400, "Bad Request", "Year must be an integer"),
            )
            return

    db.update_album(album_id, title, year)

    log_info(f"Album updated: {album_id}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Album updated",
        "album_id": album_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_artist_cover(client_socket, artist_id):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    cover_path = artist[3]

    send_cover_file(client_socket, cover_path, "Artist cover not found")


def handle_album_cover(client_socket, album_id):
    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    cover_path = album[5]

    send_cover_file(client_socket, cover_path, "Album cover not found")


def handle_update_album_cover(client_socket, album_id, headers, body, current_user):
    if not require_admin(client_socket, current_user):
        return

    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    content_type = headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", "Expected multipart/form-data"),
        )
        return

    boundary = extract_boundary(content_type)

    if not boundary:
        send_response(client_socket, build_error_response(400, "Bad Request", "Boundary not found"))
        return

    form_data = parse_multipart_form_data(body, boundary)
    cover_data = form_data.get("cover")

    if not cover_data or not cover_data.get("filename"):
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Field cover is required"),
        )
        return

    original_cover_filename = cover_data["filename"]
    cover_content = cover_data["content"]

    is_valid, error_message = validate_cover_file(
        original_cover_filename,
        cover_content,
        MAX_COVER_SIZE,
    )

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    old_cover_path = album[5]
    old_cover_hash = album[6]

    saved_cover_filename, relative_cover_path, cover_hash = save_or_reuse_cover_file(
        original_cover_filename,
        cover_content,
    )

    db.update_album_cover(album_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash != cover_hash:
        remove_unused_cover_file(old_cover_path, old_cover_hash)

    log_info(f"Album cover updated: {album_id}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Album cover updated",
        "album_id": album_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_update_artist_cover(client_socket, artist_id, headers, body, current_user):
    if not require_admin(client_socket, current_user):
        return

    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    content_type = headers.get("content-type", "")

    if "multipart/form-data" not in content_type:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", "Expected multipart/form-data"),
        )
        return

    boundary = extract_boundary(content_type)

    if not boundary:
        send_response(client_socket, build_error_response(400, "Bad Request", "Boundary not found"))
        return

    form_data = parse_multipart_form_data(body, boundary)
    cover_data = form_data.get("cover")

    if not cover_data or not cover_data.get("filename"):
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Field cover is required"),
        )
        return

    original_cover_filename = cover_data["filename"]
    cover_content = cover_data["content"]

    is_valid, error_message = validate_cover_file(
        original_cover_filename,
        cover_content,
        MAX_COVER_SIZE,
    )

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    old_cover_path = artist[3]
    old_cover_hash = artist[4]

    saved_cover_filename, relative_cover_path, cover_hash = save_or_reuse_cover_file(
        original_cover_filename,
        cover_content,
    )

    db.update_artist_cover(artist_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash != cover_hash:
        remove_unused_cover_file(old_cover_path, old_cover_hash)

    log_info(f"Artist cover updated: {artist_id}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Artist cover updated",
        "artist_id": artist_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))