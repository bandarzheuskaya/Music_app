import psycopg

from settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

DB_CONFIG = {
    "host": DB_HOST,
    "port": DB_PORT,
    "dbname": DB_NAME,
    "user": DB_USER,
    "password": DB_PASSWORD
}


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
                CREATE TABLE IF NOT EXISTS tracks (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    title VARCHAR(255) NOT NULL,
                    artist VARCHAR(255) NOT NULL,
                    source_type VARCHAR(20) NOT NULL DEFAULT 'local',
                    filename VARCHAR(255),
                    file_path VARCHAR(500),
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

        conn.commit()


# =========================
# USERS
# =========================

def create_user(username, email, password_hash):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (username, email, password_hash)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (username, email, password_hash))
            user_id = cur.fetchone()[0]
        conn.commit()
        return user_id


def get_user_by_id(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, created_at
                FROM users
                WHERE id = %s
            """, (user_id,))
            return cur.fetchone()


def get_user_by_username(username):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, created_at
                FROM users
                WHERE username = %s
            """, (username,))
            return cur.fetchone()


def get_user_by_email(email):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, created_at
                FROM users
                WHERE email = %s
            """, (email,))
            return cur.fetchone()


def get_user_by_login(login_value):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, username, email, password_hash, created_at
                FROM users
                WHERE username = %s OR email = %s
            """, (login_value, login_value))
            return cur.fetchone()


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
# TRACKS
# =========================

def add_track(
    title,
    artist,
    user_id=None,
    source_type="local",
    filename=None,
    file_path=None,
    external_url=None,
    external_id=None
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tracks (
                    user_id,
                    title,
                    artist,
                    source_type,
                    filename,
                    file_path,
                    external_url,
                    external_id
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                user_id,
                title,
                artist,
                source_type,
                filename,
                file_path,
                external_url,
                external_id
            ))
            track_id = cur.fetchone()[0]
        conn.commit()
        return track_id


def get_track_by_id(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    user_id,
                    title,
                    artist,
                    source_type,
                    filename,
                    file_path,
                    external_url,
                    external_id,
                    uploaded_at
                FROM tracks
                WHERE id = %s
            """, (track_id,))
            return cur.fetchone()


def get_all_tracks(user_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute("""
                    SELECT
                        id,
                        user_id,
                        title,
                        artist,
                        source_type,
                        filename,
                        file_path,
                        external_url,
                        external_id,
                        uploaded_at
                    FROM tracks
                    ORDER BY id DESC
                """)
            else:
                cur.execute("""
                    SELECT
                        id,
                        user_id,
                        title,
                        artist,
                        source_type,
                        filename,
                        file_path,
                        external_url,
                        external_id,
                        uploaded_at
                    FROM tracks
                    WHERE user_id = %s OR user_id IS NULL
                    ORDER BY id DESC
                """, (user_id,))
            return cur.fetchall()


def get_user_tracks(user_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id,
                    user_id,
                    title,
                    artist,
                    source_type,
                    filename,
                    file_path,
                    external_url,
                    external_id,
                    uploaded_at
                FROM tracks
                WHERE user_id = %s
                ORDER BY id DESC
            """, (user_id,))
            return cur.fetchall()


def search_tracks(query, user_id=None):
    query = (query or "").strip()

    if not query:
        return get_all_tracks(user_id=user_id)

    pattern = f"%{query}%"

    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute("""
                    SELECT
                        id,
                        user_id,
                        title,
                        artist,
                        source_type,
                        filename,
                        file_path,
                        external_url,
                        external_id,
                        uploaded_at
                    FROM tracks
                    WHERE title ILIKE %s
                       OR artist ILIKE %s
                    ORDER BY id DESC
                """, (pattern, pattern))
            else:
                cur.execute("""
                    SELECT
                        id,
                        user_id,
                        title,
                        artist,
                        source_type,
                        filename,
                        file_path,
                        external_url,
                        external_id,
                        uploaded_at
                    FROM tracks
                    WHERE (user_id = %s OR user_id IS NULL)
                      AND (title ILIKE %s OR artist ILIKE %s)
                    ORDER BY id DESC
                """, (user_id, pattern, pattern))
            return cur.fetchall()


def get_all_artists(user_id=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            if user_id is None:
                cur.execute("""
                    SELECT DISTINCT artist
                    FROM tracks
                    WHERE artist IS NOT NULL
                      AND TRIM(artist) <> ''
                    ORDER BY artist
                """)
            else:
                cur.execute("""
                    SELECT DISTINCT artist
                    FROM tracks
                    WHERE (user_id = %s OR user_id IS NULL)
                      AND artist IS NOT NULL
                      AND TRIM(artist) <> ''
                    ORDER BY artist
                """, (user_id,))
            rows = cur.fetchall()
            return [row[0] for row in rows]


def update_track(track_id, title, artist):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE tracks
                SET title = %s,
                    artist = %s
                WHERE id = %s
            """, (title, artist, track_id))
        conn.commit()


def delete_track(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM tracks
                WHERE id = %s
            """, (track_id,))
        conn.commit()


def get_track_owner_id(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT user_id
                FROM tracks
                WHERE id = %s
            """, (track_id,))
            row = cur.fetchone()
            return row[0] if row else None


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
            cur.execute("""
                SELECT
                    t.id,
                    t.user_id,
                    t.title,
                    t.artist,
                    t.source_type,
                    t.filename,
                    t.file_path,
                    t.external_url,
                    t.external_id,
                    t.uploaded_at
                FROM favorites f
                JOIN tracks t ON f.track_id = t.id
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
            cur.execute("""
                SELECT
                    t.id,
                    t.user_id,
                    t.title,
                    t.artist,
                    t.source_type,
                    t.filename,
                    t.file_path,
                    t.external_url,
                    t.external_id,
                    t.uploaded_at
                FROM playlist_tracks pt
                JOIN tracks t ON pt.track_id = t.id
                WHERE pt.playlist_id = %s
                ORDER BY pt.added_at DESC
            """, (playlist_id,))
            return cur.fetchall()


if __name__ == "__main__":
    init_db()
    print("База данных инициализирована")