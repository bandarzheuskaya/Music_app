function getCurrentPage() {
    const params = new URLSearchParams(window.location.search);
    return params.get("page") || "tracks";
}

function getCurrentId() {
    const params = new URLSearchParams(window.location.search);
    return params.get("id");
}

function getCurrentSearchQuery() {
    const params = new URLSearchParams(window.location.search);
    return params.get("search") || "";
}

function getCurrentType() {
    const params = new URLSearchParams(window.location.search);
    return params.get("type") || "common";
}

function setActiveNavButton(page, type = "all") {
    const buttons = document.querySelectorAll(".nav-button");
    buttons.forEach(button => button.classList.remove("active"));

    if (page === "tracks" && type === "mine") {
        document.getElementById("nav-my-tracks-button")?.classList.add("active");
        return;
    }

    if (page === "tracks") {
        document.getElementById("nav-all-tracks-button")?.classList.add("active");
        return;
    }

    if (page === "artists" || page === "artist") {
        document.getElementById("nav-artists-button")?.classList.add("active");
        return;
    }

    if (page === "playlists" || page === "playlist") {
        document.getElementById("nav-playlists-button")?.classList.add("active");
        return;
    }

    if (page === "favorites") {
        document.getElementById("nav-favorites-button")?.classList.add("active");
        return;
    }

    if (page === "users" || page === "user-tracks") {
        document.getElementById("nav-users-button")?.classList.add("active");
        return;
    }

    if (page === "notifications") {
        document.getElementById("nav-notifications-button")?.classList.add("active");
    }
}

function navigateTo(page, params = {}) {
    const url = new URL("index.html", window.location.href);
    url.searchParams.set("page", page);

    Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== "") {
            url.searchParams.set(key, value);
        }
    });

    history.pushState({}, "", url);
    renderRoute();
}

async function renderRoute() {
    const page = getCurrentPage();
    const id = getCurrentId();
    const type = getCurrentType();

    setActiveNavButton(page, type);

    if (typeof updateTopbarNavigationState === "function") {
        updateTopbarNavigationState();
    }

    if (page === "album") {
        await renderAlbumPage(id);
        return;
    }

    if (page === "artist") {
        await renderArtistPage(id);
        return;
    }

    if (page === "artists") {
        await renderArtistsPage();
        return;
    }

    if (page === "playlists") {
        await renderPlaylistsPage();
        return;
    }

    if (page === "playlist") {
        await renderPlaylistPage(id);
        return;
    }

    if (page === "favorites") {
        await renderFavoritesPage();
        return;
    }

    if (page === "users") {
        await renderAdminUsersPage();
        return;
    }

    if (page === "user-tracks") {
        await renderAdminUserTracksPage(id);
        return;
    }

    if (page === "notifications") {
        await renderNotificationsPage();
        return;
    }

    await renderTracksPage(getCurrentSearchQuery(), type === "all" ? "common" : type);
}

window.addEventListener("popstate", renderRoute);
