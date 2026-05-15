function renderSharedPlayer() {
    const mountNode = document.getElementById("shared-player");
    if (!mountNode) return;

    mountNode.innerHTML = `
        <div id="bottom-player" class="bottom-player hidden">
    <button id="close-player-button" class="player-close-button" type="button">×</button>
            <div class="bottom-player-left">
                <img id="bottom-player-cover" class="bottom-player-cover hidden" src="" alt="Cover">
                <div id="bottom-player-cover-placeholder" class="bottom-player-cover-placeholder">♪</div>

                <div class="bottom-player-track-info">
                    <div id="bottom-player-title" class="bottom-player-title">Ничего не играет</div>
                    <div id="bottom-player-artist" class="bottom-player-artist">—</div>
                </div>
            </div>

            <div class="bottom-player-center">
                <div class="bottom-player-controls">
                    <button id="prev-track-button" class="circle-button" type="button">⏮</button>
                    <button id="play-pause-button" class="circle-button" type="button">▶</button>
                    <button id="next-track-button" class="circle-button" type="button">⏭</button>
                </div>

                <div class="bottom-player-progress">
                    <span id="current-time-label" class="time-label">0:00</span>
                    <input id="seek-range" type="range" min="0" max="100" step="0.1" value="0">
                    <span id="duration-label" class="time-label">0:00</span>
                </div>
            </div>

            <div class="bottom-player-right">
                <label for="volume-range">Громкость</label>
                <input id="volume-range" type="range" min="0" max="1" step="0.01" value="1">
            </div>

            <audio id="global-audio"></audio>
        </div>
    `;
}

document.addEventListener("DOMContentLoaded", renderSharedPlayer);