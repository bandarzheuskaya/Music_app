# service/serializers.py

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