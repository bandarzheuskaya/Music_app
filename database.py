import psycopg

DB_CONFIG ={
    'host': 'localhost',
    "port": 5432,
    "dbname": "music_service",
    "user": "postgres",
    "password": "An5498488"
}

def get_connection():
    return psycopg.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"]
    )

def get_all_tracks():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, artist, filename
                FROM tracks
                ORDER BY id DESC
            """)
            return cur.fetchall()

def get_track_by_id(track_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, title, artist, filename
                FROM tracks
                WHERE id = %s
            """, (track_id,))
            return cur.fetchone()

def add_track(title, artist, filename):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO tracks (title, artist, filename)
                VALUES (%s, %s, %s)
            """, (title, artist, filename))
        conn.commit()


if __name__ == "__main__":
    print(get_all_tracks())