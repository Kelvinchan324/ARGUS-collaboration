const menu = document.querySelector("[data-menu]");
const nav = document.querySelector("[data-nav]");
const dialog = document.querySelector("[data-dialog]");
const dialogImage = document.querySelector("[data-dialog-image]");

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

const inspectionVideo = document.querySelector("[data-local-src]");
if (inspectionVideo && window.location.protocol === "file:") {
  inspectionVideo.src = inspectionVideo.dataset.localSrc;
  inspectionVideo.load();
}

document.querySelectorAll("[data-lightbox]").forEach((button) => {
  button.addEventListener("click", () => {
    dialogImage.src = button.dataset.lightbox;
    dialogImage.alt = button.querySelector("img")?.alt || "ARGUS project visual";
    dialog?.showModal();
  });
});

document.querySelector("[data-close]")?.addEventListener("click", () => dialog?.close());
dialog?.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});
