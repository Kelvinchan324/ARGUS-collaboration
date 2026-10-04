const menu = document.querySelector("[data-menu]");
const nav = document.querySelector("[data-nav]");

menu?.addEventListener("click", () => {
  const open = nav.classList.toggle("open");
  menu.setAttribute("aria-expanded", String(open));
});

nav?.querySelectorAll("a").forEach((link) => {
  link.addEventListener("click", () => {
    nav.classList.remove("open");
    menu?.setAttribute("aria-expanded", "false");
  });
});

document.querySelector("[data-print]")?.addEventListener("click", () => window.print());
