function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
}

function getTrackDisplayArtist(track) {
    return track.artist_name || track.artist || "Неизвестный исполнитель";
}

function getTrackDisplayAlbum(track) {
    return track.album_title || "";
}

function getTrackCoverUrl(track) {
    if (!track) return "";

    const coverUrl = track.effective_cover_url || track.cover_url || track.album_cover_url || "";
    return coverUrl ? buildMediaUrl(coverUrl) : "";
}

function openInternalPage(page, params = {}) {
    if (typeof navigateTo === "function") {
        navigateTo(page, params);
    }
}

function renderTrackCards(container, tracks, options = {}) {
    if (!container) return;

    const {
        emptyText = "Треки не найдены.",
        showActions = true,
        onEdit = null,
        onDelete = null,
        onPlay = null,
        onAddToPlaylist = null,
        onAddFavorite = null,
        onRemoveFavorite = null,
        onToggleFavorite = null,
        isFavorite = null,
        onRemoveFromPlaylist = null,
        allowDelete = false
    } = options;

    container.innerHTML = "";

    if (!tracks || !tracks.length) {
        container.innerHTML = `<div class="track-card">${emptyText}</div>`;
        return;
    }

    tracks.forEach((track) => {
        const card = document.createElement("div");
        card.className = "track-card";

        const artistName = escapeHtml(getTrackDisplayArtist(track));
        const albumTitle = escapeHtml(getTrackDisplayAlbum(track));
        const title = escapeHtml(track.title || "");
        const coverUrl = getTrackCoverUrl(track);

        const coverHtml = coverUrl
            ? `<img class="track-card-cover-image" src="${escapeHtml(coverUrl)}" alt="Обложка">`
            : `<div class="track-card-cover-placeholder">♪</div>`;

        const canModify = typeof canModifyTrackForCurrentUser === "function"
            ? canModifyTrackForCurrentUser(track)
            : showActions;

        const isTrackFavorite = typeof isFavorite === "function"
            ? Boolean(isFavorite(track))
            : Boolean(track.is_favorite || track.isFavorite || track.favorite);

        const hasFavoriteButton = showActions && typeof onToggleFavorite === "function";

        const hasMenuActions = showActions && (
            canModify ||
            onDelete ||
            onAddToPlaylist ||
            onAddFavorite ||
            onRemoveFavorite ||
            onRemoveFromPlaylist
        );

        const menuItems = [];

        menuItems.push(`
            <button class="dropdown-item play-action" type="button">
                Воспроизвести
            </button>
        `);

        if (onAddFavorite) {
            menuItems.push(`
                <button class="dropdown-item favorite-action" type="button">
                    В избранное
                </button>
            `);
        }

        if (onRemoveFavorite) {
            menuItems.push(`
                <button class="dropdown-item remove-favorite-action" type="button">
                    Убрать из избранного
                </button>
            `);
        }

        if (onAddToPlaylist) {
            menuItems.push(`
                <button class="dropdown-item add-playlist-action" type="button">
                    Добавить в плейлист
                </button>
            `);
        }

        if (onRemoveFromPlaylist) {
            menuItems.push(`
                <button class="dropdown-item remove-playlist-action" type="button">
                    Убрать из плейлиста
                </button>
            `);
        }

        if (canModify && onEdit) {
            menuItems.push(`
                <button class="dropdown-item edit-action" type="button">
                    Редактировать
                </button>
            `);
        }

        if (onDelete && (canModify || allowDelete)) {
            menuItems.push(`
                <button class="dropdown-item delete-action" type="button">
                    Удалить
                </button>
            `);
        }

        const actionsHtml = `
            <div class="track-actions">
                <button class="play-icon-button play-action" type="button" title="Воспроизвести">
                    ▶
                </button>

                ${hasFavoriteButton ? `
                    <button
                        class="favorite-icon-button ${isTrackFavorite ? "active" : ""}"
                        type="button"
                        title="${isTrackFavorite ? "Убрать из избранного" : "Добавить в избранное"}"
                        aria-label="${isTrackFavorite ? "Убрать из избранного" : "Добавить в избранное"}"
                    >
                        ${isTrackFavorite ? "♥" : "♡"}
                    </button>
                ` : ""}

                ${hasMenuActions ? `
                    <button class="menu-button" type="button">⋯</button>

                    <div class="dropdown-menu">
                        ${menuItems.join("")}
                    </div>
                ` : ""}
            </div>
        `;

        card.innerHTML = `
            <div class="track-card-top">
                <div class="track-card-cover">
                    ${coverHtml}
                </div>

                <div class="track-main-info">
                    <h3 class="track-title-link" data-track-id="${track.id}">
                        ${title}
                    </h3>

                    <p class="track-artist-link" data-artist-id="${track.artist_id || ""}">
                        ${artistName}
                    </p>

                    ${albumTitle ? `<div class="muted-text">Альбом: ${albumTitle}</div>` : ""}
                </div>

                ${actionsHtml}
            </div>
        `;

        const playButtons = card.querySelectorAll(".play-action");

        playButtons.forEach((button) => {
            button.addEventListener("click", () => {
                if (onPlay) {
                    onPlay(track);
                } else if (typeof playTrack === "function") {
                    playTrack(track);
                }
            });
        });

        const titleLink = card.querySelector(".track-title-link");

        if (track.album_id) {
            titleLink.classList.add("clickable-link");

            titleLink.addEventListener("click", () => {
                openInternalPage("album", { id: track.album_id });
            });
        }

        const artistLink = card.querySelector(".track-artist-link");

        if (track.artist_id) {
            artistLink.classList.add("clickable-link");

            artistLink.addEventListener("click", () => {
                openInternalPage("artist", { id: track.artist_id });
            });
        }

        if (showActions) {
            const editButton = card.querySelector(".edit-action");
            const deleteButton = card.querySelector(".delete-action");
            const addPlaylistButton = card.querySelector(".add-playlist-action");
            const favoriteButton = card.querySelector(".favorite-action");
            const favoriteIconButton = card.querySelector(".favorite-icon-button");
            const removeFavoriteButton = card.querySelector(".remove-favorite-action");
            const removePlaylistButton = card.querySelector(".remove-playlist-action");

            if (editButton) {
                editButton.addEventListener("click", () => {
                    if (onEdit) onEdit(track);
                });
            }

            if (deleteButton) {
                deleteButton.addEventListener("click", () => {
                    if (onDelete) onDelete(track);
                });
            }

            if (addPlaylistButton) {
                addPlaylistButton.addEventListener("click", () => {
                    if (onAddToPlaylist) onAddToPlaylist(track);
                });
            }

            if (favoriteButton) {
                favoriteButton.addEventListener("click", () => {
                    if (onAddFavorite) onAddFavorite(track);
                });
            }

            if (favoriteIconButton) {
                favoriteIconButton.addEventListener("click", async () => {
                    await onToggleFavorite(track);
                });
            }

            if (removeFavoriteButton) {
                removeFavoriteButton.addEventListener("click", () => {
                    if (onRemoveFavorite) onRemoveFavorite(track);
                });
            }

            if (removePlaylistButton) {
                removePlaylistButton.addEventListener("click", () => {
                    if (onRemoveFromPlaylist) onRemoveFromPlaylist(track);
                });
            }
        }

        container.appendChild(card);
    });
}