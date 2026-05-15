function iconSvg(name) {
    const icons = {
        back: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5m6-6-6 6 6 6"/></svg>',
        home: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10.5V20h13v-9.5"/><path d="M9.5 20v-5h5v5"/></svg>',
        search: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m16 16 5 5"/></svg>'
    };

    return icons[name] || "";
}

function renderSharedTopbar() {
    const mountNode = document.getElementById("shared-topbar");
    if (!mountNode) return;

    mountNode.innerHTML = `
        <section class="global-topbar">
            <div class="global-topbar-left">
                <button id="back-button" class="icon-button top-link-button" type="button" aria-label="Назад" title="Назад">
                    ${iconSvg("back")}
                </button>
                <button id="home-button" class="icon-button top-link-button" type="button" aria-label="Главная" title="Главная">
                    ${iconSvg("home")}
                </button>
            </div>

            <div class="global-topbar-center">
                <div class="search-input-wrapper global-search-wrapper">
                    <span class="search-input-icon">${iconSvg("search")}</span>
                    <input
                        id="shared-search-input"
                        class="global-search-input"
                        type="text"
                        placeholder="Поиск по названию, исполнителю или альбому"
                        autocomplete="off"
                    >
                    <button
                        id="shared-search-clear"
                        class="search-clear-button global-search-clear hidden"
                        type="button"
                        aria-label="Очистить поиск"
                        title="Очистить поиск"
                    >×</button>
                </div>

                <button id="shared-search-button" class="icon-button search-button" type="button" aria-label="Найти" title="Найти">
                    ${iconSvg("search")}
                </button>
            </div>
        </section>
    `;
}

function updateTopbarUser(user) {
    const accountLabel = document.getElementById("account-label");
    const accountRoleLabel = document.getElementById("account-role-label");
    const loginButton = document.getElementById("open-login-modal-button");
    const registerButton = document.getElementById("open-register-modal-button");
    const logoutButton = document.getElementById("logout-button");

    if (!accountLabel || !accountRoleLabel || !loginButton || !registerButton || !logoutButton) return;

    if (user) {
        accountLabel.textContent = user.username;
        accountRoleLabel.textContent = user.role === "admin" ? "Администратор" : "Пользователь";
        loginButton.classList.add("hidden");
        registerButton.classList.add("hidden");
        logoutButton.classList.remove("hidden");
    } else {
        accountLabel.textContent = "Гость";
        accountRoleLabel.textContent = "Не авторизован";
        loginButton.classList.remove("hidden");
        registerButton.classList.remove("hidden");
        logoutButton.classList.add("hidden");
    }
}

function updateTopbarNavigationState() {
    const backButton = document.getElementById("back-button");
    const homeButton = document.getElementById("home-button");
    const page = typeof getCurrentPage === "function" ? getCurrentPage() : "tracks";
    const type = typeof getCurrentType === "function" ? getCurrentType() : "common";
    const search = typeof getCurrentSearchQuery === "function" ? getCurrentSearchQuery() : "";
    const isHome = page === "tracks" && (type === "common" || type === "all") && !search;

    if (backButton) {
        backButton.disabled = isHome;
        backButton.classList.toggle("is-disabled", isHome);
    }

    if (homeButton) {
        homeButton.classList.toggle("active", isHome);
    }
}

function initSharedTopbarSearch() {
    const searchInput = document.getElementById("shared-search-input");
    const searchButton = document.getElementById("shared-search-button");
    const searchClear = document.getElementById("shared-search-clear");
    const backButton = document.getElementById("back-button");
    const homeButton = document.getElementById("home-button");

    backButton?.addEventListener("click", () => {
        if (!backButton.disabled) history.back();
    });

    homeButton?.addEventListener("click", () => {
        if (typeof navigateTo === "function") {
            navigateTo("tracks", { type: "common" });
        } else {
            window.location.href = "index.html?page=tracks&type=common";
        }
    });

    if (!searchInput || !searchButton) {
        updateTopbarNavigationState();
        return;
    }

    function syncSearchClear() {
        searchClear?.classList.toggle("hidden", !searchInput.value.trim());
    }

    function goToSearch() {
        const query = searchInput.value.trim();
        const type = typeof getCurrentType === "function" ? getCurrentType() : "common";

        if (typeof navigateTo === "function") {
            navigateTo("tracks", query ? { search: query, type } : { type });
            return;
        }

        window.location.href = query
            ? `index.html?page=tracks&type=${encodeURIComponent(type)}&search=${encodeURIComponent(query)}`
            : `index.html?page=tracks&type=${encodeURIComponent(type)}`;
    }

    searchButton.addEventListener("click", goToSearch);

    searchInput.addEventListener("input", syncSearchClear);

    searchInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
            event.preventDefault();
            goToSearch();
        }
    });

    searchClear?.addEventListener("click", () => {
        const type = typeof getCurrentType === "function" ? getCurrentType() : "common";

        searchInput.value = "";
        syncSearchClear();
        searchInput.focus();

        if (typeof navigateTo === "function") {
            navigateTo("tracks", { type });
        }
    });

    syncSearchClear();
    updateTopbarNavigationState();
}

function initSharedTopbar() {
    renderSharedTopbar();
    initSharedTopbarSearch();
}

document.addEventListener("DOMContentLoaded", initSharedTopbar);
