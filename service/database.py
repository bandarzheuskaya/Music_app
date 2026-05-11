import psycopg

from service.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD
}


TRACK_SELECT_SQL = """
    SELECT
        t.id,
        t.user_id,
        t.artist_id,
        t.album_id,
        t.title,
        t.artist,
        t.source_type,
        t.filename,
        t.file_path,
        t.file_hash,
        t.cover_filename,
        t.cover_path,
        t.cover_hash,
        t.external_url,
        t.external_id,
        t.uploaded_at,
        a.name AS artist_name,
        al.title AS album_title,
        al.cover_filename AS album_cover_filename,
        al.cover_path AS album_cover_path,
        al.cover_hash AS album_cover_hash
    FROM tracks t
    LEFT JOIN artists a ON t.artist_id = a.id
    LEFT JOIN albums al ON t.album_id = al.id
"""


def get_connection():
    return psycopg.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    email VARCHAR(255) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    session_token VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS artists (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL UNIQUE,
                    cover_filename VARCHAR(255),
                    cover_path VARCHAR(500),
                    cover_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS albums (
                    id SERIAL PRIMARY KEY,
                    artist_id INTEGER NOT NULL REFERENCES artists(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    year INTEGER,
                    cover_filename VARCHAR(255),
                    cover_path VARCHAR(500),
                    cover_hash VARCHAR(64),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (artist_id, title)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    artist_id INTEGER REFERENCES artists(id) ON DELETE SET NULL,
                    album_id INTEGER REFERENCES albums(id) ON DELETE SET NULL,
                    title VARCHAR(255) NOT NULL,
                    artist VARCHAR(255) NOT NULL,
                    source_type VARCHAR(20) NOT NULL DEFAULT 'local',
                    filename VARCHAR(255),
                    file_path VARCHAR(500),
                    file_hash VARCHAR(64),
                    cover_filename VARCHAR(255),
                    cover_path VARCHAR(500),
                    cover_hash VARCHAR(64),
                    external_url VARCHAR(1000),
                    external_id VARCHAR(255),
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS favorites (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (user_id, track_id)
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id SERIAL PRIMARY KEY,
                    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE (playlist_id, track_id)
                );
            """)

            cur.execute("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'user';
            """)

            cur.execute("""
                ALTER TABLE tracks
                ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);
            """)

            cur.execute("""
                ALTER TABLE tracks
                ADD COLUMN IF NOT EXISTS cover_hash VARCHAR(64);
            """)

            cur.execute("""
                ALTER TABLE albums
                ADD COLUMN IF NOT EXISTS cover_hash VARCHAR(64);
            """)

            cur.execute("""
                ALTER TABLE artists
                ADD COLUMN IF NOT EXISTS cover_hash VARCHAR(64);
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    message TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        conn.commit()


# =========================
# USERS
# =========================

def create_user(username, email, password_hash, role="user"):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, email, password_hash, role))
            user_id = cur.fetchone()[0]
        conn.commit()
        return user_id


def get_user_by_id(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, role, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            return cur.fetchone()


def get_user_by_username(username):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, role, created_at
                FROM users
                WHERE username = %s
            """, (username,))
            return cur.fetchone()


def get_user_by_email(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, role, created_at
                FROM users
                WHERE email = %s
            """, (email,))
            return cur.fetchone()


def get_user_by_login(login_value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, role, created_at
                FROM users
                WHERE username = %s
            """, (login_value,))
            return cur.fetchone()


def delete_user(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM users
                WHERE id = %s
            """, (user_id,))
        conn.commit()


# =========================
# SESSIONS
# =========================

def create_session(user_id, session_token, expires_at):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO sessions (user_id, session_token, expires_at)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (user_id, session_token, expires_at))
            session_id = cur.fetchone()[0]
        conn.commit()
        return session_id


def get_session_by_token(session_token):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, session_token, created_at, expires_at
                FROM sessions
                WHERE session_token = %s
            """, (session_token,))
            return cur.fetchone()


def delete_session(session_token):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM sessions
                WHERE session_token = %s
            """, (session_token,))
        conn.commit()


def delete_expired_sessions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM sessions
                WHERE expires_at < CURRENT_TIMESTAMP
            """)
        conn.commit()


# =========================
# ARTISTS
# =========================

def create_artist(name, cover_filename=None, cover_path=None, cover_hash=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO artists (name, cover_filename, cover_path, cover_hash)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
            """, (name, cover_filename, cover_path, cover_hash))
            artist_id = cur.fetchone()[0]
        conn.commit()
        return artist_id


def get_artist_by_id(artist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, cover_filename, cover_path, cover_hash, created_at
                FROM artists
                WHERE id = %s
            """, (artist_id,))
            return cur.fetchone()


def get_artist_by_name(name):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, cover_filename, cover_path, cover_hash, created_at
                FROM artists
                WHERE name = %s
            """, (name,))
            return cur.fetchone()


def get_all_artists_full():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, cover_filename, cover_path, cover_hash, created_at
                FROM artists
                ORDER BY name
            """)
            return cur.fetchall()


def get_all_artists():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT name
                FROM artists
                WHERE name IS NOT NULL
                  AND TRIM(name) <> ''
                ORDER BY name
            """)
            rows = cur.fetchall()
            return [row[0] for row in rows]


def update_artist_cover(artist_id, cover_filename, cover_path, cover_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE artists
                SET cover_filename = %s,
                    cover_path = %s,
                    cover_hash = %s
                WHERE id = %s
            """, (cover_filename, cover_path, cover_hash, artist_id))
        conn.commit()


def delete_artist_cover(artist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE artists
                SET cover_filename = NULL,
                    cover_path = NULL,
                    cover_hash = NULL
                WHERE id = %s
            """, (artist_id,))
        conn.commit()


# =========================
# ALBUMS
# =========================

def create_album(artist_id, title, year=None, cover_filename=None, cover_path=None, cover_hash=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO albums (
                    artist_id,
                    title,
                    year,
                    cover_filename,
                    cover_path,
                    cover_hash
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (artist_id, title) DO UPDATE
                SET year = COALESCE(EXCLUDED.year, albums.year)
                RETURNING id
            """, (artist_id, title, year, cover_filename, cover_path, cover_hash))
            album_id = cur.fetchone()[0]
        conn.commit()
        return album_id


def get_album_by_id(album_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, artist_id, title, year, cover_filename, cover_path, cover_hash, created_at
                FROM albums
                WHERE id = %s
            """, (album_id,))
            return cur.fetchone()


def get_album_by_artist_and_title(artist_id, title):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, artist_id, title, year, cover_filename, cover_path, cover_hash, created_at
                FROM albums
                WHERE artist_id = %s AND title = %s
            """, (artist_id, title))
            return cur.fetchone()


def get_albums_by_artist(artist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, artist_id, title, year, cover_filename, cover_path, cover_hash, created_at
                FROM albums
                WHERE artist_id = %s
                ORDER BY title
            """, (artist_id,))
            return cur.fetchall()


def get_all_album_titles():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT title
                FROM albums
                WHERE title IS NOT NULL
                  AND TRIM(title) <> ''
                ORDER BY title
            """)
            rows = cur.fetchall()
            return [row[0] for row in rows]


def update_album(album_id, title, year=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE albums
                SET title = %s,
                    year = %s
                WHERE id = %s
            """, (title, year, album_id))
        conn.commit()


def update_album_cover(album_id, cover_filename, cover_path, cover_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE albums
                SET cover_filename = %s,
                    cover_path = %s,
                    cover_hash = %s
                WHERE id = %s
            """, (cover_filename, cover_path, cover_hash, album_id))
        conn.commit()


def delete_album_cover(album_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE albums
                SET cover_filename = NULL,
                    cover_path = NULL,
                    cover_hash = NULL
                WHERE id = %s
            """, (album_id,))
        conn.commit()


# =========================
# TRACKS
# =========================

def add_track(
    title,
    artist,
    user_id=None,
    artist_id=None,
    album_id=None,
    source_type="local",
    filename=None,
    file_path=None,
    file_hash=None,
    cover_filename=None,
    cover_path=None,
    cover_hash=None,
    external_url=None,
    external_id=None
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tracks (
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
                    external_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
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
                external_id
            ))
            track_id = cur.fetchone()[0]
        conn.commit()
        return track_id


def get_track_by_id(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                WHERE t.id = %s
            """, (track_id,))
            return cur.fetchone()


def get_all_tracks(user_id=None, only_public=False, only_mine=False):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if only_public or user_id is None:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE t.user_id IS NULL
                    ORDER BY t.id DESC
                """)
            elif only_mine:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE t.user_id = %s
                    ORDER BY t.id DESC
                """, (user_id,))
            else:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE t.user_id IS NULL OR t.user_id = %s
                    ORDER BY t.id DESC
                """, (user_id,))

            return cur.fetchall()


def search_tracks(query, user_id=None, only_public=False, only_mine=False):
    query = (query or "").strip()

    if not query:
        return get_all_tracks(
            user_id=user_id,
            only_public=only_public,
            only_mine=only_mine
        )

    pattern = f"%{query}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            if only_public or user_id is None:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE t.user_id IS NULL
                      AND (
                          t.title ILIKE %s
                          OR t.artist ILIKE %s
                          OR al.title ILIKE %s
                      )
                    ORDER BY t.id DESC
                """, (pattern, pattern, pattern))
            elif only_mine:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE t.user_id = %s
                      AND (
                          t.title ILIKE %s
                          OR t.artist ILIKE %s
                          OR al.title ILIKE %s
                      )
                    ORDER BY t.id DESC
                """, (user_id, pattern, pattern, pattern))
            else:
                cur.execute(TRACK_SELECT_SQL + """
                    WHERE (t.user_id IS NULL OR t.user_id = %s)
                      AND (
                          t.title ILIKE %s
                          OR t.artist ILIKE %s
                          OR al.title ILIKE %s
                      )
                    ORDER BY t.id DESC
                """, (user_id, pattern, pattern, pattern))

            return cur.fetchall()


def get_tracks_by_artist_id(artist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                WHERE t.artist_id = %s
                  AND t.user_id IS NULL
                ORDER BY t.id DESC
            """, (artist_id,))
            return cur.fetchall()


def get_tracks_by_album_id(album_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                WHERE t.album_id = %s
                  AND t.user_id IS NULL
                ORDER BY t.id ASC
            """, (album_id,))
            return cur.fetchall()


def update_track(track_id, title, artist, artist_id=None, album_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tracks
                SET title = %s,
                    artist = %s,
                    artist_id = %s,
                    album_id = %s
                WHERE id = %s
            """, (title, artist, artist_id, album_id, track_id))
        conn.commit()


def update_track_cover(track_id, cover_filename, cover_path, cover_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tracks
                SET cover_filename = %s,
                    cover_path = %s,
                    cover_hash = %s
                WHERE id = %s
            """, (cover_filename, cover_path, cover_hash, track_id))
        conn.commit()


def delete_track_cover(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tracks
                SET cover_filename = NULL,
                    cover_path = NULL,
                    cover_hash = NULL
                WHERE id = %s
            """, (track_id,))
        conn.commit()


def delete_track(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM tracks
                WHERE id = %s
            """, (track_id,))
        conn.commit()


def user_has_track_with_title(user_id, title, exclude_track_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if exclude_track_id is None:
                cur.execute("""
                    SELECT 1
                    FROM tracks
                    WHERE user_id = %s
                      AND LOWER(title) = LOWER(%s)
                    LIMIT 1
                """, (user_id, title))
            else:
                cur.execute("""
                    SELECT 1
                    FROM tracks
                    WHERE user_id = %s
                      AND LOWER(title) = LOWER(%s)
                      AND id <> %s
                    LIMIT 1
                """, (user_id, title, exclude_track_id))

            return cur.fetchone() is not None


def public_track_exists(title, artist_id, album_id, exclude_track_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if exclude_track_id is None:
                cur.execute("""
                    SELECT 1
                    FROM tracks
                    WHERE user_id IS NULL
                      AND LOWER(title) = LOWER(%s)
                      AND artist_id = %s
                      AND album_id = %s
                    LIMIT 1
                """, (title, artist_id, album_id))
            else:
                cur.execute("""
                    SELECT 1
                    FROM tracks
                    WHERE user_id IS NULL
                      AND LOWER(title) = LOWER(%s)
                      AND artist_id = %s
                      AND album_id = %s
                      AND id <> %s
                    LIMIT 1
                """, (title, artist_id, album_id, exclude_track_id))

            return cur.fetchone() is not None


# =========================
# FILE REFERENCES
# =========================

def find_track_file_by_hash(file_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT filename, file_path, file_hash
                FROM tracks
                WHERE file_hash = %s
                  AND file_path IS NOT NULL
                LIMIT 1
            """, (file_hash,))
            return cur.fetchone()


def find_cover_by_hash(cover_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cover_filename, cover_path, cover_hash
                FROM tracks
                WHERE cover_hash = %s
                  AND cover_path IS NOT NULL
                LIMIT 1
            """, (cover_hash,))
            row = cur.fetchone()

            if row:
                return row

            cur.execute("""
                SELECT cover_filename, cover_path, cover_hash
                FROM albums
                WHERE cover_hash = %s
                  AND cover_path IS NOT NULL
                LIMIT 1
            """, (cover_hash,))
            row = cur.fetchone()

            if row:
                return row

            cur.execute("""
                SELECT cover_filename, cover_path, cover_hash
                FROM artists
                WHERE cover_hash = %s
                  AND cover_path IS NOT NULL
                LIMIT 1
            """, (cover_hash,))
            return cur.fetchone()


def count_track_file_references(file_hash):
    if not file_hash:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM tracks
                WHERE file_hash = %s
            """, (file_hash,))
            return cur.fetchone()[0]


def count_cover_references(cover_hash):
    if not cover_hash:
        return 0

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (
                        SELECT COUNT(*)
                        FROM tracks
                        WHERE cover_hash = %s
                    )
                    +
                    (
                        SELECT COUNT(*)
                        FROM albums
                        WHERE cover_hash = %s
                    )
                    +
                    (
                        SELECT COUNT(*)
                        FROM artists
                        WHERE cover_hash = %s
                    )
            """, (cover_hash, cover_hash, cover_hash))
            return cur.fetchone()[0]


# =========================
# FAVORITES
# =========================

def add_to_favorites(user_id, track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO favorites (user_id, track_id)
                VALUES (%s, %s)
                ON CONFLICT (user_id, track_id) DO NOTHING
            """, (user_id, track_id))
        conn.commit()


def remove_from_favorites(user_id, track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM favorites
                WHERE user_id = %s AND track_id = %s
            """, (user_id, track_id))
        conn.commit()


def get_favorite_tracks(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                JOIN favorites f ON f.track_id = t.id
                WHERE f.user_id = %s
                ORDER BY f.created_at DESC
            """, (user_id,))
            return cur.fetchall()


def is_favorite(user_id, track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 1
                FROM favorites
                WHERE user_id = %s AND track_id = %s
            """, (user_id, track_id))
            return cur.fetchone() is not None


# =========================
# PLAYLISTS
# =========================

def create_playlist(user_id, title):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO playlists (user_id, title)
                VALUES (%s, %s)
                RETURNING id
            """, (user_id, title))
            playlist_id = cur.fetchone()[0]
        conn.commit()
        return playlist_id


def get_playlists(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, title, created_at
                FROM playlists
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))
            return cur.fetchall()


def get_playlist_by_id(playlist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, user_id, title, created_at
                FROM playlists
                WHERE id = %s
            """, (playlist_id,))
            return cur.fetchone()


def update_playlist(playlist_id, title):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE playlists
                SET title = %s
                WHERE id = %s
            """, (title, playlist_id))
        conn.commit()


def delete_playlist(playlist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM playlists
                WHERE id = %s
            """, (playlist_id,))
        conn.commit()


def add_track_to_playlist(playlist_id, track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO playlist_tracks (playlist_id, track_id)
                VALUES (%s, %s)
                ON CONFLICT (playlist_id, track_id) DO NOTHING
            """, (playlist_id, track_id))
        conn.commit()


def remove_track_from_playlist(playlist_id, track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM playlist_tracks
                WHERE playlist_id = %s AND track_id = %s
            """, (playlist_id, track_id))
        conn.commit()


def get_playlist_tracks(playlist_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                JOIN playlist_tracks pt ON pt.track_id = t.id
                WHERE pt.playlist_id = %s
                ORDER BY pt.added_at DESC
            """, (playlist_id,))
            return cur.fetchall()

# =========================
# ADMIN
# =========================

def get_all_users():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, role, created_at
                FROM users
                ORDER BY id
            """)
            return cur.fetchall()


def update_user_role(user_id, role):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users
                SET role = %s
                WHERE id = %s
            """, (role, user_id))
        conn.commit()


def get_user_tracks(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(TRACK_SELECT_SQL + """
                WHERE t.user_id = %s
                ORDER BY t.id DESC
            """, (user_id,))
            return cur.fetchall()


def create_notification(user_id, message):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO notifications (user_id, message)
                VALUES (%s, %s)
            """, (user_id, message))
        conn.commit()


def get_notifications(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, message, is_read, created_at
                FROM notifications
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))
            return cur.fetchall()


def mark_notification_as_read(notification_id, user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE notifications
                SET is_read = TRUE
                WHERE id = %s
                  AND user_id = %s
            """, (notification_id, user_id))
        conn.commit()

if __name__ == "__main__":
    init_db()
    print("База данных инициализирована")