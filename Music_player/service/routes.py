import re

import service.auth as auth

from service.utils import (
    build_empty_response,
    build_error_response,
    send_response,
)

from service.handlers.auth_handlers import (
    handle_register,
    handle_login,
    handle_logout,
    handle_me,
)

from service.handlers.playlist_handlers import (
    handle_get_playlists,
    handle_create_playlist,
    handle_get_playlist,
    handle_update_playlist,
    handle_delete_playlist,
    handle_add_track_to_playlist,
    handle_remove_track_from_playlist,
)

from service.handlers.track_handlers import (
    handle_get_tracks,
    handle_get_track,
    handle_search_tracks,
    handle_create_track,
    handle_update_track,
    handle_delete_track,
    handle_stream_track,
    handle_cover_track,
    handle_update_track_cover,
)

from service.handlers.catalog_handlers import (
    handle_get_artists,
    handle_get_artist,
    handle_get_artist_tracks,
    handle_get_artist_albums,
    handle_get_albums,
    handle_get_album,
    handle_get_album_tracks,
    handle_create_album,
    handle_update_album,
    handle_artist_cover,
    handle_album_cover,
    handle_update_album_cover,
    handle_update_artist_cover,
)

from service.handlers.favorite_handlers import (
    handle_get_favorites,
    handle_add_favorite,
    handle_remove_favorite,
)

from service.handlers.cover_handlers import handle_delete_cover

from service.handlers.admin_handlers import (
    handle_admin_get_users,
    handle_admin_update_user_role,
    handle_admin_get_user_tracks,
    handle_admin_delete_user_track,
)

from service.handlers.notification_handlers import handle_get_notifications


def handle_static_route(
    handler,
    client_socket,
    query_params,
    headers,
    body,
    current_user,
):
    if handler in (
        handle_register,
        handle_login,
    ):
        handler(client_socket, headers, body)
        return True

    if handler == handle_logout:
        handler(client_socket, headers)
        return True

    if handler == handle_me:
        handler(client_socket, headers)
        return True

    if handler == handle_get_tracks:
        handler(client_socket, current_user, query_params)
        return True

    if handler == handle_search_tracks:
        handler(client_socket, query_params, current_user)
        return True

    if handler == handle_get_artists:
        handler(client_socket)
        return True

    if handler == handle_get_albums:
        handler(client_socket, query_params)
        return True

    if handler in (
        handle_create_album,
        handle_create_track,
        handle_create_playlist,
    ):
        handler(client_socket, headers, body, current_user)
        return True

    if handler in (
        handle_get_favorites,
        handle_get_playlists,
        handle_admin_get_users,
        handle_get_notifications,
    ):
        handler(client_socket, current_user)
        return True

    return False


STATIC_ROUTES = {
    ("POST", "/api/auth/register"): handle_register,
    ("POST", "/api/auth/login"): handle_login,
    ("POST", "/api/auth/logout"): handle_logout,
    ("GET", "/api/auth/me"): handle_me,

    ("GET", "/api/tracks"): handle_get_tracks,
    ("GET", "/api/tracks/search"): handle_search_tracks,
    ("POST", "/api/tracks"): handle_create_track,

    ("GET", "/api/artists"): handle_get_artists,

    ("GET", "/api/albums"): handle_get_albums,
    ("POST", "/api/albums"): handle_create_album,

    ("GET", "/api/favorites"): handle_get_favorites,

    ("GET", "/api/playlists"): handle_get_playlists,
    ("POST", "/api/playlists"): handle_create_playlist,

    ("GET", "/api/admin/users"): handle_admin_get_users,

    ("GET", "/api/notifications"): handle_get_notifications,
}


def dispatch_request(client_socket, method, path_only, query_params, headers, body):
    if method == "OPTIONS":
        send_response(client_socket, build_empty_response(204, "No Content"))
        return

    current_user = auth.get_current_user(headers)

    static_handler = STATIC_ROUTES.get((method, path_only))

    if static_handler:
        handled = handle_static_route(
            static_handler,
            client_socket,
            query_params,
            headers,
            body,
            current_user,
        )

        if handled:
            return

    # Избранные

    match_favorite = re.fullmatch(r"/api/favorites/(\d+)", path_only)
    if match_favorite:
        track_id = int(match_favorite.group(1))

        if method == "POST":
            handle_add_favorite(client_socket, track_id, current_user)
            return

        if method == "DELETE":
            handle_remove_favorite(client_socket, track_id, current_user)
            return

    # Плейлисты

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

    # Исполнители

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

    # Альбомы

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

    match_album_cover = re.fullmatch(r"/api/albums/(\d+)/cover", path_only)
    if match_album_cover:
        album_id = int(match_album_cover.group(1))

        if method == "GET":
            handle_album_cover(client_socket, album_id)
            return

        if method == "POST":
            handle_update_album_cover(client_socket, album_id, headers, body, current_user)
            return

    # Треки

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

    match_track_cover = re.fullmatch(r"/api/tracks/(\d+)/cover", path_only)
    if match_track_cover:
        track_id = int(match_track_cover.group(1))

        if method == "GET":
            handle_cover_track(client_socket, track_id, current_user)
            return

        if method == "POST":
            handle_update_track_cover(client_socket, track_id, headers, body, current_user)
            return

    # Обложки

    match_delete_cover = re.fullmatch(r"/api/covers/(track|album|artist)/(\d+)", path_only)
    if match_delete_cover and method == "DELETE":
        entity_type = match_delete_cover.group(1)
        entity_id = int(match_delete_cover.group(2))

        handle_delete_cover(client_socket, entity_type, entity_id, current_user)
        return

    # Админ

    match_admin_user_role = re.fullmatch(r"/api/admin/users/(\d+)/role", path_only)
    if match_admin_user_role and method == "PUT":
        user_id = int(match_admin_user_role.group(1))
        handle_admin_update_user_role(client_socket, user_id, headers, body, current_user)
        return

    match_admin_user_tracks = re.fullmatch(r"/api/admin/users/(\d+)/tracks", path_only)
    if match_admin_user_tracks and method == "GET":
        user_id = int(match_admin_user_tracks.group(1))
        handle_admin_get_user_tracks(client_socket, user_id, current_user)
        return

    match_admin_delete_track = re.fullmatch(r"/api/admin/users/(\d+)/tracks/(\d+)", path_only)
    if match_admin_delete_track and method == "DELETE":
        user_id = int(match_admin_delete_track.group(1))
        track_id = int(match_admin_delete_track.group(2))

        handle_admin_delete_user_track(client_socket, user_id, track_id, current_user)
        return

    send_response(
        client_socket,
        build_error_response(404, "Not Found", "Endpoint not found")
    )