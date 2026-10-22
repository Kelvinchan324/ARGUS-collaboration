"use strict";
const feeds = document.querySelector("#feeds");
const connection = document.querySelector("#connection");
const cards = new Map();

async function toggleFullscreen(element) {
  try {
    if (document.fullscreenElement === element) await document.exitFullscreen();
    else if (element.requestFullscreen) await element.requestFullscreen();
  } catch { connection.textContent = "Fullscreen is unavailable in this browser"; }
}
document.querySelector("#fullscreen").addEventListener("click", () => toggleFullscreen(document.documentElement));
for (const mode of ["overview", "grid"]) {
  document.querySelector(`#${mode}`).addEventListener("click", () => {
    feeds.classList.toggle("equal", mode === "grid");
    for (const name of ["overview", "grid"]) document.querySelector(`#${name}`).setAttribute("aria-pressed", String(mode === name));
  });
}

function makeCard(camera) {
  const card = document.querySelector("#camera-card").content.firstElementChild.cloneNode(true);
  card.querySelector("h2").textContent = camera.label;
  card.querySelector(".camera-number").textContent = String(camera.id + 1).padStart(2, "0");
  card.querySelector(".source").textContent = `DEVICE / ${camera.source}`;
  const image = card.querySelector(".feed");
  image.alt = camera.label;
  image.addEventListener("error", () => { image.removeAttribute("src"); card.dataset.online = "false"; });
  card.querySelector(".expand").addEventListener("click", () => toggleFullscreen(card));
  feeds.append(card);
  cards.set(camera.id, card);
  return card;
}

async function refresh() {
  try {
    const response = await fetch("/api/cameras", {cache: "no-store", signal: AbortSignal.timeout(2500)});
    if (!response.ok) throw new Error("Camera service unavailable");
    const {cameras} = await response.json();
    const ids = new Set(cameras.map(camera => camera.id));
    for (const [id, card] of cards) if (!ids.has(id)) { card.remove(); cards.delete(id); }
    let online = 0;
    for (const camera of cameras) {
      const card = cards.get(camera.id) || makeCard(camera);
      const image = card.querySelector(".feed");
      card.dataset.online = String(camera.online);
      card.querySelector(".badge").textContent = camera.online ? "Live" : "Offline";
      card.querySelector(".offline-message strong").textContent = "Camera unavailable";
      card.querySelector(".reason").textContent = camera.error || "Reconnecting automatically";
      card.querySelector(".resolution").textContent = camera.online && camera.resolution ? `${camera.resolution.join(" × ")} px` : "No live frames";
      // Reconnect after a browser/network error; one missing USB camera does
      // not restart the other feeds. Never display a stale frame as live.
      if (camera.online) {
        online++;
        if (!image.hasAttribute("src")) image.src = `/stream/${camera.id}?reconnect=${Date.now()}`;
      } else image.removeAttribute("src");
    }
    connection.dataset.state = online === cameras.length && online > 0 ? "live" : "partial";
    connection.textContent = `${online} / ${cameras.length} cameras live`;
  } catch {
    connection.dataset.state = "offline";
    connection.textContent = "Camera service disconnected · Reconnecting";
    for (const card of cards.values()) {
      card.dataset.online = "false";
      card.querySelector(".badge").textContent = "Offline";
      card.querySelector(".offline-message strong").textContent = "Connection lost";
      card.querySelector(".reason").textContent = "Check the follower service and network. Retrying automatically.";
      card.querySelector(".feed").removeAttribute("src");
    }
  } finally { setTimeout(refresh, 1000); }
}
refresh();
