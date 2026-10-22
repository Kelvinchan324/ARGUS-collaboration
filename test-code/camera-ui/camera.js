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

function makeCard(camera) {
  const card = document.querySelector("#camera-card").content.firstElementChild.cloneNode(true);
  card.querySelector("h2").textContent = camera.label;
  card.dataset.cameraId = String(camera.id);
  const image = card.querySelector(".feed");
  image.alt = camera.label;
  image.addEventListener("error", () => { image.removeAttribute("src"); card.dataset.online = "false"; });
  const expand = card.querySelector(".expand");
  expand.setAttribute("aria-label", `Expand ${camera.label}`);
  expand.addEventListener("click", () => toggleFullscreen(card));
  feeds.append(card);
  cards.set(camera.id, card);
  return card;
}

async function refresh() {
  try {
    const response = await fetch("/api/cameras", {cache: "no-store", signal: AbortSignal.timeout(2500)});
    if (!response.ok) throw new Error("Camera service unavailable");
    const {cameras} = await response.json();
    feeds.classList.toggle("triple", cameras.length === 3);
    const ids = new Set(cameras.map(camera => camera.id));
    for (const [id, card] of cards) if (!ids.has(id)) { card.remove(); cards.delete(id); }
    let online = 0;
    // API IDs stay top=0, left=1, right=2; show them in physical left-to-right order.
    const ordered = cameras.length === 3 ? [cameras[1], cameras[0], cameras[2]] : cameras;
    for (const camera of ordered) {
      const card = cards.get(camera.id) || makeCard(camera);
      const image = card.querySelector(".feed");
      card.dataset.online = String(camera.online);
      card.querySelector(".badge").textContent = camera.online ? "Live" : "Offline";
      card.querySelector(".offline-message strong").textContent = "Reconnecting";
      // Keep device diagnostics available on hover without cluttering the view.
      card.title = camera.online ? `Device ${camera.source}${camera.resolution ? ` · ${camera.resolution.join(" × ")}` : ""}` : camera.error;
      // Reconnect after a browser/network error; one missing USB camera does
      // not restart the other feeds. Never display a stale frame as live.
      if (camera.online) {
        online++;
        if (!image.hasAttribute("src")) image.src = `/stream/${camera.id}?reconnect=${Date.now()}`;
      } else image.removeAttribute("src");
    }
    connection.dataset.state = online === cameras.length && online > 0 ? "live" : "partial";
    connection.textContent = `${online}/${cameras.length} live`;
  } catch {
    connection.dataset.state = "offline";
    connection.textContent = "Reconnecting";
    for (const card of cards.values()) {
      card.dataset.online = "false";
      card.querySelector(".badge").textContent = "Offline";
      card.querySelector(".offline-message strong").textContent = "Connection lost";
      card.title = "Check the follower service and network";
      card.querySelector(".feed").removeAttribute("src");
    }
  } finally { setTimeout(refresh, 1000); }
}
refresh();
