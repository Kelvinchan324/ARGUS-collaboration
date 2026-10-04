import * as THREE from "https://esm.sh/three@0.181.2";
import { OrbitControls } from "https://esm.sh/three@0.181.2/examples/jsm/controls/OrbitControls.js";

const canvas = document.querySelector("#cad-canvas");
if (!canvas) throw new Error("CAD viewer canvas is missing");

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100);
camera.position.set(6.4, 4.2, 7.8);

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.25;

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.enablePan = false;
controls.minDistance = 4.2;
controls.maxDistance = 14;
controls.target.set(0, 1.4, 0);
let interacting = false;
controls.addEventListener("start", () => { interacting = true; });
controls.addEventListener("end", () => { interacting = false; });

scene.add(new THREE.HemisphereLight(0xcfeeff, 0x18202a, 2.8));
const key = new THREE.DirectionalLight(0xffffff, 4.2);
key.position.set(5, 8, 6);
scene.add(key);
const rim = new THREE.DirectionalLight(0xff2929, 3.2);
rim.position.set(-5, 4, -4);
scene.add(rim);
const fill = new THREE.PointLight(0x42dfff, 28, 18);
fill.position.set(0, 2, 5);
scene.add(fill);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(4.8, 72),
  new THREE.MeshStandardMaterial({ color: 0x0a1017, metalness: 0.72, roughness: 0.42 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.05;
scene.add(floor);

const materials = {
  black: new THREE.MeshStandardMaterial({ color: 0x11161c, metalness: 0.82, roughness: 0.28 }),
  dark: new THREE.MeshStandardMaterial({ color: 0x252e37, metalness: 0.65, roughness: 0.34 }),
  red: new THREE.MeshStandardMaterial({ color: 0xff2828, metalness: 0.64, roughness: 0.3 }),
  white: new THREE.MeshStandardMaterial({ color: 0xe6edf1, metalness: 0.42, roughness: 0.3 }),
  cyan: new THREE.MeshStandardMaterial({ color: 0x55ddff, emissive: 0x0c647c, emissiveIntensity: 1.25, metalness: 0.4, roughness: 0.22 }),
  screen: new THREE.MeshStandardMaterial({ color: 0x07141c, emissive: 0x2acfff, emissiveIntensity: 1.7, metalness: 0.5, roughness: 0.2 })
};

const box = (x, y, z, material, px = 0, py = 0, pz = 0) => {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(x, y, z), material);
  mesh.position.set(px, py, pz);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  return mesh;
};

const cylinder = (radius, depth, material, px = 0, py = 0, pz = 0, axis = "y") => {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, depth, 24), material);
  mesh.position.set(px, py, pz);
  if (axis === "x") mesh.rotation.z = Math.PI / 2;
  if (axis === "z") mesh.rotation.x = Math.PI / 2;
  mesh.castShadow = true;
  return mesh;
};

const beam = (length, thickness, material, position, rotation = [0, 0, 0]) => {
  const mesh = box(thickness, length, thickness, material, ...position);
  mesh.rotation.set(...rotation);
  return mesh;
};

function addWheels(group, x, z, radius = 0.28) {
  [-x, x].forEach((wheelX) => [-z, z].forEach((wheelZ) => {
    group.add(cylinder(radius, 0.22, materials.black, wheelX, radius, wheelZ, "x"));
    group.add(cylinder(radius * .45, 0.235, materials.red, wheelX, radius, wheelZ, "x"));
  }));
}

function addBimanualArms(group, shoulderY, spread, scale = 1) {
  [-1, 1].forEach((side) => {
    group.add(cylinder(.18 * scale, .25 * scale, materials.red, side * spread, shoulderY, 0, "z"));
    const upper = beam(1.25 * scale, .22 * scale, materials.dark, [side * (spread + .42 * scale), shoulderY - .45 * scale, 0], [0, 0, side * -.72]);
    const lower = beam(1.05 * scale, .19 * scale, materials.black, [side * (spread + .87 * scale), shoulderY - 1.1 * scale, .12], [side * .24, 0, side * .2]);
    group.add(upper, lower);
    group.add(box(.32 * scale, .18 * scale, .46 * scale, materials.red, side * (spread + .98 * scale), shoulderY - 1.62 * scale, .25));
  });
}

function robotAR() {
  const g = new THREE.Group();
  g.add(box(2.7, .28, 1.55, materials.black, 0, .48, 0));
  addWheels(g, 1.14, .62, .34);
  [-1.05, 1.05].forEach((x) => [-.57, .57].forEach((z) => g.add(beam(2.65, .1, materials.dark, [x, 1.73, z]))));
  g.add(box(2.32, .14, 1.15, materials.dark, 0, 1.25, 0));
  g.add(beam(2.25, .16, materials.red, [0, 2.28, 0]));
  g.add(box(1.22, .48, .74, materials.red, 0, 3.18, 0));
  g.add(box(.68, .45, .58, materials.black, 0, 3.61, 0));
  g.add(box(.18, .1, .12, materials.cyan, -.18, 3.63, .31), box(.18, .1, .12, materials.cyan, .18, 3.63, .31));
  addBimanualArms(g, 3.15, .72, .92);
  return g;
}

function alohaMini() {
  const g = new THREE.Group();
  g.add(box(2.15, .34, 1.35, materials.black, 0, .42, 0));
  addWheels(g, .87, .52, .25);
  g.add(beam(2.55, .22, materials.dark, [0, 1.7, -.23]));
  g.add(box(1.6, .18, .72, materials.black, 0, 2.45, 0));
  g.add(box(.72, .52, .42, materials.dark, 0, 2.88, -.08));
  g.add(box(.45, .23, .15, materials.cyan, 0, 2.93, .22));
  addBimanualArms(g, 2.42, .55, .72);
  return g;
}

function quadruped({ small = false } = {}) {
  const g = new THREE.Group();
  const s = small ? .78 : 1;
  g.add(box(2.15 * s, .7 * s, 1.0 * s, small ? materials.dark : materials.white, 0, 1.55 * s, 0));
  g.add(box(.55 * s, .58 * s, .72 * s, small ? materials.black : materials.white, 0, 1.62 * s, .75 * s));
  g.add(box(.28 * s, .15 * s, .08 * s, materials.screen, 0, 1.68 * s, 1.13 * s));
  [-.78, .78].forEach((x) => [-.37, .37].forEach((z) => {
    const zSide = z > 0 ? 1 : -1;
    g.add(cylinder(.15 * s, .35 * s, materials.dark, x * s, 1.28 * s, z * 1.6 * s, "z"));
    const upper = beam(.92 * s, .2 * s, small ? materials.red : materials.white, [x * 1.18 * s, .93 * s, z * 1.65 * s], [zSide * .08, 0, x > 0 ? -.45 : .45]);
    const lower = beam(.82 * s, .17 * s, materials.dark, [x * 1.42 * s, .28 * s, z * 1.68 * s], [zSide * -.12, 0, x > 0 ? .18 : -.18]);
    g.add(upper, lower);
    g.add(box(.33 * s, .12 * s, .3 * s, materials.black, x * 1.5 * s, .02, z * 1.7 * s));
  }));
  return g;
}

const modelData = {
  "robot-ar": { name: "Robot-AR", kicker: "BIMANUAL MOBILE PLATFORM", description: "A wheeled manipulation platform with two arms, an elevated sensor head, and an onboard control computer.", create: robotAR, camera: [6.4, 4.2, 7.8], targetY: 1.65 },
  aloha: { name: "Aloha Mini", kicker: "COMPACT DUAL-ARM PLATFORM", description: "A compact research robot combining a mobile base, lift structure, cameras, and two SO-101 arms.", create: alohaMini, camera: [5.6, 3.7, 7], targetY: 1.4 },
  go2: { name: "Unitree Go2", kicker: "QUADRUPED INSPECTION PLATFORM", description: "A legged robot for remote perception, inspection, telemetry, and human takeover through the ARGUS cockpit.", create: () => quadruped(), camera: [5.6, 3.2, 6.7], targetY: .8 },
  pupper: { name: "Pupper V3", kicker: "OPEN ROBOTICS & AI PLATFORM", description: "A smaller open-source quadruped used to study portable motion control, interaction, and AI behaviors.", create: () => quadruped({ small: true }), camera: [5, 2.8, 6], targetY: .65 }
};

let activeModel;
let activeKey = "robot-ar";

function selectModel(keyName) {
  const data = modelData[keyName];
  if (!data) return;
  if (activeModel) scene.remove(activeModel);
  activeKey = keyName;
  activeModel = data.create();
  activeModel.rotation.y = -.35;
  scene.add(activeModel);
  camera.position.set(...data.camera);
  controls.target.set(0, data.targetY, 0);
  controls.update();
  document.querySelector("#model-name").textContent = data.name;
  document.querySelector("#model-kicker").textContent = data.kicker;
  document.querySelector("#model-description").textContent = data.description;
  document.querySelectorAll("[data-model]").forEach((button) => button.classList.toggle("active", button.dataset.model === keyName));
}

document.querySelectorAll("[data-model]").forEach((button) => button.addEventListener("click", () => selectModel(button.dataset.model)));
document.querySelector("#reset-view")?.addEventListener("click", () => selectModel(activeKey));

const autoRotate = document.querySelector("#auto-rotate");
const resize = () => {
  const parent = canvas.parentElement;
  const width = parent.clientWidth;
  const height = parent.clientHeight;
  renderer.setSize(width, height, false);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
};
new ResizeObserver(resize).observe(canvas.parentElement);

selectModel(activeKey);
resize();

function animate() {
  requestAnimationFrame(animate);
  if (activeModel && autoRotate?.checked && !interacting) activeModel.rotation.y += .0045;
  controls.update();
  renderer.render(scene, camera);
}
animate();
