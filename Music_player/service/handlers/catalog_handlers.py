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
    json_dumps,
    calculate_bytes_hash,
)


def send_cover_file(client_socket, cover_path, cover_hash, not_found_message, headers):
    if not cover_path:
        send_response(client_socket, build_error_response(404, "Not Found", not_found_message))
        return

    abs_path = os.path.abspath(cover_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Cover file not found"))
        return

    etag = f'"{cover_hash}"' if cover_hash else None
    client_etag = headers.get("if-none-match")

    if etag and client_etag == etag:
        response = build_response(
            304,
            "Not Modified",
            body=b"",
            content_type="text/plain; charset=utf-8",
            extra_headers={
                "ETag": etag,
                "Cache-Control": "no-cache"
            }
        )
        send_response(client_socket, response)
        return

    content_type = get_image_content_type(abs_path)

    with open(abs_path, "rb") as f:
        body = f.read()

    extra_headers = {
        "Cache-Control": "no-cache"
    }

    if etag:
        extra_headers["ETag"] = etag

    response = build_response(
        200,
        "OK",
        body=body,
        content_type=content_type,
        extra_headers=extra_headers
    )
    send_response(client_socket, response)


def handle_get_artists(client_socket, headers):
    artists = db.get_all_artists()

    payload = {
        "status": "success",
        "artists": artists,
    }

    artists_bytes = "\n".join(artists).encode("utf-8")
    etag_hash = calculate_bytes_hash(artists_bytes)
    etag = f'"{etag_hash[:16]}"'

    client_etag = headers.get("if-none-match")

    if etag and client_etag == etag:
        response = build_response(
            304,
            "Not Modified",
            body=b"",
            content_type="application/json; charset=utf-8",
            extra_headers={
                "ETag": etag,
                "Cache-Control": "no-cache",
            },
        )
        send_response(client_socket, response)
        return

    body = json_dumps(payload)
    response = build_response(
        200,
        "OK",
        body=body,
        content_type="application/json; charset=utf-8",
        extra_headers={
            "ETag": etag,
            "Cache-Control": "no-cache",
        },
    )

    send_response(client_socket, response)

def handle_get_artist(client_socket, artist_id, headers):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(
            client_socket,
            build_error_response(404, "Not Found", "Artist not found"),
        )
        return

    payload = {
        "status": "success",
        "artist": artist_to_dict(artist),
    }

    body = json_dumps(payload)
    etag_hash = calculate_bytes_hash(body)
    etag = f'"{etag_hash[:16]}"'

    client_etag = headers.get("if-none-match")

    if client_etag == etag:
        response = build_response(
            304,
            "Not Modified",
            body=b"",
            content_type="application/json; charset=utf-8",
            extra_headers={
                "ETag": etag,
                "Cache-Control": "no-cache",
            },
        )
        send_response(client_socket, response)
        return

    response = build_response(
        200,
        "OK",
        body=body,
        content_type="application/json; charset=utf-8",
        extra_headers={
            "ETag": etag,
            "Cache-Control": "no-cache",
        },
    )
    send_response(client_socket, response)

def handle_get_artist_tracks(client_socket, artist_id, headers):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(
            client_socket,
            build_error_response(404, "Not Found", "Artist not found"),
        )
        return

    tracks = db.get_tracks_by_artist_id(artist_id)

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    body = json_dumps(payload)
    etag_hash = calculate_bytes_hash(body)
    etag = f'"{etag_hash[:16]}"'

    client_etag = headers.get("if-none-match")

    if client_etag == etag:
        response = build_response(
            304,
            "Not Modified",
            body=b"",
            content_type="application/json; charset=utf-8",
            extra_headers={
                "ETag": etag,
                "Cache-Control": "no-cache",
            },
        )
        send_response(client_socket, response)
        return

    response = build_response(
        200,
        "OK",
        body=body,
        content_type="application/json; charset=utf-8",
        extra_headers={
            "ETag": etag,
            "Cache-Control": "no-cache",
        },
    )
    send_response(client_socket, response)

def handle_get_artist_albums(client_socket, artist_id, headers):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(
            client_socket,
            build_error_response(404, "Not Found", "Artist not found"),
        )
        return

    albums = db.get_albums_by_artist(artist_id)

    payload = {
        "status": "success",
        "albums": [album_to_dict(album) for album in albums],
    }

    body = json_dumps(payload)
    etag_hash = calculate_bytes_hash(body)
    etag = f'"{etag_hash[:16]}"'

    client_etag = headers.get("if-none-match")

    if client_etag == etag:
        response = build_response(
            304,
            "Not Modified",
            body=b"",
            content_type="application/json; charset=utf-8",
            extra_headers={
                "ETag": etag,
                "Cache-Control": "no-cache",
            },
        )
        send_response(client_socket, response)
        return

    response = build_response(
        200,
        "OK",
        body=body,
        content_type="application/json; charset=utf-8",
        extra_headers={
            "ETag": etag,
            "Cache-Control": "no-cache",
        },
    )
    send_response(client_socket, response)

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


def handle_artist_cover(client_socket, artist_id, headers):
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    cover_path = artist[3]
    cover_hash = artist[4]

    send_cover_file(client_socket, cover_path, cover_hash, "Artist cover not found", headers)


def handle_album_cover(client_socket, album_id, headers):
    album = db.get_album_by_id(album_id)

    if not album:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    cover_path = album[5]
    cover_hash = album[6]

    send_cover_file(client_socket, cover_path, cover_hash, "Album cover not found", headers)


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

def handle_home_data(client_socket, current_user):
    if not current_user:
        tracks = db.get_all_tracks(only_public=True)
    else:
        tracks = db.get_all_tracks(
            user_id=current_user["id"],
            only_public=True
        )

    artists = db.get_all_artists()

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
        "artists": artists,
    }

    send_response(
        client_socket,
        build_json_response(200, "OK", payload)
    )