let allTracksCache = [];
let displayedTracksCache = [];
let albumModalSource = "upload";
let currentAlbum = null;
let currentArtist = null;
let currentUser = null;
let currentTracksType = "common";
let currentPlaylist = null;
let addToPlaylistTrack = null;
let favoriteTrackIds = new Set();

function getElement(id) {
    return document.getElementById(id);
}

function getUserFriendlyMessage(text) {
    const messages = {
        "You already uploaded this track file": "Этот трек уже загружен",
        "This public track file already exists": "Такой трек уже есть в общей библиотеке",
        "You already have track with this title": "У вас уже есть трек с таким названием",
        "Public track already exists": "Такой трек уже есть в общей библиотеке",
        "This track already exists in the common library": "Этот трек уже есть в общей библиотеке"
    };

    return messages[text] || text;
}

function showMessage(text, type = "info") {
    const messageBox = getElement("message-box");
    if (!messageBox) return;

    messageBox.textContent = getUserFriendlyMessage(text);
    messageBox.classList.remove("hidden", "message-success", "message-error", "message-info");
    messageBox.classList.add(`message-${type}`);
}

function hideMessage() {
    const messageBox = getElement("message-box");
    if (!messageBox) return;

    messageBox.textContent = "";
    messageBox.classList.add("hidden");
    messageBox.classList.remove("message-success", "message-error", "message-info");
}


async function refreshFavoriteTrackIds() {
    favoriteTrackIds = new Set();

    if (!isRegularUser()) {
        return;
    }

    const result = await apiGetFavorites();

    if (result.status === "success") {
        favoriteTrackIds = new Set((result.tracks || []).map((track) => Number(track.id)));
    }
}

function isTrackFavorite(track) {
    return favoriteTrackIds.has(Number(track.id));
}

async function toggleFavorite(track) {
    const trackId = Number(track.id);
    const alreadyFavorite = favoriteTrackIds.has(trackId);

    const result = alreadyFavorite
        ? await apiRemoveFavorite(trackId)
        : await apiAddFavorite(trackId);

    if (result.status !== "success") {
        showMessage(result.message || "Ошибка избранного", "error");
        return false;
    }

    if (alreadyFavorite) {
        favoriteTrackIds.delete(trackId);
        showMessage("Трек убран из избранного", "success");
    } else {
        favoriteTrackIds.add(trackId);
        showMessage("Трек добавлен в избранное", "success");
    }

    return true;
}

function setFileNameLabel(inputId, labelId, emptyText = "Файл не выбран") {
    const input = getElement(inputId);
    const label = getElement(labelId);

    if (!input || !label) return;

    const file = input.files && input.files[0];
    label.textContent = file ? file.name : emptyText;
}

async function resolveCreatedAlbumId(result, payload) {
    const directId = result?.album?.id || result?.id || result?.album_id;

    if (directId) {
        return directId;
    }

    const albumsResult = await apiGetAlbumsByArtist(payload.artist);

    if (albumsResult.status !== "success") {
        return null;
    }

    const album = (albumsResult.albums || [])
        .find((item) => item.title === payload.title);

    return album ? album.id : null;
}

function closeCustomDialog(modal, resolve, value) {
    if (modal) {
        modal.remove();
    }
    resolve(value);
}

function showConfirmModal(message, options = {}) {
    return new Promise((resolve) => {
        const modal = document.createElement("div");
        modal.className = "custom-dialog-modal";

        const title = options.title || "Подтверждение";
        const confirmText = options.confirmText || "Подтвердить";
        const cancelText = options.cancelText || "Отмена";
        const dangerClass = options.danger === false ? "" : " danger-button";

        modal.innerHTML = `
            <div class="custom-dialog-backdrop"></div>
            <div class="custom-dialog-content">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(message)}</p>
                <div class="custom-dialog-actions">
                    <button class="pill-button secondary-button custom-dialog-cancel" type="button">${escapeHtml(cancelText)}</button>
                    <button class="pill-button custom-dialog-confirm${dangerClass}" type="button">${escapeHtml(confirmText)}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.querySelector(".custom-dialog-confirm")?.addEventListener("click", () => {
            closeCustomDialog(modal, resolve, true);
        });

        modal.querySelector(".custom-dialog-cancel")?.addEventListener("click", () => {
            closeCustomDialog(modal, resolve, false);
        });

        modal.querySelector(".custom-dialog-backdrop")?.addEventListener("click", () => {
            closeCustomDialog(modal, resolve, false);
        });
    });
}

function showInfoModal(message, options = {}) {
    return new Promise((resolve) => {
        const modal = document.createElement("div");
        modal.className = "custom-dialog-modal";

        const title = options.title || "Сообщение";
        const buttonText = options.buttonText || "ОК";

        modal.innerHTML = `
            <div class="custom-dialog-backdrop"></div>
            <div class="custom-dialog-content">
                <h3>${escapeHtml(title)}</h3>
                <p>${escapeHtml(message)}</p>
                <div class="custom-dialog-actions">
                    <button class="pill-button custom-dialog-ok" type="button">${escapeHtml(buttonText)}</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        modal.querySelector(".custom-dialog-ok")?.addEventListener("click", () => {
            closeCustomDialog(modal, resolve, true);
        });

        modal.querySelector(".custom-dialog-backdrop")?.addEventListener("click", () => {
            closeCustomDialog(modal, resolve, true);
        });
    });
}

function getTracksWord(count) {
    const lastTwo = count % 100;
    const lastOne = count % 10;

    if (lastTwo >= 11 && lastTwo <= 14) {
        return "треков";
    }

    if (lastOne === 1) {
        return "трек";
    }

    if (lastOne >= 2 && lastOne <= 4) {
        return "трека";
    }

    return "треков";
}


function isLoggedIn() {
    return Boolean(currentUser);
}

function isAdmin() {
    return currentUser && currentUser.role === "admin";
}

function isRegularUser() {
    return currentUser && currentUser.role === "user";
}

function canModifyTrackForCurrentUser(track) {
    if (!currentUser || !track) return false;
    if (track.is_public) return isAdmin();
    return track.user_id === currentUser.id;
}

function applyRoleToInterface() {
    document.querySelectorAll(".auth-only").forEach((element) => {
        element.classList.toggle("hidden", !isLoggedIn());
    });

    document.querySelectorAll(".user-only").forEach((element) => {
        element.classList.toggle("hidden", !isRegularUser());
    });

    document.querySelectorAll(".admin-only").forEach((element) => {
        element.classList.toggle("hidden", !isAdmin());
    });

    if (typeof updateTopbarUser === "function") {
        updateTopbarUser(currentUser);
    }
}

async function loadCurrentUser() {
    const result = await apiGetMe();
    currentUser = result.status === "success" ? result.user : null;
    applyRoleToInterface();
}

function openLoginModal() {
    getElement("login-modal")?.classList.remove("hidden");
}

function closeLoginModal() {
    getElement("login-modal")?.classList.add("hidden");
    getElement("login-form")?.reset();
}

function openRegisterModal() {
    getElement("register-modal")?.classList.remove("hidden");
}

function closeRegisterModal() {
    getElement("register-modal")?.classList.add("hidden");
    getElement("register-form")?.reset();
}

function renderPlaceholderPage(title, text) {
    const pageContent = getElement("page-content");
    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <h2>${escapeHtml(title)}</h2>
            </div>
            <div class="track-card">${escapeHtml(text)}</div>
        </section>
    `;
}

function setAlbumControlsVisible(visible) {
    const uploadAlbumRow = getElement("album-select")?.closest(".form-row");
    const editAlbumRow = getElement("edit-album-select")?.closest(".form-row");
    uploadAlbumRow?.classList.toggle("hidden", !visible);
    editAlbumRow?.classList.toggle("hidden", !visible);
}

function resetAlbumSelect(selectElement, placeholderText) {
    if (!selectElement) return;

    selectElement.innerHTML = "";

    const option = document.createElement("option");
    option.value = "";
    option.textContent = placeholderText;

    selectElement.appendChild(option);
    selectElement.value = "";
}

function fillAlbumSelect(selectElement, albums, selectedTitle = "") {
    if (!selectElement) return;

    resetAlbumSelect(selectElement, "Выбери альбом");

    (albums || []).forEach((album) => {
        const option = document.createElement("option");
        option.value = album.title;
        option.textContent = album.year ? `${album.title} (${album.year})` : album.title;
        selectElement.appendChild(option);
    });

    if (selectedTitle) {
        selectElement.value = selectedTitle;
    }
}

async function loadAlbumsForArtist(artistName, selectElement, selectedTitle = "") {
    const artist = (artistName || "").trim();

    if (!artist) {
        resetAlbumSelect(selectElement, "Сначала выбери исполнителя");
        return;
    }

    const result = await apiGetAlbumsByArtist(artist);

    if (result.status !== "success") {
        resetAlbumSelect(selectElement, "Ошибка загрузки альбомов");
        return;
    }

    const albums = result.albums || [];

    if (!albums.length) {
        resetAlbumSelect(selectElement, "Нет альбомов – создай новый");
        return;
    }

    fillAlbumSelect(selectElement, albums, selectedTitle);
}

function renderArtists(artists) {
    const artistsDatalist = getElement("artists-datalist");
    if (!artistsDatalist) return;

    artistsDatalist.innerHTML = "";

    (artists || []).forEach((artist) => {
        const option = document.createElement("option");
        option.value = artist;
        artistsDatalist.appendChild(option);
    });
}

async function loadArtists() {
    const result = await apiGetArtists();

    if (result.status === "success") {
        renderArtists(result.artists || []);
    }
}

function openUploadModal() {
    const uploadModal = getElement("upload-modal");
    if (!uploadModal) return;

    setAlbumControlsVisible(isAdmin());
    uploadModal.classList.remove("hidden");
}

function closeUploadModal() {
    const uploadModal = getElement("upload-modal");
    const uploadForm = getElement("upload-form");
    const uploadAlbumSelect = getElement("album-select");

    if (!uploadModal || !uploadForm) return;

    uploadModal.classList.add("hidden");
    uploadForm.reset();
    const uploadFileNameLabel = getElement("file-name-label");
    if (uploadFileNameLabel) {
        uploadFileNameLabel.textContent = "Файл не выбран";
    }
    resetAlbumSelect(uploadAlbumSelect, "Сначала выбери исполнителя");
}

function openEditModal(track) {
    const editModal = getElement("edit-modal");
    const editTrackIdInput = getElement("edit-track-id");
    const editTitleInput = getElement("edit-title");
    const editArtistInput = getElement("edit-artist");
    const editCoverInput = getElement("edit-cover");
    const editAlbumSelect = getElement("edit-album-select");

    if (!editModal) return;

    editTrackIdInput.value = track.id;
    editTitleInput.value = track.title || "";
    editArtistInput.value = track.artist_name || track.artist || "";
    editCoverInput.value = "";

    setAlbumControlsVisible(Boolean(track.is_public));
    editModal.classList.remove("hidden");

    if (track.is_public) {
        loadAlbumsForArtist(editArtistInput.value.trim(), editAlbumSelect, track.album_title || "");
    } else {
        resetAlbumSelect(editAlbumSelect, "Личные треки без альбома");
    }
}

function closeEditModal() {
    const editModal = getElement("edit-modal");
    const editForm = getElement("edit-form");
    const editTrackIdInput = getElement("edit-track-id");
    const editAlbumSelect = getElement("edit-album-select");

    if (!editModal || !editForm) return;

    editModal.classList.add("hidden");
    editForm.reset();
    editTrackIdInput.value = "";
    resetAlbumSelect(editAlbumSelect, "Сначала выбери исполнителя");
}

function openCreateAlbumModal(source) {
    albumModalSource = source;

    const uploadArtistInput = getElement("artist");
    const editArtistInput = getElement("edit-artist");
    const createAlbumModal = getElement("create-album-modal");
    const createAlbumArtistInput = getElement("create-album-artist");
    const createAlbumTitleInput = getElement("create-album-title");
    const createAlbumYearInput = getElement("create-album-year");
    const createAlbumCoverInput = getElement("create-album-cover");
    const createAlbumCoverLabel = getElement("create-album-cover-name-label");

    const artistValue = source === "edit"
        ? editArtistInput.value.trim()
        : uploadArtistInput.value.trim();

    if (!artistValue) {
        showMessage("Сначала укажи исполнителя");
        return;
    }

    createAlbumArtistInput.value = artistValue;
    createAlbumTitleInput.value = "";
    createAlbumYearInput.value = "";

    if (createAlbumCoverInput) {
        createAlbumCoverInput.value = "";
    }

    if (createAlbumCoverLabel) {
        createAlbumCoverLabel.textContent = "Файл не выбран";
    }

    createAlbumModal.classList.remove("hidden");
}

function closeCreateAlbumModal() {
    const createAlbumModal = getElement("create-album-modal");
    const createAlbumForm = getElement("create-album-form");

    if (!createAlbumModal || !createAlbumForm) return;

    createAlbumModal.classList.add("hidden");
    createAlbumForm.reset();
    setFileNameLabel("create-album-cover", "create-album-cover-name-label");
}

function openEditAlbumModal() {
    const editAlbumModal = getElement("edit-album-modal");
    const editAlbumIdInput = getElement("edit-album-id");
    const editAlbumTitleInput = getElement("edit-album-title");
    const editAlbumYearInput = getElement("edit-album-year");
    const editAlbumCoverInput = getElement("edit-album-cover");

    if (!currentAlbum || !editAlbumModal) return;

    editAlbumIdInput.value = currentAlbum.id;
    editAlbumTitleInput.value = currentAlbum.title || "";
    editAlbumYearInput.value = currentAlbum.year || "";
    editAlbumCoverInput.value = "";

    editAlbumModal.classList.remove("hidden");
}

function closeEditAlbumModal() {
    const editAlbumModal = getElement("edit-album-modal");
    const editAlbumForm = getElement("edit-album-form");

    if (!editAlbumModal || !editAlbumForm) return;

    editAlbumModal.classList.add("hidden");
    editAlbumForm.reset();
}

function openEditArtistModal() {
    const modal = getElement("edit-artist-modal");
    const artistIdInput = getElement("edit-artist-id");
    const coverInput = getElement("edit-artist-cover");

    if (!modal || !currentArtist) return;

    artistIdInput.value = currentArtist.id;
    coverInput.value = "";

    modal.classList.remove("hidden");
}

function closeEditArtistModal() {
    const modal = getElement("edit-artist-modal");
    const form = getElement("edit-artist-form");

    if (!modal || !form) return;

    modal.classList.add("hidden");
    form.reset();
}

function renderTracksLayout() {
    const pageContent = getElement("page-content");
    const canShowUploadButton = isAdmin() || (isRegularUser() && currentTracksType === "mine");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header panel-header-with-action">
                <div>
                    <h2 id="tracks-page-title">Библиотека треков</h2>
                    <span id="tracks-count" class="muted-text">0 треков</span>
                </div>

                ${canShowUploadButton ? `
                    <button id="page-upload-track-button" class="pill-button" type="button">
                        Добавить трек
                    </button>
                ` : ""}
            </div>

            <div id="message-box" class="message-box hidden"></div>
            <div id="tracks-list" class="tracks-list"></div>
        </section>
    `;

    getElement("page-upload-track-button")?.addEventListener("click", openUploadModal);
}

function renderTracks(tracks) {
    const tracksList = getElement("tracks-list");
    const tracksCount = getElement("tracks-count");

    if (!tracksList || !tracksCount) return;

    displayedTracksCache = tracks;

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(displayedTracksCache, allTracksCache);
    }

    tracksCount.textContent = `${tracks.length} ${getTracksWord(tracks.length)}`;

    renderTrackCards(tracksList, tracks, {
        emptyText: "Треки не найдены.",
        showActions: true,
        onEdit: (track) => openEditModal(track),
        onDelete: async (track) => {
            const confirmed = await showConfirmModal(`Удалить трек "${track.title}"?`, { confirmText: "Удалить" });
            if (!confirmed) return;

            const result = await apiDeleteTrack(track.id);

            if (result.status === "success") {
                showMessage("Трек удалён");
                await loadTracks();
                await loadArtists();
            } else {
                showMessage(result.message || "Ошибка удаления");
            }
        },
        onPlay: (track) => playTrack(track),
        onAddToPlaylist: isRegularUser() ? (track) => openAddToPlaylistModal(track) : null,
        isFavorite: isTrackFavorite,
        onToggleFavorite: isRegularUser() ? async (track) => {
            await toggleFavorite(track);
            renderTracks(displayedTracksCache);
        } : null
    });
}

async function loadTracks(type = currentTracksType) {
    hideMessage();
    currentTracksType = type || "all";

    const result = await apiGetTracks(currentTracksType);

    if (result.status === "success") {
        allTracksCache = result.tracks || [];
        await refreshFavoriteTrackIds();
        renderTracks(allTracksCache);
    } else {
        showMessage(result.message || "Ошибка загрузки");
    }
}

async function runSearch(query) {
    const normalizedQuery = (query || "").trim();
    hideMessage();

    if (!normalizedQuery) {
        renderTracks(allTracksCache);
        return;
    }

    const result = await apiSearchTracks(normalizedQuery, currentTracksType);

    if (result.status === "success") {
        renderTracks(result.tracks || []);
    } else {
        showMessage(result.message || "Ошибка поиска");
    }
}

async function renderTracksPage(searchQuery = "", type = "common") {
    currentAlbum = null;
    currentArtist = null;
    currentTracksType = type === "mine" ? "mine" : "common";

    renderTracksLayout();

    const title = getElement("tracks-page-title");
    if (title) {
        title.textContent = currentTracksType === "mine"
            ? "Мои треки"
            : "Библиотека треков";
    }

    const homeResult = await apiRequest("/api/home");

if (homeResult.status !== "success") {
    showMessage(homeResult.message || "Ошибка загрузки");
    return;
}

allTracksCache = homeResult.tracks || [];

await refreshFavoriteTrackIds();

renderTracks(allTracksCache);

renderArtists(homeResult.artists || []);

    if (searchQuery) {
        const sharedSearchInput = getElement("shared-search-input");
        if (sharedSearchInput) {
            sharedSearchInput.value = searchQuery;
        }

        await runSearch(searchQuery);
    }
}

function renderAlbumCover(album) {
    const image = getElement("album-cover-image");
    const placeholder = getElement("album-cover-placeholder");

    if (!image || !placeholder) return;

    if (album.cover_url) {
        image.src = buildMediaUrl(album.cover_url);
        image.classList.remove("hidden");
        placeholder.classList.add("hidden");
    } else {
        image.src = "";
        image.classList.add("hidden");
        placeholder.classList.remove("hidden");
    }
}

function renderAlbumLayout() {
    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="artist-header-block">
                <div class="artist-header-cover">
                    <img id="album-cover-image" src="" loading="lazy" alt="Обложка альбома" class="side-cover-image hidden">
                    <div id="album-cover-placeholder" class="side-cover-placeholder">Нет обложки</div>
                </div>

                <div class="artist-header-info">
                    <h2 id="album-title">Альбом</h2>
                    <p id="album-year" class="muted-text"></p>
                    <div style="margin-top: 16px;">
                        <button id="open-edit-album-button" class="pill-button admin-only hidden" type="button">Редактировать альбом</button>
                    </div>
                </div>
            </div>
        </section>

        <section class="tracks-panel">
            <div class="panel-header">
                <h3>Треки альбома</h3>
            </div>
            <div id="album-tracks-list" class="tracks-list"></div>
        </section>
    `;

    const openEditAlbumButton = getElement("open-edit-album-button");

    if (openEditAlbumButton) {
        openEditAlbumButton.addEventListener("click", openEditAlbumModal);
    }

    applyRoleToInterface();
}

async function renderAlbumPage(albumId) {
    currentArtist = null;

    renderAlbumLayout();

    if (!albumId) {
        getElement("album-title").textContent = "Альбом не найден";
        return;
    }

    const [albumResult, tracksResult] = await Promise.all([
        apiGetAlbumById(albumId),
        apiGetAlbumTracks(albumId),
    ]);

    if (albumResult.status !== "success") {
        getElement("album-title").textContent = "Альбом не найден";
        return;
    }

    currentAlbum = albumResult.album;

    getElement("album-title").textContent = currentAlbum.title;
    getElement("album-year").textContent = currentAlbum.year ? `Год: ${currentAlbum.year}` : "";

    renderAlbumCover(currentAlbum);

    const tracks = tracksResult.tracks || [];

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(tracks, tracks);
    }

    await refreshFavoriteTrackIds();

    renderTrackCards(getElement("album-tracks-list"), tracks, {
        emptyText: "В альбоме пока нет треков.",
        showActions: true,
        onPlay: (track) => playTrack(track),
        onAddToPlaylist: isRegularUser() ? (track) => openAddToPlaylistModal(track) : null,
        isFavorite: isTrackFavorite,
        onToggleFavorite: isRegularUser() ? async (track) => {
            await toggleFavorite(track);
            await renderAlbumPage(albumId);
        } : null
    });
}

function renderArtistCover(artist) {
    const image = getElement("artist-cover-image");
    const placeholder = getElement("artist-cover-placeholder");

    if (!image || !placeholder) return;

    if (artist.cover_url) {
        image.src = buildMediaUrl(artist.cover_url);
        image.classList.remove("hidden");
        placeholder.classList.add("hidden");
    } else {
        image.src = "";
        image.classList.add("hidden");
        placeholder.classList.remove("hidden");
    }
}

function renderArtistAlbums(albums) {
    const list = getElement("artist-albums-list");
    if (!list) return;

    list.innerHTML = "";

    if (!albums.length) {
        list.innerHTML = `<div class="track-card">У исполнителя пока нет альбомов.</div>`;
        return;
    }

    albums.forEach((album) => {
        const card = document.createElement("div");
        card.className = "artist-album-card";

        const coverUrl = album.cover_url ? buildMediaUrl(album.cover_url) : "";
        const coverHtml = coverUrl
            ? `<img class="artist-album-cover" src="${escapeHtml(coverUrl)}" loading="lazy" alt="Обложка альбома">`
            : `<div class="artist-album-cover-placeholder">♪</div>`;

        card.innerHTML = `
            ${coverHtml}
            <div class="artist-album-info">
                <h3>${escapeHtml(album.title)}</h3>
                <p>${album.year ? escapeHtml(album.year) : "Год не указан"}</p>
            </div>
        `;

        card.addEventListener("click", () => {
            navigateTo("album", { id: album.id });
        });

        list.appendChild(card);
    });
}

function renderArtistLayout() {
    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel artist-hero-panel">
            <div class="artist-hero-block">
                <div class="artist-hero-cover">
                    <img id="artist-cover-image" src="" loading="lazy" alt="Фото исполнителя" class="artist-hero-image hidden">
                    <div id="artist-cover-placeholder" class="artist-hero-placeholder">♪</div>
                </div>

                <div class="artist-hero-info">
                    <div class="muted-text">Исполнитель</div>
                    <h2 id="artist-name">Исполнитель</h2>
                    <p id="artist-summary" class="muted-text">Альбомы и треки</p>
                    <div class="artist-hero-actions">
                        <button id="open-edit-artist-button" class="pill-button admin-only hidden" type="button">Редактировать фото</button>
                    </div>
                </div>
            </div>
        </section>

        <section class="tracks-panel">
            <div class="panel-header">
                <h3>Альбомы</h3>
            </div>
            <div id="artist-albums-list" class="artist-albums-grid"></div>
        </section>

        <section class="tracks-panel">
            <div class="panel-header">
                <h3>Треки</h3>
            </div>
            <div id="artist-tracks-list-page" class="tracks-list"></div>
        </section>
    `;

    const openEditArtistButton = getElement("open-edit-artist-button");

    if (openEditArtistButton) {
        openEditArtistButton.addEventListener("click", openEditArtistModal);
    }

    applyRoleToInterface();
}

async function renderArtistPage(artistId) {
    currentAlbum = null;

    renderArtistLayout();

    if (!artistId) {
        getElement("artist-name").textContent = "Исполнитель не найден";
        return;
    }

    const [artistResult, tracksResult, albumsResult] = await Promise.all([
        apiGetArtistById(artistId),
        apiGetArtistTracks(artistId),
        apiGetArtistAlbums(artistId),
    ]);

    if (artistResult.status !== "success") {
        getElement("artist-name").textContent = "Исполнитель не найден";
        return;
    }

    currentArtist = artistResult.artist;

    const tracks = tracksResult.tracks || [];

    getElement("artist-name").textContent = currentArtist.name;
    const artistSummary = getElement("artist-summary");
    if (artistSummary) {
        const albumsCount = (albumsResult.albums || []).length;
        const tracksCount = tracks.length;
        artistSummary.textContent = `${albumsCount} альбомов · ${tracksCount} ${getTracksWord(tracksCount)}`;
    }

    renderArtistCover(currentArtist);
    renderArtistAlbums(albumsResult.albums || []);

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(tracks, tracks);
    }

    await refreshFavoriteTrackIds();

    renderTrackCards(getElement("artist-tracks-list-page"), tracks, {
        emptyText: "У исполнителя пока нет треков.",
        showActions: true,
        onPlay: (track) => playTrack(track),
        onAddToPlaylist: isRegularUser() ? (track) => openAddToPlaylistModal(track) : null,
        isFavorite: isTrackFavorite,
        onToggleFavorite: isRegularUser() ? async (track) => {
            await toggleFavorite(track);
            await renderArtistPage(artistId);
        } : null
    });
}

async function renderArtistsPage() {
    currentAlbum = null;
    currentArtist = null;

    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header artists-panel-header">
                <div>
                    <h2>Исполнители</h2>
                    <span id="artists-count" class="muted-text">0 исполнителей</span>
                </div>
            </div>

            <div class="artists-search-wrapper">
                <input
                    id="artists-search-input"
                    class="artists-search-input"
                    type="text"
                    placeholder="Поиск исполнителя"
                    autocomplete="off"
                >
                <button
                    id="artists-search-clear"
                    class="search-clear-button artists-search-clear hidden"
                    type="button"
                    aria-label="Очистить поиск"
                    title="Очистить поиск"
                >×</button>
            </div>

            <div id="artists-list" class="artists-grid"></div>
        </section>
    `;

    const result = await apiGetTracks("common");

    if (result.status !== "success") {
        getElement("artists-list").innerHTML = `
            <div class="track-card">Ошибка загрузки исполнителей.</div>
        `;
        return;
    }

    const tracks = result.tracks || [];
    const artistsMap = new Map();

    tracks.forEach((track) => {
        const artistId = track.artist_id;
        const artistName = track.artist_name || track.artist;

        if (!artistId || !artistName) return;

        if (!artistsMap.has(artistId)) {
            artistsMap.set(artistId, {
                id: artistId,
                name: artistName,
                tracksCount: 0,
                coverUrl: track.artist_cover_url || track.artist_cover || track.effective_artist_cover_url || ""
            });
        }

        artistsMap.get(artistId).tracksCount += 1;
    });

    const artists = Array.from(artistsMap.values())
        .sort((a, b) => a.name.localeCompare(b.name));

    await Promise.all(artists.map(async (artist) => {
        if (artist.coverUrl) return;

        const artistResult = await apiGetArtistById(artist.id);

        if (artistResult.status === "success" && artistResult.artist) {
            artist.coverUrl = artistResult.artist.cover_url || "";
        }
    }));

    function renderArtistsCards(filteredArtists) {
        const list = getElement("artists-list");
        const count = getElement("artists-count");

        if (!list || !count) return;

        count.textContent = `${filteredArtists.length} исполнителей`;

        if (!filteredArtists.length) {
            list.innerHTML = `<div class="track-card artists-empty-card">Исполнители не найдены.</div>`;
            return;
        }

        list.innerHTML = "";

        filteredArtists.forEach((artist) => {
            const card = document.createElement("div");
            card.className = "artist-list-card";

            const coverHtml = artist.coverUrl
                ? `<img class="artist-list-avatar" src="${API_BASE}${escapeHtml(artist.coverUrl)}" alt="Фото исполнителя">`
                : `<div class="artist-list-avatar-placeholder">${escapeHtml(artist.name.slice(0, 1).toUpperCase())}</div>`;

            card.innerHTML = `
                ${coverHtml}
                <div class="artist-list-info">
                    <h3>${escapeHtml(artist.name)}</h3>
                    <p>${artist.tracksCount} ${getTracksWord(artist.tracksCount)}</p>
                </div>
                <button class="artist-open-button" type="button" aria-label="Открыть исполнителя">›</button>
            `;

            card.addEventListener("click", () => {
                navigateTo("artist", { id: artist.id });
            });

            card.querySelector("button")?.addEventListener("click", (event) => {
                event.stopPropagation();
                navigateTo("artist", { id: artist.id });
            });

            list.appendChild(card);
        });
    }

    renderArtistsCards(artists);

    const artistsSearchInput = getElement("artists-search-input");
    const artistsSearchClear = getElement("artists-search-clear");

    function applyArtistsSearch() {
        const query = artistsSearchInput?.value.trim().toLowerCase() || "";

        artistsSearchClear?.classList.toggle("hidden", !query.length);

        const filteredArtists = artists.filter((artist) =>
            artist.name.toLowerCase().includes(query)
        );

        renderArtistsCards(filteredArtists);
    }

    artistsSearchInput?.addEventListener("input", applyArtistsSearch);

    artistsSearchClear?.addEventListener("click", () => {
        artistsSearchInput.value = "";
        artistsSearchInput.focus();
        applyArtistsSearch();
    });
}

function openAddToPlaylistModal(track) {
    if (!isLoggedIn()) {
        showMessage("Войди в аккаунт, чтобы добавлять треки в плейлисты");
        return;
    }

    addToPlaylistTrack = track;

    const modal = getElement("add-to-playlist-modal");
    const trackIdInput = getElement("add-to-playlist-track-id");
    const select = getElement("add-to-playlist-select");

    if (!modal || !trackIdInput || !select) return;

    trackIdInput.value = track.id;
    select.innerHTML = `<option value="">Загрузка плейлистов...</option>`;
    modal.classList.remove("hidden");

    apiGetPlaylists().then((result) => {
        if (result.status !== "success") {
            select.innerHTML = `<option value="">Ошибка загрузки плейлистов</option>`;
            return;
        }

        const playlists = result.playlists || [];

        if (!playlists.length) {
            select.innerHTML = `<option value="">Сначала создай плейлист</option>`;
            return;
        }

        select.innerHTML = "";
        playlists.forEach((playlist) => {
            const option = document.createElement("option");
            option.value = playlist.id;
            option.textContent = playlist.title;
            select.appendChild(option);
        });
    });
}

function closeAddToPlaylistModal() {
    const modal = getElement("add-to-playlist-modal");
    const form = getElement("add-to-playlist-form");

    modal?.classList.add("hidden");
    form?.reset();
    addToPlaylistTrack = null;
}

function renderPlaylistsLayout() {
    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel playlists-panel">
            <div class="panel-header panel-header-with-action">
                <div>
                    <h2>Плейлисты</h2>
                    <span id="playlists-count" class="muted-text">0 плейлистов</span>
                </div>
            </div>

            <div id="message-box" class="message-box hidden"></div>

            <form id="create-playlist-inline-form" class="inline-field-group playlist-create-form playlist-create-form-top">
                <input id="create-playlist-title" type="text" placeholder="Название плейлиста" required>
                <button class="pill-button" type="submit">Создать плейлист</button>
            </form>

            <div id="playlists-list" class="tracks-list playlists-grid"></div>
        </section>
    `;

    const form = getElement("create-playlist-inline-form");
    if (form) {
        form.addEventListener("submit", async (event) => {
            event.preventDefault();

            const title = getElement("create-playlist-title").value.trim();
            if (!title) return;

            const result = await apiCreatePlaylist({ title });

            if (result.status !== "success") {
                showMessage(result.message || "Ошибка создания плейлиста");
                return;
            }

            showMessage("Плейлист создан");
            await renderPlaylistsPage();
        });
    }
}

async function renderPlaylistsPage() {
    currentAlbum = null;
    currentArtist = null;
    currentPlaylist = null;

    if (!isRegularUser()) {
        renderPlaceholderPage("Плейлисты", "Плейлисты доступны только обычному пользователю.");
        return;
    }

    renderPlaylistsLayout();

    const result = await apiGetPlaylists();
    const list = getElement("playlists-list");
    const count = getElement("playlists-count");

    if (result.status !== "success") {
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки плейлистов")}</div>`;
        return;
    }

    const playlists = result.playlists || [];
    if (count) count.textContent = `${playlists.length} плейлистов`;

    if (!playlists.length) {
        list.innerHTML = `<div class="track-card">Плейлистов пока нет.</div>`;
        return;
    }

    list.innerHTML = "";

    playlists.forEach((playlist) => {
        const card = document.createElement("div");
        card.className = "track-card";

        card.className = "track-card playlist-card";

        card.innerHTML = `
            <div class="playlist-cover-placeholder">♫</div>
            <div class="track-main-info playlist-info">
                <h3 style="cursor:pointer;">${escapeHtml(playlist.title)}</h3>
                <p class="muted-text">Личный плейлист</p>
            </div>
            <div class="track-actions playlist-actions">
                <button class="menu-button" type="button">⋯</button>
                <div class="dropdown-menu">
                    <button class="dropdown-item open-playlist-button" type="button">Открыть</button>
                    <button class="dropdown-item delete-playlist-button" type="button">Удалить</button>
                </div>
            </div>
        `;

        card.querySelector("h3").addEventListener("click", () => navigateTo("playlist", { id: playlist.id }));
        card.querySelector(".open-playlist-button").addEventListener("click", () => navigateTo("playlist", { id: playlist.id }));
        card.querySelector(".delete-playlist-button").addEventListener("click", async () => {
            const confirmed = await showConfirmModal(`Удалить плейлист "${playlist.title}"?`, { confirmText: "Удалить" });
            if (!confirmed) return;

            const deleteResult = await apiDeletePlaylist(playlist.id);
            if (deleteResult.status !== "success") {
                showMessage(deleteResult.message || "Ошибка удаления плейлиста");
                return;
            }

            showMessage("Плейлист удалён");
            await renderPlaylistsPage();
        });

        list.appendChild(card);
    });
}

function renderPlaylistLayout() {
    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <div>
                    <h2 id="playlist-title">Плейлист</h2>
                    <p id="playlist-info" class="muted-text"></p>
                </div>
                <button id="rename-playlist-button" class="pill-button secondary-button" type="button">Переименовать</button>
            </div>

            <div id="message-box" class="message-box hidden"></div>
            <div id="playlist-tracks-list" class="tracks-list"></div>
        </section>
    `;

    getElement("rename-playlist-button")?.addEventListener("click", async () => {
        if (!currentPlaylist) return;

        const newTitle = prompt("Новое название плейлиста", currentPlaylist.title || "");
        if (!newTitle || !newTitle.trim()) return;

        const result = await apiUpdatePlaylist(currentPlaylist.id, { title: newTitle.trim() });
        if (result.status !== "success") {
            showMessage(result.message || "Ошибка переименования плейлиста");
            return;
        }

        await renderPlaylistPage(currentPlaylist.id);
    });
}

async function renderPlaylistPage(playlistId) {
    currentAlbum = null;
    currentArtist = null;

    if (!isRegularUser()) {
        renderPlaceholderPage("Плейлист", "Плейлисты доступны только обычному пользователю.");
        return;
    }

    renderPlaylistLayout();

    const result = await apiGetPlaylist(playlistId);
    const list = getElement("playlist-tracks-list");

    if (result.status !== "success") {
        getElement("playlist-title").textContent = "Плейлист не найден";
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки плейлиста")}</div>`;
        return;
    }

    currentPlaylist = result.playlist;
    const tracks = result.tracks || [];

    getElement("playlist-title").textContent = currentPlaylist.title;
    getElement("playlist-info").textContent = `${tracks.length} ${getTracksWord(tracks.length)}`;

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(tracks, tracks);
    }

    await refreshFavoriteTrackIds();

    renderTrackCards(list, tracks, {
        emptyText: "В плейлисте пока нет треков.",
        showActions: true,
        onPlay: (track) => playTrack(track),
        isFavorite: isTrackFavorite,
        onToggleFavorite: isRegularUser() ? async (track) => {
            await toggleFavorite(track);
            await renderPlaylistPage(currentPlaylist.id);
        } : null,
        onRemoveFromPlaylist: async (track) => {
            const result = await apiRemoveTrackFromPlaylist(currentPlaylist.id, track.id);
            if (result.status !== "success") {
                showMessage(result.message || "Ошибка удаления из плейлиста");
                return;
            }

            showMessage("Трек убран из плейлиста");
            await renderPlaylistPage(currentPlaylist.id);
        }
    });
}

async function renderFavoritesPage() {
    currentAlbum = null;
    currentArtist = null;
    currentPlaylist = null;

    if (!isRegularUser()) {
        renderPlaceholderPage("Избранное", "Избранное доступно только обычному пользователю.");
        return;
    }

    const pageContent = getElement("page-content");
    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <h2>Избранное</h2>
                <span id="favorites-count" class="muted-text">0 треков</span>
            </div>

            <div id="message-box" class="message-box hidden"></div>
            <div id="favorites-tracks-list" class="tracks-list"></div>
        </section>
    `;

    const result = await apiGetFavorites();
    const list = getElement("favorites-tracks-list");

    if (result.status !== "success") {
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки избранного")}</div>`;
        return;
    }

    const tracks = result.tracks || [];
    favoriteTrackIds = new Set(tracks.map((track) => Number(track.id)));
    getElement("favorites-count").textContent = `${tracks.length} ${getTracksWord(tracks.length)}`;

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(tracks, tracks);
    }

    renderTrackCards(list, tracks, {
        emptyText: "В избранном пока нет треков.",
        showActions: true,
        onPlay: (track) => playTrack(track),
        onAddToPlaylist: (track) => openAddToPlaylistModal(track),
        isFavorite: () => true,
        onToggleFavorite: async (track) => {
            const changed = await toggleFavorite(track);
            if (changed) await renderFavoritesPage();
        },
        onRemoveFavorite: async (track) => {
            const result = await apiRemoveFavorite(track.id);
            if (result.status !== "success") {
                showMessage(result.message || "Ошибка удаления из избранного");
                return;
            }

            showMessage("Трек убран из избранного");
            await renderFavoritesPage();
        }
    });
}


async function renderAdminUsersPage() {
    if (!isAdmin()) {
        renderPlaceholderPage("Пользователи", "Доступ только для администратора.");
        return;
    }

    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <h2>Пользователи</h2>
            </div>

            <div id="message-box" class="message-box hidden"></div>
            <div id="users-list" class="tracks-list"></div>
        </section>
    `;

    const result = await apiAdminGetUsers();
    const list = getElement("users-list");

    if (!list) return;

    if (result.status !== "success") {
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки пользователей")}</div>`;
        return;
    }

    const users = result.users || [];

    if (!users.length) {
        list.innerHTML = `<div class="track-card">Пользователи не найдены.</div>`;
        return;
    }

    list.innerHTML = "";

    users.forEach((user) => {
        const card = document.createElement("div");
        card.className = "track-card";

        card.innerHTML = `
            <div class="admin-user-card">
                <div class="track-main-info">
                    <h3>${escapeHtml(user.username)}</h3>
                    <p>${escapeHtml(user.email)}</p>
                    <div class="muted-text">Роль: ${escapeHtml(user.role)}</div>
                </div>

                <div class="track-actions admin-user-actions">
                    <select class="user-role-select" aria-label="Роль пользователя">
                        <option value="user" ${user.role === "user" ? "selected" : ""}>user</option>
                        <option value="admin" ${user.role === "admin" ? "selected" : ""}>admin</option>
                    </select>
                    <button class="pill-button open-user-tracks-button" type="button">Треки</button>
                </div>
            </div>
        `;

        card.querySelector(".user-role-select")?.addEventListener("change", async (event) => {
            const newRole = event.target.value;
            const result = await apiAdminUpdateUserRole(user.id, newRole);

            if (result.status === "success") {
                showMessage("Роль пользователя изменена");
                user.role = newRole;
            } else {
                showMessage(result.message || "Ошибка изменения роли");
                event.target.value = user.role;
            }
        });

        card.querySelector(".open-user-tracks-button")?.addEventListener("click", () => {
            navigateTo("user-tracks", { id: user.id });
        });

        list.appendChild(card);
    });
}

async function renderAdminUserTracksPage(userId) {
    if (!isAdmin()) {
        renderPlaceholderPage("Треки пользователя", "Доступ только для администратора.");
        return;
    }

    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <h2>Треки пользователя</h2>
            </div>

            <div id="message-box" class="message-box hidden"></div>
            <div id="admin-user-tracks-list" class="tracks-list"></div>
        </section>
    `;

    const result = await apiAdminGetUserTracks(userId);
    const list = getElement("admin-user-tracks-list");

    if (!list) return;

    if (result.status !== "success") {
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки треков")}</div>`;
        return;
    }

    const tracks = result.tracks || [];

    if (typeof setPlayerQueue === "function") {
        setPlayerQueue(tracks, tracks);
    }

    renderTrackCards(list, tracks, {
        emptyText: "У пользователя нет треков.",
        showActions: true,
        allowDelete: true,
        onPlay: (track) => playTrack(track),
        onDelete: async (track) => {
            const confirmed = await showConfirmModal(`Удалить трек "${track.title}" у пользователя?`, { confirmText: "Удалить" });
            if (!confirmed) return;

            const result = await apiAdminDeleteUserTrack(userId, track.id);

            if (result.status !== "success") {
                showMessage(result.message || "Ошибка удаления трека");
                return;
            }

            showMessage("Трек удалён, пользователю отправлено уведомление");
            await renderAdminUserTracksPage(userId);
        }
    });
}

async function renderNotificationsPage() {
    if (!isRegularUser()) {
        renderPlaceholderPage("Уведомления", "Уведомления доступны только обычному пользователю.");
        return;
    }

    const pageContent = getElement("page-content");

    pageContent.innerHTML = `
        <section class="tracks-panel">
            <div class="panel-header">
                <h2>Уведомления</h2>
            </div>

            <div id="notifications-list" class="tracks-list"></div>
        </section>
    `;

    const result = await apiGetNotifications();
    const list = getElement("notifications-list");

    if (!list) return;

    if (result.status !== "success") {
        list.innerHTML = `<div class="track-card">${escapeHtml(result.message || "Ошибка загрузки уведомлений")}</div>`;
        return;
    }

    const notifications = result.notifications || [];

    if (!notifications.length) {
        list.innerHTML = `<div class="track-card">Уведомлений пока нет.</div>`;
        return;
    }

    list.innerHTML = "";

    notifications.forEach((notification) => {
        const card = document.createElement("div");
        card.className = "track-card";
        card.innerHTML = `
            <div class="track-main-info">
                <h3>${escapeHtml(notification.message)}</h3>
                <p class="muted-text">${notification.created_at ? new Date(notification.created_at).toLocaleString("ru-RU") : ""}</p>
            </div>
        `;
        list.appendChild(card);
    });
}

function initGlobalEvents() {
    const deleteArtistCoverButton = getElement("delete-artist-cover-button");
    const uploadForm = getElement("upload-form");
    const uploadFileInput = getElement("file");
    const uploadFileNameLabel = getElement("file-name-label");
    const uploadArtistInput = getElement("artist");
    const uploadAlbumSelect = getElement("album-select");

    const editForm = getElement("edit-form");
    const editArtistInput = getElement("edit-artist");
    const editAlbumSelect = getElement("edit-album-select");

    const createAlbumForm = getElement("create-album-form");

    const openUploadModalButton = getElement("open-upload-modal-button");
    const navAllTracksButton = getElement("nav-all-tracks-button");
    const navMyTracksButton = getElement("nav-my-tracks-button");
    const navArtistsButton = getElement("nav-artists-button");
    const navPlaylistsButton = getElement("nav-playlists-button");
    const navFavoritesButton = getElement("nav-favorites-button");
    const navUsersButton = getElement("nav-users-button");
    const navNotificationsButton = getElement("nav-notifications-button");

    const closeUploadModalButton = getElement("close-upload-modal-button");
    const uploadModalBackdrop = getElement("upload-modal-backdrop");
    const cancelUploadButton = getElement("cancel-upload-button");

    const closeEditModalButton = getElement("close-edit-modal-button");
    const editModalBackdrop = getElement("edit-modal-backdrop");
    const cancelEditButton = getElement("cancel-edit-button");

    const openCreateAlbumButton = getElement("open-create-album-button");
    const openCreateAlbumFromEditButton = getElement("open-create-album-from-edit-button");
    const closeCreateAlbumModalButton = getElement("close-create-album-modal-button");
    const createAlbumModalBackdrop = getElement("create-album-modal-backdrop");
    const cancelCreateAlbumButton = getElement("cancel-create-album-button");

    const closeEditAlbumModalButton = getElement("close-edit-album-modal-button");
    const editAlbumModalBackdrop = getElement("edit-album-modal-backdrop");
    const cancelEditAlbumButton = getElement("cancel-edit-album-button");
    const editAlbumForm = getElement("edit-album-form");

    const editArtistForm = getElement("edit-artist-form");
    const closeEditArtistModalButton = getElement("close-edit-artist-modal-button");
    const editArtistModalBackdrop = getElement("edit-artist-modal-backdrop");
    const cancelEditArtistButton = getElement("cancel-edit-artist-button");

    const addToPlaylistForm = getElement("add-to-playlist-form");
    const closeAddToPlaylistButton = getElement("close-add-to-playlist-modal-button");
    const addToPlaylistBackdrop = getElement("add-to-playlist-modal-backdrop");
    const cancelAddToPlaylistButton = getElement("cancel-add-to-playlist-button");

    if (navAllTracksButton) {
        navAllTracksButton.addEventListener("click", () => {
            navigateTo("tracks", { type: "common" });
        });
    }

    if (navMyTracksButton) {
        navMyTracksButton.addEventListener("click", () => {
            navigateTo("tracks", { type: "mine" });
        });
    }

    if (navArtistsButton) {
        navArtistsButton.addEventListener("click", () => {
            navigateTo("artists");
        });
    }

    if (navPlaylistsButton) {
        navPlaylistsButton.addEventListener("click", () => {
            navigateTo("playlists");
        });
    }

    if (navFavoritesButton) {
        navFavoritesButton.addEventListener("click", () => {
            navigateTo("favorites");
        });
    }


    if (navUsersButton) {
        navUsersButton.addEventListener("click", () => {
            navigateTo("users");
        });
    }

    if (navNotificationsButton) {
        navNotificationsButton.addEventListener("click", () => {
            navigateTo("notifications");
        });
    }

    if (openUploadModalButton) {
        openUploadModalButton.addEventListener("click", openUploadModal);
    }

    if (closeUploadModalButton) {
        closeUploadModalButton.addEventListener("click", closeUploadModal);
    }

    if (uploadModalBackdrop) {
        uploadModalBackdrop.addEventListener("click", closeUploadModal);
    }

    if (cancelUploadButton) {
        cancelUploadButton.addEventListener("click", closeUploadModal);
    }

    if (closeEditModalButton) {
        closeEditModalButton.addEventListener("click", closeEditModal);
    }

    if (editModalBackdrop) {
        editModalBackdrop.addEventListener("click", closeEditModal);
    }

    if (cancelEditButton) {
        cancelEditButton.addEventListener("click", closeEditModal);
    }

    if (openCreateAlbumButton) {
        openCreateAlbumButton.addEventListener("click", () => openCreateAlbumModal("upload"));
    }

    if (openCreateAlbumFromEditButton) {
        openCreateAlbumFromEditButton.addEventListener("click", () => openCreateAlbumModal("edit"));
    }

    if (closeCreateAlbumModalButton) {
        closeCreateAlbumModalButton.addEventListener("click", closeCreateAlbumModal);
    }

    if (createAlbumModalBackdrop) {
        createAlbumModalBackdrop.addEventListener("click", closeCreateAlbumModal);
    }

    if (cancelCreateAlbumButton) {
        cancelCreateAlbumButton.addEventListener("click", closeCreateAlbumModal);
    }

    if (closeEditAlbumModalButton) {
        closeEditAlbumModalButton.addEventListener("click", closeEditAlbumModal);
    }

    if (editAlbumModalBackdrop) {
        editAlbumModalBackdrop.addEventListener("click", closeEditAlbumModal);
    }

    if (cancelEditAlbumButton) {
        cancelEditAlbumButton.addEventListener("click", closeEditAlbumModal);
    }

    if (closeEditArtistModalButton) {
        closeEditArtistModalButton.addEventListener("click", closeEditArtistModal);
    }

    if (editArtistModalBackdrop) {
        editArtistModalBackdrop.addEventListener("click", closeEditArtistModal);
    }

    if (cancelEditArtistButton) {
        cancelEditArtistButton.addEventListener("click", closeEditArtistModal);
    }

    if (closeAddToPlaylistButton) {
        closeAddToPlaylistButton.addEventListener("click", closeAddToPlaylistModal);
    }

    if (addToPlaylistBackdrop) {
        addToPlaylistBackdrop.addEventListener("click", closeAddToPlaylistModal);
    }

    if (cancelAddToPlaylistButton) {
        cancelAddToPlaylistButton.addEventListener("click", closeAddToPlaylistModal);
    }

    if (addToPlaylistForm) {
        addToPlaylistForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const playlistId = Number(getElement("add-to-playlist-select").value);
            const trackId = Number(getElement("add-to-playlist-track-id").value);

            if (!playlistId || !trackId) {
                await showInfoModal("Выбери плейлист");
                return;
            }

            const result = await apiAddTrackToPlaylist(playlistId, trackId);

            if (result.status !== "success") {
                await showInfoModal(result.message || "Ошибка добавления в плейлист");
                return;
            }

            closeAddToPlaylistModal();
            showMessage("Трек добавлен в плейлист");
        });
    }

    getElement("file")?.addEventListener("change", () => {
        setFileNameLabel("file", "file-name-label");
    });

    getElement("create-album-cover")?.addEventListener("change", () => {
        setFileNameLabel("create-album-cover", "create-album-cover-name-label");
    });

    if (deleteArtistCoverButton) {
    deleteArtistCoverButton.addEventListener("click", async () => {
        const artistId = Number(getElement("edit-artist-id").value);

        if (!artistId) return;

        const confirmed = await showConfirmModal("Удалить аватарку исполнителя?", { confirmText: "Удалить" });
        if (!confirmed) return;

        const result = await apiDeleteCover("artist", artistId);

        if (result.status !== "success") {
            await showInfoModal(result.message || "Ошибка удаления аватарки");
            return;
        }

        closeEditArtistModal();
        await renderArtistPage(artistId);
    });
}


    if (uploadFileInput && uploadFileNameLabel) {
        uploadFileInput.addEventListener("change", () => {
            const file = uploadFileInput.files && uploadFileInput.files[0];
            uploadFileNameLabel.textContent = file ? file.name : "Файл не выбран";
        });
    }

    if (uploadArtistInput) {
        uploadArtistInput.addEventListener("change", async () => {
            await loadAlbumsForArtist(uploadArtistInput.value.trim(), uploadAlbumSelect);
        });
    }

    if (editArtistInput) {
        editArtistInput.addEventListener("change", async () => {
            await loadAlbumsForArtist(editArtistInput.value.trim(), editAlbumSelect);
        });
    }

    if (uploadForm) {
        uploadForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            hideMessage();

            if (isAdmin() && !uploadAlbumSelect.value) {
                showMessage("Общий трек администратора должен принадлежать альбому");
                return;
            }

            const formData = new FormData(uploadForm);
            if (isAdmin()) {
                formData.set("album", uploadAlbumSelect.value);
            } else {
                formData.delete("album");
            }

            const result = await apiCreateTrack(formData);

            if (result.status === "success") {
    closeUploadModal();
    await renderRoute();
    showMessage("Трек загружен", "success");
    await loadArtists();
} else {
    await showInfoModal(
        getUserFriendlyMessage(result.message || "Ошибка загрузки"),
        {
            title: "Ошибка загрузки",
            buttonText: "Понятно"
        }
    );
}
        });
    }

    if (editForm) {
        editForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            hideMessage();

            const trackId = Number(getElement("edit-track-id").value);
            const editedTrack = allTracksCache.find(track => track.id === trackId) || null;

            if (editedTrack?.is_public && !editAlbumSelect.value) {
                showMessage("Общий трек должен принадлежать альбому");
                return;
            }

            const updatePayload = {
                title: getElement("edit-title").value.trim(),
                artist: getElement("edit-artist").value.trim(),
                album: editedTrack?.is_public ? editAlbumSelect.value : ""
            };

            const updateResult = await apiUpdateTrack(trackId, updatePayload);

            if (updateResult.status !== "success") {
                showMessage(updateResult.message || "Ошибка обновления");
                return;
            }

            const coverFile = getElement("edit-cover").files[0];

            if (coverFile) {
                const coverFormData = new FormData();
                coverFormData.append("cover", coverFile);

                const coverResult = await apiUpdateTrackCover(trackId, coverFormData);

                if (coverResult.status !== "success") {
                    showMessage(coverResult.message || "Ошибка обновления обложки");
                    return;
                }
            }

            showMessage("Трек обновлён");
            closeEditModal();
            await renderRoute();
            await loadArtists();
        });
    }

    if (createAlbumForm) {
        createAlbumForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            hideMessage();

            const payload = {
                artist: getElement("create-album-artist").value.trim(),
                title: getElement("create-album-title").value.trim(),
                year: getElement("create-album-year").value.trim() || null
            };

            const result = await apiCreateAlbum(payload);

            if (result.status !== "success") {
                showMessage(result.message || "Ошибка создания альбома");
                return;
            }

            const coverFile = getElement("create-album-cover")?.files?.[0] || null;

            if (coverFile) {
                const albumId = await resolveCreatedAlbumId(result, payload);

                if (albumId) {
                    const coverFormData = new FormData();
                    coverFormData.append("cover", coverFile);

                    const coverResult = await apiUpdateAlbumCover(albumId, coverFormData);

                    if (coverResult.status !== "success") {
                        showMessage(coverResult.message || "Альбом создан, но обложка не загружена");
                        return;
                    }
                }
            }

            showMessage("Альбом создан");
            closeCreateAlbumModal();

            if (albumModalSource === "edit") {
                await loadAlbumsForArtist(getElement("edit-artist").value.trim(), editAlbumSelect, payload.title);
            } else {
                await loadAlbumsForArtist(getElement("artist").value.trim(), uploadAlbumSelect, payload.title);
            }
        });
    }

    if (editAlbumForm) {
        editAlbumForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const albumId = Number(getElement("edit-album-id").value);

            const updateResult = await apiUpdateAlbum(albumId, {
                title: getElement("edit-album-title").value.trim(),
                year: getElement("edit-album-year").value.trim() || null
            });

            if (updateResult.status !== "success") {
                await showInfoModal(updateResult.message || "Ошибка обновления альбома");
                return;
            }

            const coverFile = getElement("edit-album-cover").files[0];

            if (coverFile) {
                const coverFormData = new FormData();
                coverFormData.append("cover", coverFile);

                const coverResult = await apiUpdateAlbumCover(albumId, coverFormData);

                if (coverResult.status !== "success") {
                    await showInfoModal(coverResult.message || "Ошибка обновления обложки альбома");
                    return;
                }
            }

            closeEditAlbumModal();
            await renderAlbumPage(albumId);
        });
    }

    if (editArtistForm) {
        editArtistForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const artistId = Number(getElement("edit-artist-id").value);
            const coverFile = getElement("edit-artist-cover").files[0];

            if (!coverFile) {
                await showInfoModal("Выбери файл аватарки");
                return;
            }

            const formData = new FormData();
            formData.append("cover", coverFile);

            const result = await apiUpdateArtistCover(artistId, formData);

            if (result.status !== "success") {
                await showInfoModal(result.message || "Ошибка обновления аватарки исполнителя");
                return;
            }

            closeEditArtistModal();
            await renderArtistPage(artistId);
        });
    }


    document.addEventListener("click", async (event) => {
        if (event.target?.id === "open-login-modal-button") openLoginModal();
        if (event.target?.id === "open-register-modal-button") openRegisterModal();
        if (event.target?.id === "logout-button") {
    if (typeof closePlayer === "function") {
        closePlayer();
    }

    await apiLogout();
    currentUser = null;
    applyRoleToInterface();
    navigateTo("tracks", { type: "common" });
}
    });

    getElement("close-login-modal-button")?.addEventListener("click", closeLoginModal);
    getElement("login-modal-backdrop")?.addEventListener("click", closeLoginModal);
    getElement("cancel-login-button")?.addEventListener("click", closeLoginModal);

    getElement("close-register-modal-button")?.addEventListener("click", closeRegisterModal);
    getElement("register-modal-backdrop")?.addEventListener("click", closeRegisterModal);
    getElement("cancel-register-button")?.addEventListener("click", closeRegisterModal);

    getElement("login-form")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const result = await apiLogin(
            getElement("login-username").value.trim(),
            getElement("login-password").value
        );

        if (result.status !== "success") {
            await showInfoModal(result.message || "Ошибка входа");
            return;
        }

        currentUser = result.user;
        closeLoginModal();
        applyRoleToInterface();
        await renderRoute();
    });

    getElement("register-form")?.addEventListener("submit", async (event) => {
        event.preventDefault();
        const result = await apiRegister(
            getElement("register-username").value.trim(),
            getElement("register-email").value.trim(),
            getElement("register-password").value
        );

        if (result.status !== "success") {
            await showInfoModal(result.message || "Ошибка регистрации");
            return;
        }

        closeRegisterModal();
        openLoginModal();
        await showInfoModal("Регистрация выполнена. Теперь войди в аккаунт.");
    });

    document.addEventListener("keydown", (event) => {
        if (event.key !== "Escape") return;

        const uploadModal = getElement("upload-modal");
        const editModal = getElement("edit-modal");
        const createAlbumModal = getElement("create-album-modal");
        const editAlbumModal = getElement("edit-album-modal");
        const editArtistModal = getElement("edit-artist-modal");
        const addToPlaylistModal = getElement("add-to-playlist-modal");
        const loginModal = getElement("login-modal");
        const registerModal = getElement("register-modal");

        if (uploadModal && !uploadModal.classList.contains("hidden")) {
            closeUploadModal();
        }

        if (editModal && !editModal.classList.contains("hidden")) {
            closeEditModal();
        }

        if (createAlbumModal && !createAlbumModal.classList.contains("hidden")) {
            closeCreateAlbumModal();
        }

        if (editAlbumModal && !editAlbumModal.classList.contains("hidden")) {
            closeEditAlbumModal();
        }

        if (editArtistModal && !editArtistModal.classList.contains("hidden")) {
            closeEditArtistModal();
        }

        if (addToPlaylistModal && !addToPlaylistModal.classList.contains("hidden")) {
            closeAddToPlaylistModal();
        }

        if (loginModal && !loginModal.classList.contains("hidden")) {
            closeLoginModal();
        }

        if (registerModal && !registerModal.classList.contains("hidden")) {
            closeRegisterModal();
        }
    });

    window.addEventListener("popstate", renderRoute);
}

function initTopbarSearchOverride() {
    const searchInput = getElement("shared-search-input");
    const searchButton = getElement("shared-search-button");
    const searchClear = getElement("shared-search-clear");

    if (!searchInput || !searchButton) return;

    function syncSearchClear() {
        const hasQuery = Boolean(searchInput.value.trim());
        searchClear?.classList.toggle("hidden", !hasQuery);
    }

    function goToSearch() {
        const query = searchInput.value.trim();

        if (query) {
            navigateTo("tracks", { search: query, type: currentTracksType || "common" });
        } else {
            navigateTo("tracks", { type: currentTracksType || "common" });
        }
    }

    searchButton.onclick = goToSearch;

    searchInput.oninput = syncSearchClear;

    searchInput.onkeydown = (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            goToSearch();
        }
    };

    searchClear?.addEventListener("click", () => {
        searchInput.value = "";
        syncSearchClear();
        searchInput.focus();
        navigateTo("tracks", { type: currentTracksType || "common" });
    });

    syncSearchClear();
}

async function initPage() {
    resetAlbumSelect(getElement("album-select"), "Сначала выбери исполнителя");
    resetAlbumSelect(getElement("edit-album-select"), "Сначала выбери исполнителя");

    initGlobalEvents();
    await loadCurrentUser();

    setTimeout(() => {
        initTopbarSearchOverride();
    }, 0);

    await renderRoute();
}

window.addEventListener("DOMContentLoaded", initPage);