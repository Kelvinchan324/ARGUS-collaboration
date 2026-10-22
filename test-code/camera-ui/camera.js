"use strict";
const feeds = document.querySelector("#feeds");
const connection = document.querySelector("#connection");
const cards = new Map();
const panels = new Map();
const joints = [["shoulder_pan", "PAN"], ["shoulder_lift", "LIFT"], ["elbow_flex", "ELBOW"],
  ["wrist_flex", "WRIST P"], ["wrist_roll", "WRIST R"], ["gripper", "GRIP"]];
let cameraStates = [];
let centerView = "top";

async function toggleFullscreen(element) {
  try {
    if (document.fullscreenElement === element) await document.exitFullscreen();
    else if (element.requestFullscreen) await element.requestFullscreen();
  } catch { connection.textContent = "Fullscreen unavailable"; }
}
document.querySelector("#fullscreen").addEventListener("click", () => toggleFullscreen(document.documentElement));

function selectCenter(role) {
  centerView = role;
  for (const name of ["top", "front"]) {
    const button = document.querySelector(`#view-${name}`);
    const configured = cameraStates.some(camera => camera.role === name);
    button.disabled = !configured;
    button.title = configured ? "" : `Configure SO101_CAMERA_${name.toUpperCase()} on the follower`;
    button.setAttribute("aria-pressed", String(role === name));
  }
  for (const card of cards.values()) {
    const isCenter = ["top", "front"].includes(card.dataset.role);
    card.hidden = isCenter && card.dataset.role !== role;
    const camera = cameraStates.find(state => String(state.id) === card.dataset.cameraId);
    const image = card.querySelector(".feed");
    // Only the selected center camera streams to this browser. A view switch
    // never touches the arm receiver or restarts either gripper stream.
    if (card.hidden || !camera?.online) image.removeAttribute("src");
    else if (!image.hasAttribute("src")) image.src = `/stream/${camera.id}?reconnect=${Date.now()}`;
  }
}
for (const role of ["top", "front"]) {
  document.querySelector(`#view-${role}`).addEventListener("click", () => selectCenter(role));
}

function makeCard(camera) {
  const card = document.querySelector("#camera-card").content.firstElementChild.cloneNode(true);
  card.querySelector("h2").textContent = camera.label;
  card.dataset.cameraId = String(camera.id);
  card.dataset.role = camera.role;
  const image = card.querySelector(".feed");
  image.alt = camera.label;
  image.addEventListener("error", () => { image.removeAttribute("src"); card.dataset.online = "false"; });
  const expand = card.querySelector(".expand");
  expand.setAttribute("aria-label", `Expand ${camera.label}`);
  expand.addEventListener("click", () => toggleFullscreen(card));
  const slot = ["left", "right"].includes(camera.role) ? camera.role : "center";
  document.querySelector(`[data-slot="${slot}"]`).append(card);
  cards.set(camera.id, card);
  return card;
}

async function refreshCameras() {
  try {
    const response = await fetch("/api/cameras", {cache: "no-store", signal: AbortSignal.timeout(2500)});
    if (!response.ok) throw new Error("Camera service unavailable");
    const {cameras} = await response.json();
    cameraStates = cameras;
    const ids = new Set(cameras.map(camera => camera.id));
    for (const [id, card] of cards) if (!ids.has(id)) { card.remove(); cards.delete(id); }
    let online = 0;
    for (const camera of cameras) {
      const card = cards.get(camera.id) || makeCard(camera);
      card.dataset.online = String(camera.online);
      card.querySelector(".badge").textContent = camera.online ? "Live" : "Offline";
      card.querySelector(".offline-message strong").textContent = "Reconnecting";
      card.title = camera.online ? `Device ${camera.source}${camera.resolution ? ` · ${camera.resolution.join(" × ")}` : ""}` : camera.error;
      if (camera.online) online++;
    }
    if (!cameras.some(camera => camera.role === centerView)) centerView = cameras[0]?.role || "top";
    selectCenter(centerView);
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
  } finally { setTimeout(refreshCameras, 1000); }
}

for (const side of ["left", "right"]) {
  const panel = document.querySelector(`.telemetry[data-side="${side}"]`);
  panel.append(document.querySelector("#telemetry-panel").content.cloneNode(true));
  panel.querySelector("h2").textContent = `${side === "left" ? "L" : "R"} // ARM`;
  const values = new Map();
  for (const [joint, label] of joints) {
    const row = document.createElement("div");
    const name = document.createElement("dt");
    const value = document.createElement("dd");
    name.textContent = label;
    value.textContent = "—";
    row.append(name, value);
    panel.querySelector("dl").append(row);
    values.set(joint, value);
  }
  panels.set(side, {panel, values, history: []});
}

function renderTelemetry(data) {
  document.querySelector("#receiver-status").textContent = data.available ? "RX ONLINE" : "RX OFFLINE";
  for (const [side, {panel, values, history}] of panels) {
    const arm = data.available ? data.arms[side] : null;
    const fresh = arm?.fresh === true;
    panel.dataset.fresh = String(fresh);
    panel.querySelector(".arm-status").textContent = fresh ? "RX LIVE" : (arm?.packets > 0 ? "STALE" : "WAIT");
    panel.querySelector(".rate").textContent = fresh && Number.isFinite(arm.rate_hz) ? arm.rate_hz.toFixed(1) : "—";
    panel.querySelector(".age").textContent = Number.isFinite(arm?.packet_age_ms) ? (arm.packet_age_ms > 9999 ? "9999+" : arm.packet_age_ms.toString()) : "—";
    for (const [joint, element] of values) {
      const value = fresh ? arm.targets[joint] : null;
      element.textContent = Number.isFinite(value) ? value.toFixed(1) : "—";
    }
    if (fresh && Number.isFinite(arm.rate_hz)) {
      history.push(arm.rate_hz);
      if (history.length > 40) history.shift();
    } else history.length = 0;
    const ceiling = Math.max(data.frequency || 1, ...history, 1);
    panel.querySelector("polyline").setAttribute("points", history.map((value, index) =>
      `${index * 240 / 39},${38 - Math.min(value / ceiling, 1) * 34}`).join(" "));
  }
}

async function refreshTelemetry() {
  try {
    const response = await fetch("/api/telemetry", {cache: "no-store", signal: AbortSignal.timeout(1500)});
    if (!response.ok) throw new Error("Telemetry unavailable");
    renderTelemetry(await response.json());
  } catch { renderTelemetry({available: false, arms: {}}); }
  finally { setTimeout(refreshTelemetry, 500); }
}
refreshCameras();
refreshTelemetry();
