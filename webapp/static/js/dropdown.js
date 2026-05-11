document.addEventListener("click", (event) => {
    const isMenuButton = event.target.closest(".menu-button");
    const allMenus = document.querySelectorAll(".dropdown-menu");

    if (!isMenuButton) {
        allMenus.forEach(menu => menu.classList.remove("open"));
        return;
    }

    const currentMenu = isMenuButton.parentElement.querySelector(".dropdown-menu");
    const isOpen = currentMenu.classList.contains("open");

    allMenus.forEach(menu => menu.classList.remove("open"));

    if (!isOpen) {
        currentMenu.classList.add("open");
    }
});