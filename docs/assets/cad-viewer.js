import * as THREE from "three";
import { OrbitControls } from "./vendor/OrbitControls.js";
import { STLLoader } from "./vendor/STLLoader.js";

const canvas = document.querySelector("#cad-canvas");
if (!canvas) throw new Error("Verified CAD viewer canvas is missing");

const status = document.querySelector("#cad-status");
const nameNode = document.querySelector("#model-name");
const noteNode = document.querySelector("#model-note");
const revisionNode = document.querySelector("#model-revision");
const countNode = document.querySelector("#model-count");
const licenseNode = document.querySelector("#model-license");
const loader = new STLLoader();
const geometryCache = new Map();
const model = new THREE.Group();
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 10000);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });

renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.25;
renderer.shadowMap.enabled = true;

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.enablePan = false;
controls.minDistance = 45;
controls.maxDistance = 1800;

scene.add(model);
scene.add(new THREE.HemisphereLight(0xf4f0e5, 0x343733, 3.1));
const key = new THREE.DirectionalLight(0xfff4dc, 3.5);
key.position.set(250, 420, 280);
key.castShadow = true;
scene.add(key);
const rim = new THREE.DirectionalLight(0xe34b42, 2.2);
rim.position.set(-260, 220, -230);
scene.add(rim);

let assemblies;
let activeKey = "pupper";
let loadToken = 0;

function material(color, category) {
  const hardware = category === "hardware";
  return new THREE.MeshStandardMaterial({
    color,
    roughness: hardware ? 0.38 : 0.62,
    metalness: hardware ? 0.5 : 0.12
  });
}

async function geometryFor(part) {
  if (!geometryCache.has(part)) {
    geometryCache.set(part, loader.loadAsync(`cad/models/real/${part}.stl`));
  }
  return geometryCache.get(part);
}

function clearModel() {
  while (model.children.length) {
    const child = model.children.pop();
    child.material?.dispose();
  }
}

function fitCamera() {
  const bounds = new THREE.Box3().setFromObject(model);
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const distance = Math.max(size.x, size.y, size.z) * 1.85 / Math.min(1, Math.max(0.58, camera.aspect));
  controls.target.copy(center);
  camera.position.copy(center).add(new THREE.Vector3(1, 0.58, 1.35).normalize().multiplyScalar(distance));
  camera.near = Math.max(0.1, distance / 1000);
  camera.far = distance * 10;
  camera.updateProjectionMatrix();
  controls.update();
}

async function selectModel(key) {
  const assembly = assemblies?.[key];
  if (!assembly) return;
  const token = ++loadToken;
  activeKey = key;
  status.textContent = `Loading ${assembly.name}…`;
  document.querySelectorAll("[data-model]").forEach((button) => button.classList.toggle("active", button.dataset.model === key));
  nameNode.textContent = assembly.name;
  if (noteNode) noteNode.textContent = assembly.note;
  if (revisionNode) revisionNode.textContent = assembly.commit.slice(0, 7);
  if (licenseNode) licenseNode.textContent = assembly.license;
  const uniqueParts = [...new Set(assembly.slots.map((slot) => slot.part))];
  if (countNode) countNode.textContent = uniqueParts.length;

  const geometries = await Promise.all(uniqueParts.map(async (part) => [part, await geometryFor(part)]));
  if (token !== loadToken) return;
  const byPart = new Map(geometries);
  clearModel();
  for (const slot of assembly.slots) {
    const mesh = new THREE.Mesh(byPart.get(slot.part), material(slot.color, slot.category));
    mesh.position.fromArray(slot.pos);
    mesh.rotation.set(...slot.rotation.map(THREE.MathUtils.degToRad));
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    model.add(mesh);
  }
  fitCamera();
  status.textContent = `${uniqueParts.length} exact STL files loaded`;
}

document.querySelectorAll("[data-model]").forEach((button) => button.addEventListener("click", () => selectModel(button.dataset.model)));
document.querySelectorAll("[data-select-cad]").forEach((link) => link.addEventListener("click", () => selectModel(link.dataset.selectCad)));
document.querySelector("#reset-view")?.addEventListener("click", fitCamera);

function resize() {
  const parent = canvas.parentElement;
  renderer.setSize(parent.clientWidth, parent.clientHeight, false);
  camera.aspect = parent.clientWidth / parent.clientHeight;
  camera.updateProjectionMatrix();
}
new ResizeObserver(resize).observe(canvas.parentElement);

async function init() {
  try {
    const response = await fetch("cad/real-assemblies.json");
    if (!response.ok) throw new Error("Assembly manifest unavailable");
    assemblies = await response.json();
    await selectModel(activeKey);
  } catch (error) {
    status.textContent = "Verified CAD could not be loaded";
    console.error(error);
  }
}

resize();
init();

function animate() {
  requestAnimationFrame(animate);
  if (model.children.length && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) model.rotation.y += 0.0018;
  controls.update();
  renderer.render(scene, camera);
}
animate();
