import os
import re
import mimetypes
import psycopg

import service.auth as auth
import service.database as db

from service.settings import BUFFER_SIZE, UPLOAD_DIR, COVER_DIR, MAX_AUDIO_SIZE, MAX_COVER_SIZE
from service.utils import (
    CLIENT_DISCONNECT_ERRORS,
    build_empty_response,
    build_error_response,
    build_json_response,
    extract_boundary,
    make_unique_filename,
    parse_json_body,
    parse_multipart_form_data,
    send_response,
    build_delete_cookie_header,
    build_set_cookie_header,
    log_info,
    json_dumps,
    parse_cookies,
    build_response,
    calculate_bytes_hash,
    validate_audio_file,
    validate_cover_file,
    safe_remove_file,
)


def track_to_dict(track):
    if not track:
        return None

    (
        track_id,
        user_id,
        artist_id,
        album_id,
        title,
        artist,
        source_type,
        filename,
        file_path,
        file_hash,
        cover_filename,
        cover_path,
        cover_hash,
        external_url,
        external_id,
        uploaded_at,
        artist_name,
        album_title,
        album_cover_filename,
        album_cover_path,
        album_cover_hash,
    ) = track

    effective_cover_url = None

    if cover_path:
        effective_cover_url = f"/api/tracks/{track_id}/cover"
    elif album_cover_path and album_id:
        effective_cover_url = f"/api/albums/{album_id}/cover"

    return {
        "id": track_id,
        "user_id": user_id,
        "artist_id": artist_id,
        "album_id": album_id,
        "title": title,
        "artist": artist,
        "artist_name": artist_name or artist,
        "album_title": album_title,
        "source_type": source_type,
        "filename": filename,
        "file_path": file_path,
        "file_hash": file_hash,
        "cover_filename": cover_filename,
        "cover_path": cover_path,
        "cover_hash": cover_hash,
        "cover_url": f"/api/tracks/{track_id}/cover" if cover_path else None,
        "album_cover_filename": album_cover_filename,
        "album_cover_path": album_cover_path,
        "album_cover_hash": album_cover_hash,
        "album_cover_url": f"/api/albums/{album_id}/cover" if album_id and album_cover_path else None,
        "effective_cover_url": effective_cover_url,
        "external_url": external_url,
        "external_id": external_id,
        "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
        "is_public": user_id is None,
    }

def album_to_dict(album):
    if not album:
        return None

    (
        album_id,
        artist_id,
        title,
        year,
        cover_filename,
        cover_path,
        cover_hash,
        created_at,
    ) = album

    return {
        "id": album_id,
        "artist_id": artist_id,
        "title": title,
        "year": year,
        "cover_filename": cover_filename,
        "cover_path": cover_path,
        "cover_hash": cover_hash,
        "cover_url": f"/api/albums/{album_id}/cover" if cover_path else None,
        "created_at": created_at.isoformat() if created_at else None,
    }

def artist_to_dict(artist):
    if not artist:
        return None

    (
        artist_id,
        name,
        cover_filename,
        cover_path,
        cover_hash,
        created_at,
    ) = artist

    return {
        "id": artist_id,
        "name": name,
        "cover_filename": cover_filename,
        "cover_path": cover_path,
        "cover_hash": cover_hash,
        "cover_url": f"/api/artists/{artist_id}/cover" if cover_path else None,
        "created_at": created_at.isoformat() if created_at else None,
    }

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
        artist_id = None
        album_id = None

        if db.user_has_track_with_title(current_user["id"], title):
            send_response(
                client_socket,
                build_error_response(409, "Conflict", "You already have track with this title"),
            )
            return

    file_hash = calculate_bytes_hash(file_content)
    existing_file = db.find_track_file_by_hash(file_hash)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if existing_file:
        saved_filename = existing_file[0]
        relative_path = existing_file[1]
    else:
        saved_filename = make_unique_filename(UPLOAD_DIR, original_filename)
        full_path = os.path.join(UPLOAD_DIR, saved_filename)

        with open(full_path, "wb") as f:
            f.write(file_content)

        relative_path = os.path.relpath(full_path)

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

    is_valid, error_message = validate_cover_file(original_cover_filename, cover_content, MAX_COVER_SIZE)

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    old_cover_path = track[11]
    old_cover_hash = track[12]

    cover_hash = calculate_bytes_hash(cover_content)
    existing_cover = db.find_cover_by_hash(cover_hash)

    os.makedirs(COVER_DIR, exist_ok=True)

    if existing_cover:
        saved_cover_filename = existing_cover[0]
        relative_cover_path = existing_cover[1]
    else:
        saved_cover_filename = make_unique_filename(COVER_DIR, original_cover_filename)
        cover_full_path = os.path.join(COVER_DIR, saved_cover_filename)

        with open(cover_full_path, "wb") as f:
            f.write(cover_content)

        relative_cover_path = os.path.relpath(cover_full_path)

    db.update_track_cover(track_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash and old_cover_hash != cover_hash:
        cover_references_count = db.count_cover_references(old_cover_hash)

        if cover_references_count == 0:
            safe_remove_file(old_cover_path)

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

    if source_type == "local" and file_hash:
        references_count = db.count_track_file_references(file_hash)

        if references_count == 0:
            safe_remove_file(file_path)

    if cover_hash:
        cover_references_count = db.count_cover_references(cover_hash)

        if cover_references_count == 0:
            safe_remove_file(cover_path)

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
    content_type, _ = mimetypes.guess_type(abs_path)

    if not content_type:
        content_type = "audio/mpeg"

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

def handle_cover_track(client_socket, track_id, current_user):
    track = db.get_track_by_id(track_id)

    if not track:
        send_response(client_socket, build_error_response(404, "Not Found", "Track not found"))
        return

    if not can_view_track(current_user, track):
        send_response(client_socket, build_error_response(403, "Forbidden", "Access denied"))
        return

    cover_path = track[11]

    if not cover_path:
        send_response(client_socket, build_error_response(404, "Not Found", "Cover not found"))
        return

    abs_path = os.path.abspath(cover_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Cover file not found"))
        return

    ext = os.path.splitext(abs_path)[1].lower()
    content_type = "image/jpeg"

    if ext == ".png":
        content_type = "image/png"
    elif ext == ".webp":
        content_type = "image/webp"

    with open(abs_path, "rb") as f:
        body = f.read()

    response = build_response(200, "OK", body=body, content_type=content_type)
    send_response(client_socket, response)

def handle_artist_cover(client_socket, artist_id):
    artist_row = db.get_artist_by_id(artist_id)

    if not artist_row:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist not found"))
        return

    cover_path = artist_row[3]

    if not cover_path:
        send_response(client_socket, build_error_response(404, "Not Found", "Artist cover not found"))
        return

    abs_path = os.path.abspath(cover_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Artist cover file not found"))
        return

    ext = os.path.splitext(abs_path)[1].lower()
    content_type = "image/jpeg"

    if ext == ".png":
        content_type = "image/png"
    elif ext == ".webp":
        content_type = "image/webp"

    with open(abs_path, "rb") as f:
        body = f.read()

    response = build_response(200, "OK", body=body, content_type=content_type)
    send_response(client_socket, response)

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
        MAX_COVER_SIZE
    )

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    old_cover_path = album[5]
    old_cover_hash = album[6]

    cover_hash = calculate_bytes_hash(cover_content)
    existing_cover = db.find_cover_by_hash(cover_hash)

    os.makedirs(COVER_DIR, exist_ok=True)

    if existing_cover:
        saved_cover_filename = existing_cover[0]
        relative_cover_path = existing_cover[1]
    else:
        saved_cover_filename = make_unique_filename(COVER_DIR, original_cover_filename)
        cover_full_path = os.path.join(COVER_DIR, saved_cover_filename)

        with open(cover_full_path, "wb") as f:
            f.write(cover_content)

        relative_cover_path = os.path.relpath(cover_full_path)

    db.update_album_cover(album_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash and old_cover_hash != cover_hash:
        references_count = db.count_cover_references(old_cover_hash)

        if references_count == 0:
            safe_remove_file(old_cover_path)

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
        MAX_COVER_SIZE
    )

    if not is_valid:
        send_response(
            client_socket,
            build_error_response(415, "Unsupported Media Type", error_message),
        )
        return

    old_cover_path = artist[3]
    old_cover_hash = artist[4]

    cover_hash = calculate_bytes_hash(cover_content)
    existing_cover = db.find_cover_by_hash(cover_hash)

    os.makedirs(COVER_DIR, exist_ok=True)

    if existing_cover:
        saved_cover_filename = existing_cover[0]
        relative_cover_path = existing_cover[1]
    else:
        saved_cover_filename = make_unique_filename(COVER_DIR, original_cover_filename)
        cover_full_path = os.path.join(COVER_DIR, saved_cover_filename)

        with open(cover_full_path, "wb") as f:
            f.write(cover_content)

        relative_cover_path = os.path.relpath(cover_full_path)

    db.update_artist_cover(artist_id, saved_cover_filename, relative_cover_path, cover_hash)

    if old_cover_hash and old_cover_hash != cover_hash:
        references_count = db.count_cover_references(old_cover_hash)

        if references_count == 0:
            safe_remove_file(old_cover_path)

    log_info(f"Artist cover updated: {artist_id}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Artist cover updated",
        "artist_id": artist_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))

def handle_album_cover(client_socket, album_id):
    album_row = db.get_album_by_id(album_id)

    if not album_row:
        send_response(client_socket, build_error_response(404, "Not Found", "Album not found"))
        return

    cover_path = album_row[5]

    if not cover_path:
        send_response(client_socket, build_error_response(404, "Not Found", "Album cover not found"))
        return

    abs_path = os.path.abspath(cover_path)

    if not os.path.exists(abs_path):
        send_response(client_socket, build_error_response(404, "Not Found", "Album cover file not found"))
        return

    ext = os.path.splitext(abs_path)[1].lower()
    content_type = "image/jpeg"

    if ext == ".png":
        content_type = "image/png"
    elif ext == ".webp":
        content_type = "image/webp"

    with open(abs_path, "rb") as f:
        body = f.read()

    response = build_response(200, "OK", body=body, content_type=content_type)
    send_response(client_socket, response)

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

    if cover_hash:
        references_count = db.count_cover_references(cover_hash)

        if references_count == 0:
            safe_remove_file(cover_path)

    log_info(f"Cover deleted: {entity_type}/{entity_id}, admin={current_user['username']}")

    payload = {
        "status": "success",
        "message": "Cover deleted",
        "type": entity_type,
        "id": entity_id,
    }

    send_response(client_socket, build_json_response(200, "OK", payload))

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

    response = build_json_response(
        200,
        "OK",
        payload,
    )

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

def playlist_to_dict(playlist):
    if not playlist:
        return None

    playlist_id, user_id, title, created_at = playlist

    return {
        "id": playlist_id,
        "user_id": user_id,
        "title": title,
        "created_at": created_at.isoformat() if created_at else None,
    }


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

def user_to_admin_dict(row):
    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "role": row[3],
        "created_at": row[4].isoformat() if row[4] else None,
    }


def notification_to_dict(row):
    return {
        "id": row[0],
        "message": row[1],
        "is_read": row[2],
        "created_at": row[3].isoformat() if row[3] else None,
    }

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

def handle_get_notifications(client_socket, current_user):
    if not require_auth(client_socket, current_user):
        return

    notifications = db.get_notifications(current_user["id"])

    payload = {
        "status": "success",
        "notifications": [
            notification_to_dict(n)
            for n in notifications
        ],
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

def dispatch_request(client_socket, method, path_only, query_params, headers, body):
    if method == "OPTIONS":
        send_response(client_socket, build_empty_response(204, "No Content"))
        return

    current_user = auth.get_current_user(headers)

    if method == "GET" and path_only == "/api/tracks":
        handle_get_tracks(client_socket, current_user, query_params)
        return

    if method == "GET" and path_only == "/api/tracks/search":
        handle_search_tracks(client_socket, query_params, current_user)
        return

    if method == "GET" and path_only == "/api/artists":
        handle_get_artists(client_socket)
        return

    if method == "GET" and path_only == "/api/albums":
        handle_get_albums(client_socket, query_params)
        return

    if method == "POST" and path_only == "/api/albums":
        handle_create_album(client_socket, headers, body, current_user)
        return

    if method == "POST" and path_only == "/api/tracks":
        handle_create_track(client_socket, headers, body, current_user)
        return

    if method == "POST" and path_only == "/api/auth/register":
        handle_register(client_socket, headers, body)
        return

    if method == "POST" and path_only == "/api/auth/login":
        handle_login(client_socket, headers, body)
        return

    if method == "POST" and path_only == "/api/auth/logout":
        handle_logout(client_socket, headers)
        return

    if method == "GET" and path_only == "/api/auth/me":
        handle_me(client_socket, headers)
        return

    if method == "GET" and path_only == "/api/favorites":
        handle_get_favorites(client_socket, current_user)
        return

    match_favorite = re.fullmatch(r"/api/favorites/(\d+)", path_only)
    if match_favorite:
        track_id = int(match_favorite.group(1))

        if method == "POST":
            handle_add_favorite(client_socket, track_id, current_user)
            return

        if method == "DELETE":
            handle_remove_favorite(client_socket, track_id, current_user)
            return

    if method == "GET" and path_only == "/api/playlists":
        handle_get_playlists(client_socket, current_user)
        return

    if method == "POST" and path_only == "/api/playlists":
        handle_create_playlist(client_socket, headers, body, current_user)
        return

    match_playlist = re.fullmatch(r"/api/playlists/(\d+)", path_only)
    if match_playlist:
        playlist_id = int(match_playlist.group(1))

        if method == "GET":
            handle_get_playlist(client_socket, playlist_id, current_user)
            return

        if method == "PUT":
            handle_update_playlist(client_socket, playlist_id, headers, body, current_user)
            return

        if method == "DELETE":
            handle_delete_playlist(client_socket, playlist_id, current_user)
            return

    match_playlist_track = re.fullmatch(r"/api/playlists/(\d+)/tracks/(\d+)", path_only)
    if match_playlist_track:
        playlist_id = int(match_playlist_track.group(1))
        track_id = int(match_playlist_track.group(2))

        if method == "POST":
            handle_add_track_to_playlist(client_socket, playlist_id, track_id, current_user)
            return

        if method == "DELETE":
            handle_remove_track_from_playlist(client_socket, playlist_id, track_id, current_user)
            return

    match_artist = re.fullmatch(r"/api/artists/(\d+)", path_only)
    if match_artist and method == "GET":
        artist_id = int(match_artist.group(1))
        handle_get_artist(client_socket, artist_id)
        return

    match_artist_tracks = re.fullmatch(r"/api/artists/(\d+)/tracks", path_only)
    if match_artist_tracks and method == "GET":
        artist_id = int(match_artist_tracks.group(1))
        handle_get_artist_tracks(client_socket, artist_id)
        return

    match_artist_albums = re.fullmatch(r"/api/artists/(\d+)/albums", path_only)
    if match_artist_albums and method == "GET":
        artist_id = int(match_artist_albums.group(1))
        handle_get_artist_albums(client_socket, artist_id)
        return

    match_artist_cover = re.fullmatch(r"/api/artists/(\d+)/cover", path_only)
    if match_artist_cover:
        artist_id = int(match_artist_cover.group(1))

        if method == "GET":
            handle_artist_cover(client_socket, artist_id)
            return

        if method == "POST":
            handle_update_artist_cover(client_socket, artist_id, headers, body, current_user)
            return

    match_delete_cover = re.fullmatch(r"/api/covers/(track|album|artist)/(\d+)", path_only)
    if match_delete_cover and method == "DELETE":
        entity_type = match_delete_cover.group(1)
        entity_id = int(match_delete_cover.group(2))

        handle_delete_cover(client_socket, entity_type, entity_id, current_user)
        return

    match_album = re.fullmatch(r"/api/albums/(\d+)", path_only)
    if match_album:
        album_id = int(match_album.group(1))

        if method == "GET":
            handle_get_album(client_socket, album_id)
            return

        if method == "PUT":
            handle_update_album(client_socket, album_id, headers, body, current_user)
            return

    match_album_tracks = re.fullmatch(r"/api/albums/(\d+)/tracks", path_only)
    if match_album_tracks and method == "GET":
        album_id = int(match_album_tracks.group(1))
        handle_get_album_tracks(client_socket, album_id)
        return

    match_track = re.fullmatch(r"/api/tracks/(\d+)", path_only)
    if match_track:
        track_id = int(match_track.group(1))

        if method == "GET":
            handle_get_track(client_socket, track_id, current_user)
            return

        if method == "PUT":
            handle_update_track(client_socket, track_id, headers, body, current_user)
            return

        if method == "DELETE":
            handle_delete_track(client_socket, track_id, current_user)
            return

    match_stream = re.fullmatch(r"/api/tracks/(\d+)/stream", path_only)
    if match_stream and method == "GET":
        track_id = int(match_stream.group(1))
        handle_stream_track(client_socket, track_id, headers, current_user)
        return

    match_cover = re.fullmatch(r"/api/tracks/(\d+)/cover", path_only)
    if match_cover:
        track_id = int(match_cover.group(1))

        if method == "GET":
            handle_cover_track(client_socket, track_id, current_user)
            return

        if method == "POST":
            handle_update_track_cover(client_socket, track_id, headers, body, current_user)
            return

    match_album_cover = re.fullmatch(r"/api/albums/(\d+)/cover", path_only)
    if match_album_cover:
        album_id = int(match_album_cover.group(1))

        if method == "GET":
            handle_album_cover(client_socket, album_id)
            return

        if method == "POST":
            handle_update_album_cover(client_socket, album_id, headers, body, current_user)
            return

    if method == "GET" and path_only == "/api/admin/users":
        handle_admin_get_users(client_socket, current_user)
        return

    match_admin_user_role = re.fullmatch(
        r"/api/admin/users/(\d+)/role",
        path_only
    )

    if match_admin_user_role and method == "PUT":
        user_id = int(match_admin_user_role.group(1))

        handle_admin_update_user_role(
            client_socket,
            user_id,
            headers,
            body,
            current_user
        )
        return

    match_admin_user_tracks = re.fullmatch(
        r"/api/admin/users/(\d+)/tracks",
        path_only
    )

    if match_admin_user_tracks and method == "GET":
        user_id = int(match_admin_user_tracks.group(1))

        handle_admin_get_user_tracks(
            client_socket,
            user_id,
            current_user
        )
        return

    match_admin_delete_track = re.fullmatch(
        r"/api/admin/users/(\d+)/tracks/(\d+)",
        path_only
    )

    if match_admin_delete_track and method == "DELETE":
        user_id = int(match_admin_delete_track.group(1))
        track_id = int(match_admin_delete_track.group(2))

        handle_admin_delete_user_track(
            client_socket,
            user_id,
            track_id,
            current_user
        )
        return

    if method == "GET" and path_only == "/api/notifications":
        handle_get_notifications(client_socket, current_user)
        return

    send_response(client_socket, build_error_response(404, "Not Found", "Endpoint not found"))