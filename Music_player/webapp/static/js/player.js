let audio = null;

let bottomPlayer = null;
let bottomPlayerTitle = null;
let bottomPlayerArtist = null;
let bottomPlayerCover = null;
let bottomPlayerCoverPlaceholder = null;

let sideTrackTitle = null;
let sideTrackArtist = null;
let sideCoverImage = null;
let sideCoverPlaceholder = null;
let artistTracksList = null;

let prevTrackButton = null;
let playPauseButton = null;
let nextTrackButton = null;
let volumeRange = null;

let seekRange = null;
let currentTimeLabel = null;
let durationLabel = null;

let playerQueue = [];
let allTracksForArtistBlock = [];
let currentTrackIndex = -1;
let isSeeking = false;
let playerInitialized = false;

function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) {
        return "0:00";
    }

    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${String(secs).padStart(2, "0")}`;
}

function setPlayerQueue(tracks, allTracks) {
    playerQueue = Array.isArray(tracks) ? tracks : [];
    allTracksForArtistBlock = Array.isArray(allTracks) ? allTracks : [];
}

function getCoverSrc(track) {
    if (!track) return "";
    const coverUrl = track.effective_cover_url || track.cover_url || track.album_cover_url || "";
    return coverUrl ? `${API_BASE}${coverUrl}` : "";
}

function updateCoverUI(track) {
    const coverSrc = getCoverSrc(track);

    if (coverSrc) {
        if (bottomPlayerCover) {
            bottomPlayerCover.src = coverSrc;
            bottomPlayerCover.classList.remove("hidden");
        }
        if (bottomPlayerCoverPlaceholder) {
            bottomPlayerCoverPlaceholder.classList.add("hidden");
        }

        if (sideCoverImage) {
            sideCoverImage.src = coverSrc;
            sideCoverImage.classList.remove("hidden");
        }
        if (sideCoverPlaceholder) {
            sideCoverPlaceholder.classList.add("hidden");
        }
    } else {
        if (bottomPlayerCover) {
            bottomPlayerCover.src = "";
            bottomPlayerCover.classList.add("hidden");
        }
        if (bottomPlayerCoverPlaceholder) {
            bottomPlayerCoverPlaceholder.classList.remove("hidden");
        }

        if (sideCoverImage) {
            sideCoverImage.src = "";
            sideCoverImage.classList.add("hidden");
        }
        if (sideCoverPlaceholder) {
            sideCoverPlaceholder.classList.remove("hidden");
        }
    }
}


function resetSidePanel() {
    if (sideTrackTitle) {
        sideTrackTitle.textContent = "Трек не выбран";
    }
    if (sideTrackArtist) {
        sideTrackArtist.textContent = "–";
    }
    if (sideCoverImage) {
        sideCoverImage.src = "";
        sideCoverImage.classList.add("hidden");
    }
    if (sideCoverPlaceholder) {
        sideCoverPlaceholder.classList.remove("hidden");
        sideCoverPlaceholder.textContent = "Нет обложки";
    }
    if (artistTracksList) {
        artistTracksList.innerHTML = `<div class="muted-text">Сначала включи трек</div>`;
    }
}

function renderArtistTracks(track) {
    if (!artistTracksList) return;

    if (!track) {
        artistTracksList.innerHTML = `<div class="muted-text">Сначала включи трек</div>`;
        return;
    }

    const otherTracks = allTracksForArtistBlock.filter(item =>
        item.artist_id === track.artist_id && item.id !== track.id
    );

    if (!otherTracks.length) {
        artistTracksList.innerHTML = `<div class="muted-text">Других треков этого исполнителя пока нет</div>`;
        return;
    }

    artistTracksList.innerHTML = "";

    otherTracks.slice(0, 6).forEach(item => {
        const row = document.createElement("div");
        row.className = "artist-track-item";

        const coverSrc = getCoverSrc(item);
        const coverHtml = coverSrc
            ? `<img class="artist-track-cover" src="${coverSrc}" alt="Обложка">`
            : `<div class="artist-track-cover-placeholder">♪</div>`;

        row.innerHTML = `
            ${coverHtml}

            <div class="artist-track-meta">
                <div class="artist-track-item-title">${escapeHtml(item.title)}</div>
                <div class="artist-track-item-artist">${escapeHtml(item.artist_name || item.artist || "")}</div>
            </div>

            <button class="artist-track-play-button" type="button" aria-label="Включить">
                ▶
            </button>
        `;

        row.addEventListener("click", () => {
            playTrack(item);
        });

        const playButton = row.querySelector(".artist-track-play-button");

        playButton?.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            playTrack(item);
        });

        artistTracksList.appendChild(row);
    });
}

function updatePlayerInfo(track) {
    if (!track) return;

    if (bottomPlayer) {
        bottomPlayer.classList.remove("hidden");
    }

    if (bottomPlayerTitle) {
        bottomPlayerTitle.textContent = track.title;
    }
    if (bottomPlayerArtist) {
        bottomPlayerArtist.textContent = track.artist_name || track.artist;
    }

    if (sideTrackTitle) {
        sideTrackTitle.textContent = track.title;
    }
    if (sideTrackArtist) {
        sideTrackArtist.textContent = track.artist_name || track.artist;
    }

    updateCoverUI(track);
    renderArtistTracks(track);
}

function playTrack(track) {
    if (!track) return;
    if (!playerInitialized) {
        initPlayer();
    }
    if (!audio) return;

    const foundIndex = playerQueue.findIndex(item => item.id === track.id);
    if (foundIndex !== -1) {
        currentTrackIndex = foundIndex;
    } else {
        playerQueue.push(track);
        currentTrackIndex = playerQueue.length - 1;
    }

    audio.src = `${API_BASE}/api/tracks/${track.id}/stream`;
    updatePlayerInfo(track);
    audio.play().catch(() => {});

    if (playPauseButton) {
        playPauseButton.textContent = "⏸";
    }
}

function playCurrentTrack() {
    if (currentTrackIndex < 0 || currentTrackIndex >= playerQueue.length) return;
    playTrack(playerQueue[currentTrackIndex]);
}

function playNextTrack(loop = true) {
    if (!playerQueue.length) return;

    if (currentTrackIndex < playerQueue.length - 1) {
        currentTrackIndex += 1;
        playCurrentTrack();
        return;
    }

    if (loop) {
        currentTrackIndex = 0;
        playCurrentTrack();
        return;
    }

    if (audio) {
        audio.pause();
        audio.currentTime = 0;
    }

    if (playPauseButton) {
        playPauseButton.textContent = "▶";
    }

    if (seekRange) {
        seekRange.value = 0;
    }

    if (currentTimeLabel) {
        currentTimeLabel.textContent = "0:00";
    }
}

function playPreviousTrack() {
    if (!playerQueue.length) return;

    if (currentTrackIndex > 0) {
        currentTrackIndex -= 1;
    } else {
        currentTrackIndex = playerQueue.length - 1;
    }

    playCurrentTrack();
}

function initPlayer() {
    if (playerInitialized) return;

    audio = document.getElementById("global-audio");

    bottomPlayer = document.getElementById("bottom-player");
    bottomPlayerTitle = document.getElementById("bottom-player-title");
    bottomPlayerArtist = document.getElementById("bottom-player-artist");
    bottomPlayerCover = document.getElementById("bottom-player-cover");
    bottomPlayerCoverPlaceholder = document.getElementById("bottom-player-cover-placeholder");

    const closeButton = document.getElementById("close-player-button");

if (closeButton) {
    closeButton.addEventListener("click", closePlayer);
}
    sideTrackTitle = document.getElementById("side-track-title");
    sideTrackArtist = document.getElementById("side-track-artist");
    sideCoverImage = document.getElementById("side-cover-image");
    sideCoverPlaceholder = document.getElementById("side-cover-placeholder");
    artistTracksList = document.getElementById("artist-tracks-list");

    prevTrackButton = document.getElementById("prev-track-button");
    playPauseButton = document.getElementById("play-pause-button");
    nextTrackButton = document.getElementById("next-track-button");
    volumeRange = document.getElementById("volume-range");

    seekRange = document.getElementById("seek-range");
    currentTimeLabel = document.getElementById("current-time-label");
    durationLabel = document.getElementById("duration-label");

    if (!audio) return;

    if (playPauseButton) {
        playPauseButton.addEventListener("click", () => {
            if (!audio.src) return;

            if (audio.paused) {
                audio.play().catch(() => {});
                playPauseButton.textContent = "⏸";
            } else {
                audio.pause();
                playPauseButton.textContent = "▶";
            }
        });
    }

    if (prevTrackButton) {
        prevTrackButton.addEventListener("click", playPreviousTrack);
    }

    if (nextTrackButton) {
        nextTrackButton.addEventListener("click", playNextTrack);
    }

    if (volumeRange) {
        volumeRange.addEventListener("input", () => {
            audio.volume = Number(volumeRange.value);
        });
    }

    if (seekRange) {
        seekRange.addEventListener("input", () => {
            isSeeking = true;
            const seekTo = Number(seekRange.value);
            if (currentTimeLabel) {
                currentTimeLabel.textContent = formatTime(seekTo);
            }
        });

        seekRange.addEventListener("change", () => {
            audio.currentTime = Number(seekRange.value);
            isSeeking = false;
        });
    }

    audio.addEventListener("loadedmetadata", () => {
        if (seekRange) {
            seekRange.max = audio.duration || 0;
        }
        if (durationLabel) {
            durationLabel.textContent = formatTime(audio.duration);
        }
    });

    audio.addEventListener("timeupdate", () => {
        if (!isSeeking) {
            if (seekRange) {
                seekRange.value = audio.currentTime || 0;
            }
            if (currentTimeLabel) {
                currentTimeLabel.textContent = formatTime(audio.currentTime);
            }
        }
    });

    audio.addEventListener("ended", () => {
    playNextTrack(false);
});

    audio.addEventListener("pause", () => {
        if (playPauseButton) {
            playPauseButton.textContent = "▶";
        }
    });

    audio.addEventListener("play", () => {
        if (playPauseButton) {
            playPauseButton.textContent = "⏸";
        }
    });

    playerInitialized = true;
}

function closePlayer() {
    if (!audio) return;

    audio.pause();
    audio.currentTime = 0;

    currentTrackIndex = -1;
    playerQueue = [];

    const player = document.getElementById("bottom-player");
    if (player) {
        player.classList.add("hidden");
    }

    resetSidePanel();
}

window.addEventListener("DOMContentLoaded", () => {
    setTimeout(initPlayer, 0);
});