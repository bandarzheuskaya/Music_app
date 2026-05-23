const API_BASE = `${window.location.protocol}//${window.location.hostname}:8080`;

const apiCache = new Map();

async function apiRequest(path, options = {}) {
    try {
        const method = (options.method || "GET").toUpperCase();
const isGetRequest = method === "GET";

const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    cache: isGetRequest ? "default" : "no-store",
    ...options,
    headers: options.headers || undefined
});

        if (response.status === 204) {
            return { status: "success" };
        }

        let data = null;

        try {
            data = await response.json();
        } catch (_error) {
            data = null;
        }

        if (!response.ok) {
            return {
                status: "error",
                message:
                    data?.message ||
                    `Ошибка сервера (${response.status})`
            };
        }

        return data || {
            status: "success"
        };

    } catch (_error) {
        return {
            status: "error",
            message: "Не удалось подключиться к серверу"
        };
    }
}


async function cachedGet(path, ttl = 30000) {
    const cached = apiCache.get(path);

    if (cached && Date.now() - cached.time < ttl) {
        return cached.data;
    }

    const result = await apiRequest(path);

    if (result.status === "success") {
        apiCache.set(path, {
            data: result,
            time: Date.now()
        });
    }

    return result;
}

function clearApiCache() {
    apiCache.clear();
}

function buildTrackQuery(type = "all") {
    const params = new URLSearchParams();

    if (type && type !== "all") {
        params.set("type", type);
    }

    const queryString = params.toString();
    return queryString ? `?${queryString}` : "";
}

async function apiGetTracks(type = "all") {
    return apiRequest(`/api/tracks${buildTrackQuery(type)}`);
}

async function apiSearchTracks(query, type = "all") {
    const params = new URLSearchParams();

    params.set("q", query || "");

    if (type && type !== "all") {
        params.set("type", type);
    }

    return apiRequest(`/api/tracks/search?${params.toString()}`);
}

async function apiGetArtists() {
    return cachedGet("/api/artists");
}

async function apiGetArtistById(artistId) {
    return cachedGet(`/api/artists/${artistId}`);
}

async function apiGetArtistTracks(artistId) {
    return cachedGet(`/api/artists/${artistId}/tracks`);
}

async function apiGetArtistAlbums(artistId) {
    return cachedGet(`/api/artists/${artistId}/albums`);
}

async function apiGetAlbumsByArtist(artist) {
    return cachedGet(`/api/albums?artist=${encodeURIComponent(artist)}`);
}

async function apiGetAlbumById(albumId) {
    return cachedGet(`/api/albums/${albumId}`);
}

async function apiGetAlbumTracks(albumId) {
    return cachedGet(`/api/albums/${albumId}/tracks`);
}

async function apiCreateAlbum(payload) {
    const result = await apiRequest("/api/albums", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiCreateTrack(formData) {
    const result = await apiRequest("/api/tracks", {
        method: "POST",
        body: formData
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiDeleteTrack(trackId) {
    const result = await apiRequest(`/api/tracks/${trackId}`, {
        method: "DELETE"
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiUpdateTrack(trackId, payload) {
    const result = await apiRequest(`/api/tracks/${trackId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiUpdateTrackCover(trackId, formData) {
    const result = await apiRequest(`/api/tracks/${trackId}/cover`, {
        method: "POST",
        body: formData
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiUpdateAlbum(albumId, payload) {
    const result = await apiRequest(`/api/albums/${albumId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiUpdateAlbumCover(albumId, formData) {
    const result = await apiRequest(`/api/albums/${albumId}/cover`, {
        method: "POST",
        body: formData
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiUpdateArtistCover(artistId, formData) {
    const result = await apiRequest(`/api/artists/${artistId}/cover`, {
        method: "POST",
        body: formData
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiDeleteCover(entityType, entityId) {
    const result = await apiRequest(`/api/covers/${entityType}/${entityId}`, {
        method: "DELETE"
    });

    if (result.status !== "error") {
        clearApiCache();
    }

    return result;
}

async function apiRegister(usernameOrPayload, email, password) {
    const payload = typeof usernameOrPayload === "object"
        ? usernameOrPayload
        : {
            username: usernameOrPayload,
            email: email,
            password: password
        };

    return apiRequest("/api/auth/register", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
}

async function apiLogin(usernameOrPayload, password) {
    const payload = typeof usernameOrPayload === "object"
        ? usernameOrPayload
        : {
            username: usernameOrPayload,
            password: password
        };

    return apiRequest("/api/auth/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
}

async function apiLogout() {
    return apiRequest("/api/auth/logout", {
        method: "POST"
    });
}

async function apiGetMe() {
    return apiRequest("/api/auth/me");
}

async function apiGetFavorites() {
    return apiRequest("/api/favorites");
}

async function apiAddFavorite(trackId) {
    return apiRequest(`/api/favorites/${trackId}`, {
        method: "POST"
    });
}

async function apiRemoveFavorite(trackId) {
    return apiRequest(`/api/favorites/${trackId}`, {
        method: "DELETE"
    });
}

async function apiGetPlaylists() {
    return apiRequest("/api/playlists");
}

async function apiCreatePlaylist(titleOrPayload) {
    const payload = typeof titleOrPayload === "object"
        ? titleOrPayload
        : {
            title: titleOrPayload
        };

    return apiRequest("/api/playlists", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
}

async function apiGetPlaylist(playlistId) {
    return apiRequest(`/api/playlists/${playlistId}`);
}

async function apiUpdatePlaylist(playlistId, titleOrPayload) {
    const payload = typeof titleOrPayload === "object"
        ? titleOrPayload
        : {
            title: titleOrPayload
        };

    return apiRequest(`/api/playlists/${playlistId}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });
}

async function apiDeletePlaylist(playlistId) {
    return apiRequest(`/api/playlists/${playlistId}`, {
        method: "DELETE"
    });
}

async function apiAddTrackToPlaylist(playlistId, trackId) {
    return apiRequest(`/api/playlists/${playlistId}/tracks/${trackId}`, {
        method: "POST"
    });
}

async function apiRemoveTrackFromPlaylist(playlistId, trackId) {
    return apiRequest(`/api/playlists/${playlistId}/tracks/${trackId}`, {
        method: "DELETE"
    });
}
async function apiAdminGetUsers() {
    return apiRequest("/api/admin/users");
}

async function apiAdminUpdateUserRole(userId, role) {
    return apiRequest(`/api/admin/users/${userId}/role`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ role })
    });
}

async function apiAdminGetUserTracks(userId) {
    return apiRequest(`/api/admin/users/${userId}/tracks`);
}

async function apiAdminDeleteUserTrack(userId, trackId) {
    return apiRequest(`/api/admin/users/${userId}/tracks/${trackId}`, {
        method: "DELETE"
    });
}

async function apiGetNotifications() {
    return apiRequest("/api/notifications");
}

function buildMediaUrl(path) {
    if (!path) return "";
    return `${API_BASE}${path}`;
}
