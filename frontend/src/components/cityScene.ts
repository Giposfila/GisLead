import * as THREE from "three";

/** A schematic city, never a representation of collected lead locations. */
export function mountCity(host: HTMLDivElement) {
  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setClearColor(0x000000, 0);
  host.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-7, 7, 5, -5, 0.1, 80);
  camera.position.set(12, 13, 15);
  camera.lookAt(0, 0, 0);
  const city = new THREE.Group();
  scene.add(city);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x65754c, 2.5));
  const sunlight = new THREE.DirectionalLight(0xffffff, 3);
  sunlight.position.set(-3, 9, 5);
  scene.add(sunlight);

  // All blocks share one geometry and material; instance IDs are stable row/column IDs.
  const cube = new THREE.BoxGeometry(1, 1, 1);
  const buildingMaterial = new THREE.MeshStandardMaterial({
    color: 0xffffff,
    roughness: 0.9,
  });
  const buildings = new THREE.InstancedMesh(cube, buildingMaterial, 64);
  const transform = new THREE.Object3D();
  const color = new THREE.Color();
  for (let row = 0; row < 8; row++) {
    for (let column = 0; column < 8; column++) {
      const id = row * 8 + column;
      const height = 0.25 + ((id * 17 + row * 11) % 13) * 0.085;
      const x = (column - 3.5) * 1.08 + (column > 3 ? 0.42 : -0.42);
      const z = (row - 3.5) * 1.08 + (row > 3 ? 0.42 : -0.42);
      transform.position.set(x, height / 2, z);
      transform.scale.set(0.65 + (id % 3) * 0.06, height, 0.7);
      transform.updateMatrix();
      buildings.setMatrixAt(id, transform.matrix);
      buildings.setColorAt(
        id,
        color.setHex(
          id % 11 === 0 ? 0xa5ff4f : id % 3 === 0 ? 0xb8c6a4 : 0xd8dfcb,
        ),
      );
    }
  }
  buildings.instanceMatrix.needsUpdate = true;
  if (buildings.instanceColor) buildings.instanceColor.needsUpdate = true;
  buildings.computeBoundingSphere();
  city.add(buildings);

  const groundMaterial = new THREE.MeshStandardMaterial({
    color: 0xdce3d0,
    roughness: 1,
  });
  const base = new THREE.Mesh(cube, groundMaterial);
  base.position.y = -0.18;
  base.scale.set(10.5, 0.28, 10.5);
  city.add(base);
  const grid = new THREE.GridHelper(10.4, 20, 0xc4ceb6, 0xc4ceb6);
  grid.position.y = -0.025;
  city.add(grid);

  const ringGeometry = new THREE.RingGeometry(0.97, 1, 96);
  const ringMaterial = new THREE.MeshBasicMaterial({
    color: 0x74b92e,
    transparent: true,
    opacity: 0.6,
    side: THREE.DoubleSide,
    depthWrite: false,
  });
  const rings = Array.from({ length: 3 }, (_, index) => {
    const ring = new THREE.Mesh(ringGeometry, ringMaterial.clone());
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.035;
    ring.scale.setScalar(1.4 + index * 1.45);
    city.add(ring);
    return ring;
  });

  const pinGeometry = new THREE.OctahedronGeometry(0.23);
  const pinMaterial = new THREE.MeshStandardMaterial({
    color: 0x9df345,
    roughness: 0.4,
    metalness: 0.1,
  });
  const stemGeometry = new THREE.CylinderGeometry(0.018, 0.018, 1.1, 6);
  const stemMaterial = new THREE.MeshBasicMaterial({ color: 0x709947 });
  const locations = [
    [-2.04, 1.85, -2.04],
    [2.04, 2.2, 0.96],
    [-0.96, 1.65, 3.12],
  ];
  const pins = locations.map(([x, y, z]) => {
    const pin = new THREE.Mesh(pinGeometry, pinMaterial);
    pin.position.set(x, y, z);
    const stem = new THREE.Mesh(stemGeometry, stemMaterial);
    stem.position.set(x, y - 0.6, z);
    city.add(pin, stem);
    return pin;
  });

  const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let paused = false;
  let visible = true;
  let disposed = false;
  let frame = 0;
  let previous = 0;
  let elapsed = 0;
  let pointerX = 0;
  let pointerY = 0;
  const render = () => renderer.render(scene, camera);
  const tick = (now: number) => {
    frame = 0;
    if (disposed) return;
    const delta = previous ? Math.min((now - previous) / 1000, 0.05) : 0;
    previous = now;
    elapsed += delta;
    const damping = 1 - Math.exp(-4 * delta);
    city.rotation.y += (pointerX * 0.08 - city.rotation.y) * damping;
    city.rotation.x += (pointerY * 0.035 - city.rotation.x) * damping;
    rings.forEach((ring, index) => {
      const phase = (elapsed * 0.14 + index / 3) % 1;
      ring.scale.setScalar(0.4 + phase * 5.6);
      ring.material.opacity = (1 - phase) * 0.55;
    });
    pins.forEach((pin, index) => {
      pin.position.y =
        locations[index][1] + Math.sin(elapsed * 1.6 + index * 2) * 0.09;
      pin.rotation.y = elapsed * 0.35;
    });
    render();
    frame = requestAnimationFrame(tick);
  };
  const syncMotion = () => {
    if (disposed) return;
    cancelAnimationFrame(frame);
    frame = 0;
    previous = 0;
    if (motion.matches) {
      city.rotation.set(0, 0, 0);
      pins.forEach((pin, i) => {
        pin.position.y = locations[i][1];
        pin.rotation.y = 0;
      });
      rings.forEach((ring, i) => {
        ring.scale.setScalar(1.4 + i * 1.45);
        ring.material.opacity = 0.35;
      });
    }
    if (!paused && !motion.matches && visible && !document.hidden && !disposed)
      frame = requestAnimationFrame(tick);
    render();
  };
  const resize = () => {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    const aspect = width / height;
    const halfHeight = Math.max(5.9, 6.6 / aspect);
    camera.left = -halfHeight * aspect;
    camera.right = halfHeight * aspect;
    camera.top = halfHeight;
    camera.bottom = -halfHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    render();
  };
  const onPointer = (event: PointerEvent) => {
    if (event.pointerType === "touch") return;
    const rect = host.getBoundingClientRect();
    pointerX = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    pointerY = ((event.clientY - rect.top) / rect.height) * 2 - 1;
  };
  const resetPointer = () => {
    pointerX = 0;
    pointerY = 0;
  };
  const onContextLost = (event: Event) => {
    event.preventDefault();
    visible = false;
    delete host.dataset.ready;
    syncMotion();
  };
  const onContextRestored = () => {
    visible = true;
    host.dataset.ready = "true";
    resize();
    syncMotion();
  };
  const sizeObserver = new ResizeObserver(resize);
  const intersection = new IntersectionObserver(([entry]) => {
    visible = entry.isIntersecting;
    syncMotion();
  });
  sizeObserver.observe(host);
  intersection.observe(host);
  host.addEventListener("pointermove", onPointer);
  host.addEventListener("pointerleave", resetPointer);
  renderer.domElement.addEventListener("webglcontextlost", onContextLost);
  renderer.domElement.addEventListener(
    "webglcontextrestored",
    onContextRestored,
  );
  document.addEventListener("visibilitychange", syncMotion);
  motion.addEventListener("change", syncMotion);
  resize();
  syncMotion();
  host.dataset.ready = "true";

  return {
    setPaused(value: boolean) {
      paused = value;
      syncMotion();
    },
    dispose() {
      disposed = true;
      cancelAnimationFrame(frame);
      sizeObserver.disconnect();
      intersection.disconnect();
      document.removeEventListener("visibilitychange", syncMotion);
      motion.removeEventListener("change", syncMotion);
      host.removeEventListener("pointermove", onPointer);
      host.removeEventListener("pointerleave", resetPointer);
      renderer.domElement.removeEventListener(
        "webglcontextlost",
        onContextLost,
      );
      renderer.domElement.removeEventListener(
        "webglcontextrestored",
        onContextRestored,
      );
      // Shared resources are released exactly once, after their final consumer.
      const geometries = new Set<THREE.BufferGeometry>();
      const materials = new Set<THREE.Material>();
      scene.traverse((node) => {
        if (node instanceof THREE.Mesh || node instanceof THREE.LineSegments) {
          geometries.add(node.geometry);
          (Array.isArray(node.material)
            ? node.material
            : [node.material]
          ).forEach((material) => materials.add(material));
        }
      });
      buildings.dispose();
      ringMaterial.dispose();
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      renderer.dispose();
      renderer.domElement.remove();
      delete host.dataset.ready;
    },
  };
}
