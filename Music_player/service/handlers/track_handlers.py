import os
import re

import service.database as db

from service.settings import BUFFER_SIZE, MAX_AUDIO_SIZE, MAX_COVER_SIZE

from service.permissions import (
    require_auth,
    can_view_track,
    can_modify_track,
)

from service.serializers import track_to_dict

from service.file_service import (
    save_or_reuse_audio_file,
    save_or_reuse_cover_file,
    remove_unused_audio_file,
    remove_unused_cover_file,
    guess_file_content_type,
    get_image_content_type,
)

from service.utils import (
    CLIENT_DISCONNECT_ERRORS,
    build_empty_response,
    build_error_response,
    build_json_response,
    extract_boundary,
    parse_json_body,
    parse_multipart_form_data,
    send_response,
    build_response,
    validate_audio_file,
    validate_cover_file,
    log_info,
)


def resolve_artist_and_album_ids(artist_name, album_title):
    artist_name = (artist_name or "").strip()
    album_title = (album_title or "").strip()

    if not artist_name:
        return None, None

    artist_id = db.create_artist(artist_name)

    album_id = None
    if album_title:
        album = db.get_album_by_artist_and_title(artist_id, album_title)
        if album:
            album_id = album[0]
        else:
            album_id = db.create_album(artist_id, album_title)

    return artist_id, album_id


def handle_get_tracks(client_socket, current_user, query_params):
    tracks_type = query_params.get("type", ["all"])[0]

    if not current_user:
        tracks = db.get_all_tracks(only_public=True)
    else:
        user_id = current_user["id"]

        if tracks_type == "common":
            tracks = db.get_all_tracks(user_id=user_id, only_public=True)
        elif tracks_type == "mine":
            tracks = db.get_all_tracks(user_id=user_id, only_mine=True)
        else:
            tracks = db.get_all_tracks(user_id=user_id)

    payload = {
        "status": "success",
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_get_track(client_socket, track_id, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    payload = {
        "status": "success",
        "track": track_to_dict(track),
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_search_tracks(client_socket, query_params, current_user):
    query = query_params.get("q", [""])[0]
    tracks_type = query_params.get("type", ["all"])[0]

    if not current_user:
        tracks = db.search_tracks(query, only_public=True)
    else:
        user_id = current_user["id"]

        if tracks_type == "common":
            tracks = db.search_tracks(query, user_id=user_id, only_public=True)
        elif tracks_type == "mine":
            tracks = db.search_tracks(query, user_id=user_id, only_mine=True)
        else:
            tracks = db.search_tracks(query, user_id=user_id)

    payload = {
        "status": "success",
        "query": query,
        "tracks": [track_to_dict(track) for track in tracks],
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_create_track(client_socket, headers, body, current_user):
    if not require_auth(client_socket, current_user):
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

    title = form_data.get("title", "").strip()
    artist = form_data.get("artist", "").strip()
    album = form_data.get("album", "").strip()
    file_data = form_data.get("file")

    if not title or not artist or not file_data:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Fields title, artist and file are required"),
        )
        return

    original_filename = file_data["filename"]
    file_content = file_data["content"]

    is_valid, error_message = validate_audio_file(original_filename, file_content, MAX_AUDIO_SIZE)

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    is_admin_user = current_user["role"] == "admin"

    artist_id = None
    album_id = None
    track_user_id = current_user["id"]

    if is_admin_user:
        if not album:
            send_response(
                client_socket,
                build_error_response(400, "Bad Request", "Admin track must belong to an album"),
            )
            return

        artist_id, album_id = resolve_artist_and_album_ids(artist, album)
        track_user_id = None

        if db.public_track_exists(title, artist_id, album_id):
            send_response(
                client_socket,
                build_error_response(409, "Conflict", "Public track already exists"),
            )
            return
    else:
        if db.user_has_track_with_title(current_user["id"], title):
            send_response(
                client_socket,
                build_error_response(409, "Conflict", "You already have track with this title"),
            )
            return

    saved_filename, relative_path, file_hash = save_or_reuse_audio_file(
        original_filename,
        file_content,
    )

    track_id = db.add_track(
        title=title,
        artist=artist,
        user_id=track_user_id,
        artist_id=artist_id,
        album_id=album_id,
        source_type="local",
        filename=saved_filename,
        file_path=relative_path,
        file_hash=file_hash,
        cover_filename=None,
        cover_path=None,
        cover_hash=None,
    )

    log_info(f"Track created: {title}, user_id={track_user_id}")

    payload = {
        "status": "success",
        "message": "Track created",
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(201, "Created", payload))


def handle_update_track(client_socket, track_id, headers, body, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_modify_track(current_user, track):
        send_response(
            client_socket,
            build_error_response(403, "Forbidden", "You cannot edit this track"),
        )
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
    artist = str(data.get("artist", "")).strip()
    album = str(data.get("album", "")).strip()

    if not title or not artist:
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Fields title and artist are required"),
        )
        return

    track_user_id = track[1]

    if track_user_id is None:
        if not album:
            send_response(
                client_socket,
                build_error_response(400, "Bad Request", "Public track must belong to an album"),
            )
            return

        artist_id, album_id = resolve_artist_and_album_ids(artist, album)

        if db.public_track_exists(title, artist_id, album_id, exclude_track_id=track_id):
            send_response(
                client_socket,
                build_error_response(409, "Conflict", "Public track already exists"),
            )
            return
    else:
        artist_id = None
        album_id = None

        if db.user_has_track_with_title(track_user_id, title, exclude_track_id=track_id):
            send_response(
                client_socket,
                build_error_response(409, "Conflict", "You already have track with this title"),
            )
            return

    db.update_track(track_id, title, artist, artist_id=artist_id, album_id=album_id)

    log_info(f"Track updated: {track_id}")

    payload = {
        "status": "success",
        "message": "Track updated",
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_update_track_cover(client_socket, track_id, headers, body, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_modify_track(current_user, track):
        send_response(
            client_socket,
            build_error_response(403, "Forbidden", "You cannot edit this track"),
        )
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

    old_cover_path = track[11]
    old_cover_hash = track[12]

    saved_cover_filename, relative_cover_path, cover_hash = save_or_reuse_cover_file(
        original_cover_filename,
        cover_content,
    )

    db.update_track_cover(track_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash != cover_hash:
        remove_unused_cover_file(old_cover_path, old_cover_hash)

    log_info(f"Track cover updated: {track_id}")

    payload = {
        "status": "success",
        "message": "Track cover updated",
        "track_id": track_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))


def handle_delete_track(client_socket, track_id, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_modify_track(current_user, track):
        send_response(
            client_socket,
            build_error_response(403, "Forbidden", "You cannot delete this track"),
        )
        return

    source_type = track[6]
    file_path = track[8]
    file_hash = track[9]
    cover_path = track[11]
    cover_hash = track[12]

    db.delete_track(track_id)

    if source_type == "local":
        remove_unused_audio_file(file_path, file_hash)

    remove_unused_cover_file(cover_path, cover_hash)

    log_info(f"Track deleted: {track_id}")

    send_response(client_socket, build_empty_response(204, "No Content"))


def handle_stream_track(client_socket, track_id, headers, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    source_type = track[6]
    file_path = track[8]

    if source_type != "local":
        send_response(
            client_socket,
            build_error_response(400, "Bad Request", "Only local tracks can be streamed directly"),
        )
        return

    if not file_path:
        send_response(client_socket, build_error_response(404, "Not Found", "Track file path not found"))
        return

    abs_path = os.path.abspath(file_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Track file not found"))
        return

    file_size = os.path.getsize(abs_path)
    content_type = guess_file_content_type(abs_path, default="audio/mpeg")

    range_header = headers.get("range")

    start = 0
    end = file_size - 1
    status_line = "HTTP/1.1 200 OK\r\n"

    if range_header:
        match = re.match(r"bytes=(\d*)-(\d*)", range_header)

        if not match:
            send_response(client_socket, build_error_response(416, "Range Not Satisfiable", "Invalid Range header"))
            return

        start_str, end_str = match.groups()

        if start_str == "" and end_str == "":
            send_response(client_socket, build_error_response(416, "Range Not Satisfiable", "Invalid Range values"))
            return

        if start_str != "":
            start = int(start_str)

        if end_str != "":
            end = int(end_str)

        if start_str == "" and end_str != "":
            suffix_length = int(end_str)
            start = max(file_size - suffix_length, 0)
            end = file_size - 1

        if start > end or start >= file_size:
            response = (
                "HTTP/1.1 416 Range Not Satisfiable\r\n"
                + f"Content-Range: bytes */{file_size}\r\n"
                + "Connection: close\r\n"
                + "\r\n"
            )
            client_socket.sendall(response.encode("utf-8"))
            return

        end = min(end, file_size - 1)
        status_line = "HTTP/1.1 206 Partial Content\r\n"

    content_length = end - start + 1

    response_headers = (
        status_line
        + f"Content-Type: {content_type}\r\n"
        + "Accept-Ranges: bytes\r\n"
        + f"Content-Length: {content_length}\r\n"
    )

    if range_header:
        response_headers += f"Content-Range: bytes {start}-{end}/{file_size}\r\n"

    response_headers += "Connection: close\r\n\r\n"

    try:
        client_socket.sendall(response_headers.encode("utf-8"))

        with open(abs_path, "rb") as file:
            file.seek(start)
            bytes_left = content_length

            while bytes_left > 0:
                chunk_size = min(BUFFER_SIZE, bytes_left)
                chunk = file.read(chunk_size)

                if not chunk:
                    break

                client_socket.sendall(chunk)
                bytes_left -= len(chunk)

    except CLIENT_DISCONNECT_ERRORS:
        return


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


def handle_cover_track(client_socket, track_id, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    cover_path = track[11]

    send_cover_file(client_socket, cover_path, "Cover not found")