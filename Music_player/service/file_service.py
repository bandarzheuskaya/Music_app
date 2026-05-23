import os
import mimetypes

import service.database as db

from service.settings import UPLOAD_DIR, COVER_DIR
from service.utils import (
    calculate_bytes_hash,
    calculate_file_hash,
    make_unique_filename,
    safe_remove_file,
)


def find_existing_file_on_disk_by_hash(directory, file_hash):
    if not file_hash or not os.path.isdir(directory):
        return None

    for root, _dirs, files in os.walk(directory):
        for filename in files:
            full_path = os.path.join(root, filename)

            try:
                if calculate_file_hash(full_path) == file_hash:
                    return filename, os.path.relpath(full_path), file_hash
            except OSError:
                continue

    return None


def save_or_reuse_audio_file(original_filename, file_content):
    file_hash = calculate_bytes_hash(file_content)
    existing_file = db.find_track_file_by_hash(file_hash)

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if existing_file:
        return existing_file[0], existing_file[1], file_hash

    existing_file_on_disk = find_existing_file_on_disk_by_hash(UPLOAD_DIR, file_hash)

    if existing_file_on_disk:
        return existing_file_on_disk

    saved_filename = make_unique_filename(UPLOAD_DIR, original_filename)
    full_path = os.path.join(UPLOAD_DIR, saved_filename)

    with open(full_path, "wb") as f:
        f.write(file_content)

    relative_path = os.path.relpath(full_path)

    return saved_filename, relative_path, file_hash


def save_or_reuse_cover_file(original_filename, cover_content):
    cover_hash = calculate_bytes_hash(cover_content)
    existing_cover = db.find_cover_by_hash(cover_hash)

    os.makedirs(COVER_DIR, exist_ok=True)

    if existing_cover:
        return existing_cover[0], existing_cover[1], cover_hash

    saved_filename = make_unique_filename(COVER_DIR, original_filename)
    full_path = os.path.join(COVER_DIR, saved_filename)

    with open(full_path, "wb") as f:
        f.write(cover_content)

    relative_path = os.path.relpath(full_path)

    return saved_filename, relative_path, cover_hash


def remove_unused_audio_file(file_path, file_hash):
    if not file_hash:
        return

    references_count = db.count_track_file_references(file_hash)

    if references_count == 0:
        safe_remove_file(file_path)


def remove_unused_cover_file(cover_path, cover_hash):
    if not cover_hash:
        return

    references_count = db.count_cover_references(cover_hash)

    if references_count == 0:
        safe_remove_file(cover_path)


def guess_file_content_type(file_path, default="application/octet-stream"):
    content_type, _ = mimetypes.guess_type(file_path)
    return content_type or default


def get_image_content_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".png":
        return "image/png"

    if ext == ".webp":
        return "image/webp"

    return "image/jpeg"
