"""Serve an interactive 3D view of grid.dat and its source DSM points."""

from __future__ import annotations

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import numpy as np


DATA_DIR = Path(__file__).resolve().parent
FILES = [
    "53394610_dsm_1m.dat",
    "53394611_dsm_1m.dat",
    "53394620_dsm_1m.dat",
    "53394621_dsm_1m.dat",
    "53394630_dsm_1m.dat",
    "53394631_dsm_1m.dat",
    "53394640_dsm_1m.dat",
    "53394641_dsm_1m.dat",
]
NODATA = -9999.0


PAGE = r"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DSM Grid Inspector</title>
  <style>
    :root { color-scheme: dark; font-family: "Avenir Next", "Yu Gothic UI", sans-serif; }
    * { box-sizing: border-box; }
    body { margin: 0; overflow: hidden; background: #111819; color: #e7eeeb; }
    canvas { display: block; }
    #viewport { position: fixed; inset: 0; }
    .panel { position: fixed; z-index: 2; background: #172121ee; border: 1px solid #394846; }
    #controls { top: 16px; left: 16px; width: min(340px, calc(100vw - 32px)); padding: 16px; }
    h1 { margin: 0 0 4px; font-size: 17px; font-weight: 650; }
    .subtle, .hint { color: #aabbb5; font-size: 12px; }
    #stats { margin: 12px 0; line-height: 1.7; font-variant-numeric: tabular-nums; }
    .picker { display: grid; grid-template-columns: 1fr 1fr auto; gap: 8px; align-items: end; }
    label { display: grid; gap: 5px; color: #b9c9c3; font-size: 12px; }
    input, select, button { min-width: 0; height: 36px; border: 1px solid #52635e; border-radius: 3px; background: #202e2b; color: #f2f5f2; font: inherit; }
    input { padding: 0 8px; width: 100%; }
    button { padding: 0 12px; cursor: pointer; background: #c9ef72; border-color: #c9ef72; color: #172119; font-weight: 700; }
    button:hover { background: #d8fa8c; }
    #selection { margin-top: 12px; padding-top: 10px; border-top: 1px solid #394846; font-size: 12px; line-height: 1.6; }
    .neighbor-map { position: fixed; z-index: 2; top: 290px; right: 16px; display: grid; grid-template: repeat(3, 1fr) / repeat(3, 1fr); gap: 4px; width: min(270px, calc(100vw - 32px)); }
    .map-point { display: grid; align-content: center; justify-items: center; min-width: 0; min-height: 42px; padding: 4px 2px; border: 1px solid #465650; background: #202e2b; font-variant-numeric: tabular-nums; }
    .map-point small { color: #aabbb5; font-size: 10px; }
    .map-point b { max-width: 100%; overflow: hidden; color: #ff9b88; font-size: 10px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
    .map-point[data-dir="center"] { border-color: #c9ef72; background: #303d25; }
    .map-point[data-dir="center"] b { color: #dafa9b; }
    .map-north { grid-area: 1 / 2; }
    .map-west { grid-area: 2 / 1; }
    .map-center { grid-area: 2 / 2; }
    .map-east { grid-area: 2 / 3; }
    .map-south { grid-area: 3 / 2; }
    #neighbors { width: 100%; margin-top: 8px; border-collapse: collapse; font-size: 11px; font-variant-numeric: tabular-nums; }
    #neighbors th, #neighbors td { padding: 4px 3px; text-align: right; border-bottom: 1px solid #30403c; white-space: nowrap; }
    #neighbors th:first-child, #neighbors td:first-child { text-align: left; }
    #settings { right: 16px; top: 16px; width: 190px; padding: 12px; display: grid; gap: 11px; }
    #settings input { height: auto; accent-color: #c9ef72; }
    #legend { position: fixed; right: 16px; bottom: 16px; padding: 10px 12px; font-size: 11px; }
    .swatch { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; }
    #status { position: fixed; left: 50%; bottom: 18px; transform: translateX(-50%); z-index: 3; padding: 8px 12px; background: #172121ee; border: 1px solid #394846; font-size: 12px; }
    .picker label > span { white-space: nowrap; }
    @media (max-width: 680px) {
      #controls { top: 10px; left: 10px; padding: 12px; max-height: calc(100vh - 304px); overflow: auto; }
      #settings { top: auto; right: 10px; bottom: 10px; left: 10px; width: auto; grid-template-columns: repeat(3, minmax(0, 1fr)); align-items: center; gap: 10px; }
      #legend { top: 10px; right: 10px; bottom: auto; }
      .neighbor-map { top: auto; right: auto; bottom: 150px; left: 10px; width: min(270px, calc(100vw - 20px)); }
      #status { display: none; }
      #neighbors { font-size: 10px; }
    }
  </style>
  <script type="importmap">
    {"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.180.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.180.0/examples/jsm/"}}
  </script>
</head>
<body>
  <div id="viewport"></div>
  <section id="controls" class="panel">
    <h1>DSM Grid Inspector</h1>
    <div class="subtle">grid.dat · 4近傍の確認</div>
    <div id="stats">データを読み込み中...</div>
    <form id="picker" class="picker">
      <label><span>行 (0–<span id="rowMax">-</span>)</span><input id="row" type="number" min="0" value="0" required></label>
      <label><span>列 (0–<span id="colMax">-</span>)</span><input id="col" type="number" min="0" value="0" required></label>
      <button type="submit">表示</button>
    </form>
    <div id="selection">格子を選択してください。</div>
    <table id="neighbors" hidden>
      <thead><tr><th>近傍</th><th>点ID</th><th>標高</th><th>Δ標高</th></tr></thead>
      <tbody></tbody>
    </table>
  </section>
  <div class="neighbor-map panel" aria-label="選択点と四近傍の位置関係">
    <div class="map-point map-north" data-dir="north"><small>行 −1</small><b>—</b></div>
    <div class="map-point map-west" data-dir="west"><small>列 −1</small><b>—</b></div>
    <div class="map-point map-center" data-dir="center"><small>選択</small><b>—</b></div>
    <div class="map-point map-east" data-dir="east"><small>列 +1</small><b>—</b></div>
    <div class="map-point map-south" data-dir="south"><small>行 +1</small><b>—</b></div>
  </div>
  <section id="settings" class="panel">
    <label>点群密度<select id="density"><option value="8">1/8</option><option value="4" selected>1/4</option><option value="2">1/2</option><option value="1">全点</option></select></label>
    <label>点サイズ <span id="pointSizeValue">1.5</span><input id="pointSize" type="range" min="1" max="4" value="1.5" step="0.5"></label>
    <label>高さ倍率 <span id="verticalValue">2</span>×<input id="vertical" type="range" min="1" max="8" value="2" step="0.5"></label>
  </section>
  <div id="legend" class="panel"><span class="swatch" style="background:#c9ef72"></span>選択点　<span class="swatch" style="background:#ff836c"></span>四近傍</div>
  <div id="status">点群データを読み込み中...</div>

  <script type="module">
    import * as THREE from 'three';
    import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

    const status = document.querySelector('#status');
    const number = value => Number(value).toLocaleString('ja-JP');
    const format = value => Number.isFinite(value) ? value.toFixed(2) : '—';

    async function loadBinary(url, Type) {
      const response = await fetch(url);
      if (!response.ok) throw new Error(`${url}: ${response.status}`);
      return new Type(await response.arrayBuffer());
    }

    const meta = await (await fetch('/meta.json')).json();
    const [positions, grid] = await Promise.all([
      loadBinary('/points.bin', Float32Array),
      loadBinary('/grid.bin', Int32Array),
    ]);
    const pointCount = positions.length / 3;
    const rows = meta.rows;
    const cols = meta.cols;
    document.querySelector('#row').max = rows - 1;
    document.querySelector('#col').max = cols - 1;
    document.querySelector('#rowMax').textContent = number(rows - 1);
    document.querySelector('#colMax').textContent = number(cols - 1);
    document.querySelector('#stats').innerHTML = `${number(pointCount)} 点 · ${number(meta.validCells)} セル<br>${number(rows)} 行 × ${number(cols)} 列 · 欠損標高 ${number(meta.noData)} 点`;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#111819');
    const span = Math.max(meta.xSpan, meta.ySpan, meta.zSpan * 2, 100);
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 1000000);
    function updateCameraFrustum() {
      const aspect = innerWidth / innerHeight;
      const viewHeight = span * Math.max(1.25, 1.1 / aspect);
      camera.left = -viewHeight * aspect / 2;
      camera.right = viewHeight * aspect / 2;
      camera.top = viewHeight / 2;
      camera.bottom = -viewHeight / 2;
      camera.updateProjectionMatrix();
    }
    updateCameraFrustum();
    camera.position.set(span * 0.78, span * 0.72, span * 0.95);
    const renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(innerWidth, innerHeight);
    document.querySelector('#viewport').appendChild(renderer.domElement);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(0, 0, 0);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.update();

    const terrain = new THREE.Group();
    scene.add(terrain);
    const floor = new THREE.GridHelper(span, 20, 0x52615a, 0x293532);
    terrain.add(floor);

    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const material = new THREE.ShaderMaterial({
      uniforms: { uMin: { value: meta.zMin }, uMax: { value: meta.zMax }, uSize: { value: 1.5 } },
      vertexShader: `
        uniform float uSize;
        varying float vHeight;
        void main() {
          vHeight = position.y;
          vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
          gl_Position = projectionMatrix * viewPosition;
          gl_PointSize = uSize;
          if (position.y < -10000.0) gl_PointSize = 0.0;
        }
      `,
      fragmentShader: `
        uniform float uMin;
        uniform float uMax;
        varying float vHeight;
        void main() {
          if (vHeight < -10000.0) discard;
          float t = clamp((vHeight - uMin) / max(uMax - uMin, 0.001), 0.0, 1.0);
          vec3 low = vec3(0.12, 0.66, 0.67);
          vec3 mid = vec3(0.79, 0.94, 0.45);
          vec3 high = vec3(1.0, 0.51, 0.30);
          vec3 color = t < 0.58 ? mix(low, mid, t / 0.58) : mix(mid, high, (t - 0.58) / 0.42);
          gl_FragColor = vec4(color, 0.88);
        }
      `,
    });
    const pointCloud = new THREE.Points(geometry, material);
    terrain.add(pointCloud);

    // 欠損点は有効な四近傍の平均標高(なければ最低標高)に赤で表示する
    const missingPositions = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const pointId = grid[r * cols + c];
        if (pointId < 0 || positions[pointId * 3 + 1] >= -10000) continue;
        let sum = 0;
        let count = 0;
        for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
          const nr = r + dr;
          const nc = c + dc;
          if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
          const neighborId = grid[nr * cols + nc];
          if (neighborId < 0) continue;
          const height = positions[neighborId * 3 + 1];
          if (height < -10000) continue;
          sum += height;
          count++;
        }
        missingPositions.push(positions[pointId * 3], count ? sum / count : meta.zMin, positions[pointId * 3 + 2]);
      }
    }
    const missingGeometry = new THREE.BufferGeometry();
    missingGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(missingPositions), 3));
    const missingCloud = new THREE.Points(missingGeometry, new THREE.PointsMaterial({ color: 0xff0000, size: 4, sizeAttenuation: false }));
    missingCloud.renderOrder = 4;
    missingCloud.frustumCulled = false;
    terrain.add(missingCloud);

    function setDensity(stride) {
      let validOrdinal = 0;
      let drawCount = 0;
      for (const pointId of grid) if (pointId >= 0 && validOrdinal++ % stride === 0) drawCount++;
      const indices = new Uint32Array(drawCount);
      validOrdinal = 0;
      let offset = 0;
      for (const pointId of grid) if (pointId >= 0 && validOrdinal++ % stride === 0) indices[offset++] = pointId;
      geometry.setIndex(new THREE.BufferAttribute(indices, 1));
      geometry.computeBoundingSphere();
      status.textContent = `${number(drawCount)} / ${number(pointCount)} 点を描画`;
      setTimeout(() => { status.textContent = '行・列を指定すると四近傍を表示'; }, 2600);
    }
    document.querySelector('#density').addEventListener('change', event => setDensity(Number(event.target.value)));
    setDensity(4);

    const markerGeometry = new THREE.BufferGeometry();
    markerGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(15), 3));
    const marker = new THREE.LineSegments(markerGeometry, new THREE.LineBasicMaterial({ color: 0xff836c, depthTest: false }));
    marker.renderOrder = 5;
    marker.frustumCulled = false;
    terrain.add(marker);
    const selectedGeometry = new THREE.BufferGeometry();
    selectedGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(3), 3));
    const selectedPoint = new THREE.Points(selectedGeometry, new THREE.PointsMaterial({ color: 0xc9ef72, size: 12, sizeAttenuation: false, depthTest: false }));
    selectedPoint.renderOrder = 6;
    selectedPoint.frustumCulled = false;
    terrain.add(selectedPoint);
    const neighborGeometry = new THREE.BufferGeometry();
    neighborGeometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(12), 3));
    const neighborPoints = new THREE.Points(neighborGeometry, new THREE.PointsMaterial({ color: 0xff836c, size: 9, sizeAttenuation: false, depthTest: false }));
    neighborPoints.renderOrder = 6;
    neighborPoints.frustumCulled = false;
    terrain.add(neighborPoints);

    function xyz(pointId) {
      const offset = pointId * 3;
      return [positions[offset], positions[offset + 1], positions[offset + 2]];
    }
    function elevation(pointId) { return positions[pointId * 3 + 1]; }

    let selectedRow = null;
    let selectedCol = null;
    let selectedDisplayY = null;
    let selectedMarkerOffsets = [];

    function updateNeighborZoomLimit() {
      if (selectedMarkerOffsets.length === 0) {
        controls.maxZoom = Infinity;
        return;
      }
      const radius = Math.max(...selectedMarkerOffsets.map(([x, y, z]) =>
        Math.hypot(x, y * terrain.scale.y, z)
      ));
      const viewSpan = Math.min(camera.right - camera.left, camera.top - camera.bottom);
      controls.maxZoom = radius > 0 ? Math.max(1, viewSpan / (radius * 2.6)) : Infinity;
      if (camera.zoom > controls.maxZoom) {
        camera.zoom = controls.maxZoom;
        camera.updateProjectionMatrix();
      }
    }

    function selectCell(row, col) {
      row = Math.trunc(row);
      col = Math.trunc(col);
      if (row < 0 || row >= rows || col < 0 || col >= cols) {
        status.textContent = '行または列が格子の範囲外です';
        return;
      }
      selectedRow = row;
      selectedCol = col;
      document.querySelector('#row').value = row;
      document.querySelector('#col').value = col;
      const pointId = grid[row * cols + col];
      const selection = document.querySelector('#selection');
      const table = document.querySelector('#neighbors');
      const body = table.querySelector('tbody');
      const neighborSpecs = [
        ['行 -1', row - 1, col, 'north'], ['行 +1', row + 1, col, 'south'],
        ['列 -1', row, col - 1, 'west'], ['列 +1', row, col + 1, 'east'],
      ];
      const neighbors = neighborSpecs.map(([label, neighborRow, neighborCol, direction]) => {
        const id = neighborRow < 0 || neighborRow >= rows || neighborCol < 0 || neighborCol >= cols
          ? -1 : grid[neighborRow * cols + neighborCol];
        return { label, row: neighborRow, col: neighborCol, direction, id };
      });
      const setMapPoint = (direction, label, id) => {
        const point = document.querySelector(`.map-point[data-dir="${direction}"]`);
        point.querySelector('small').textContent = label;
        if (id < 0) {
          point.querySelector('b').textContent = '—';
          point.title = `${label}: 空セルまたは範囲外`;
          return;
        }
        const height = elevation(id);
        point.querySelector('b').textContent = number(id);
        point.title = height < -10000
          ? `${label}: 点ID ${number(id)}、標高 NoData`
          : `${label}: 点ID ${number(id)}、標高 ${format(height + meta.zCenter)}m`;
      };
      for (const item of neighbors) setMapPoint(item.direction, item.label, item.id);
      if (pointId < 0) {
        selectedDisplayY = null;
        selectedMarkerOffsets = [];
        updateNeighborZoomLimit();
        selection.textContent = `行 ${number(row)}、列 ${number(col)} は空セルです。`;
        setMapPoint('center', '空セル', -1);
        table.hidden = true;
        marker.visible = false;
        selectedPoint.visible = false;
        neighborPoints.visible = false;
        return;
      }

      const center = xyz(pointId);
      setMapPoint('center', '選択', pointId);
      const missing = elevation(pointId) < -10000;
      const validElevations = neighbors.filter(item => item.id >= 0 && elevation(item.id) >= -10000).map(item => elevation(item.id));
      const markerHeight = missing && validElevations.length
        ? validElevations.reduce((sum, value) => sum + value, 0) / validElevations.length
        : elevation(pointId);
      const centerForDisplay = [center[0], missing ? markerHeight : center[1], center[2]];
      selectedDisplayY = centerForDisplay[1];
      selectedGeometry.attributes.position.setXYZ(0, ...centerForDisplay);
      selectedGeometry.attributes.position.needsUpdate = true;
      selectedPoint.visible = true;

      const lines = new Float32Array(24);
      const neighborPositions = new Float32Array(12);
      let lineOffset = 0;
      let neighborOffset = 0;
      selectedMarkerOffsets = [];
      for (const item of neighbors) {
        if (item.id < 0) continue;
        const position = xyz(item.id);
        if (elevation(item.id) < -10000) position[1] = markerHeight;
        selectedMarkerOffsets.push([
          position[0] - centerForDisplay[0],
          position[1] - centerForDisplay[1],
          position[2] - centerForDisplay[2],
        ]);
        lines.set(centerForDisplay, lineOffset); lineOffset += 3;
        lines.set(position, lineOffset); lineOffset += 3;
        neighborPositions.set(position, neighborOffset); neighborOffset += 3;
      }
      markerGeometry.setAttribute('position', new THREE.BufferAttribute(lines.slice(0, lineOffset), 3));
      neighborGeometry.setAttribute('position', new THREE.BufferAttribute(neighborPositions.slice(0, neighborOffset), 3));
      updateNeighborZoomLimit();
      marker.visible = lineOffset > 0;
      neighborPoints.visible = neighborOffset > 0;

      selection.innerHTML = `行 ${number(row)} · 列 ${number(col)} · 点ID ${number(pointId)}<br>X ${format(center[0] + meta.xCenter)} · Y ${format(-(center[2] + meta.yCenter))} · Z ${missing ? 'NoData' : format(center[1] + meta.zCenter)}`;
      body.innerHTML = neighbors.map(item => {
        if (item.id < 0) return `<tr><td>${item.label}</td><td colspan="3">範囲外 / 空セル</td></tr>`;
        const height = elevation(item.id);
        const delta = missing || height < -10000 ? '—' : format(height - elevation(pointId));
        return `<tr><td>${item.label}</td><td>${number(item.id)}</td><td>${height < -10000 ? 'NoData' : format(height + meta.zCenter)}</td><td>${delta}</td></tr>`;
      }).join('');
      table.hidden = false;
      document.querySelector('#row').value = row;
      document.querySelector('#col').value = col;
      status.textContent = missing ? '選択点は欠損標高です。マーカーは有効な近傍標高の平均位置に表示しています。' : '選択点と有効な四近傍を表示中';
      controls.target.set(centerForDisplay[0], selectedDisplayY * terrain.scale.y, centerForDisplay[2]);
    }

    document.querySelector('#picker').addEventListener('submit', event => {
      event.preventDefault();
      selectCell(Number(document.querySelector('#row').value), Number(document.querySelector('#col').value));
    });
    addEventListener('keydown', event => {
      const movement = {
        ArrowUp: [-1, 0],
        ArrowDown: [1, 0],
        ArrowLeft: [0, -1],
        ArrowRight: [0, 1],
      }[event.key];
      if (!movement || event.target.closest('input, select, textarea, button, [contenteditable="true"]')) return;

      event.preventDefault();
      let row = selectedRow ?? Number(document.querySelector('#row').value);
      let col = selectedCol ?? Number(document.querySelector('#col').value);
      while (true) {
        row += movement[0];
        col += movement[1];
        if (row < 0 || row >= rows || col < 0 || col >= cols) return;
        if (grid[row * cols + col] >= 0) {
          selectCell(row, col);
          return;
        }
      }
    });
    document.querySelector('#pointSize').addEventListener('input', event => {
      material.uniforms.uSize.value = Number(event.target.value);
      document.querySelector('#pointSizeValue').textContent = event.target.value;
    });
    document.querySelector('#vertical').addEventListener('input', event => {
      terrain.scale.y = Number(event.target.value);
      if (selectedDisplayY !== null) {
        controls.target.y = selectedDisplayY * terrain.scale.y;
        updateNeighborZoomLimit();
        controls.update();
      }
      document.querySelector('#verticalValue').textContent = event.target.value;
    });
    addEventListener('resize', () => {
      updateCameraFrustum();
      updateNeighborZoomLimit();
      renderer.setSize(innerWidth, innerHeight);
    });
    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    const start = Math.floor(rows / 2);
    let initialCell = -1;
    for (let distance = 0; distance < Math.max(rows, cols) && initialCell < 0; distance++) {
      for (let dr = -distance; dr <= distance && initialCell < 0; dr++) {
        for (let dc = -distance; dc <= distance; dc++) {
          const r = start + dr;
          const c = Math.floor(cols / 2) + dc;
          if (r >= 0 && r < rows && c >= 0 && c < cols && grid[r * cols + c] >= 0) {
            initialCell = r * cols + c;
            break;
          }
        }
      }
    }
    if (initialCell >= 0) selectCell(Math.floor(initialCell / cols), initialCell % cols);
    status.textContent = 'ドラッグで回転 · ホイールで拡大縮小';
  </script>
</body>
</html>"""


def load_data() -> tuple[np.ndarray, np.ndarray, dict[str, int | float]]:
    parts = []
    for filename in FILES:
        path = DATA_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(path)
        parts.append(np.loadtxt(path, usecols=(0, 1, 2), dtype=np.float32, ndmin=2))

    points = np.concatenate(parts, axis=0)
    del parts
    if not np.isfinite(points).all():
        raise ValueError("入力データに有限でない座標があります")

    grid_path = DATA_DIR / "grid.dat"
    if not grid_path.is_file():
        raise FileNotFoundError(grid_path)
    grid = np.loadtxt(grid_path, dtype=np.int32)
    valid = grid[grid >= 0]
    if valid.size and (int(valid.max()) >= len(points) or int(valid.min()) < 0):
        raise ValueError("grid.datに入力点数の範囲外のIDがあります")

    no_data = points[:, 2] <= NODATA
    valid_heights = points[~no_data, 2]
    if valid_heights.size == 0:
        raise ValueError("有効な標高がありません")
    x_min, x_max = float(points[:, 0].min()), float(points[:, 0].max())
    flipped_y = -points[:, 1]
    y_min, y_max = float(flipped_y.min()), float(flipped_y.max())
    z_min, z_max = float(valid_heights.min()), float(valid_heights.max())
    x_center = (x_min + x_max) / 2
    y_center = (y_min + y_max) / 2
    z_center = (z_min + z_max) / 2

    points[:, 0] -= x_center
    original_y = points[:, 1].copy()
    points[:, 1] = points[:, 2] - z_center
    points[:, 2] = -original_y - y_center
    del original_y

    metadata: dict[str, int | float] = {
        "rows": int(grid.shape[0]),
        "cols": int(grid.shape[1]),
        "validCells": int(valid.size),
        "noData": int(no_data.sum()),
        "xCenter": x_center,
        "yCenter": y_center,
        "zCenter": z_center,
        "zMin": z_min - z_center,
        "zMax": z_max - z_center,
        "xSpan": x_max - x_min,
        "ySpan": y_max - y_min,
        "zSpan": z_max - z_min,
    }
    return points, grid, metadata


def make_handler(points: np.ndarray, grid: np.ndarray, metadata: dict[str, int | float]):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                content = PAGE.encode("utf-8")
                content_type = "text/html; charset=utf-8"
            elif self.path == "/meta.json":
                info = {**metadata, "pointCount": len(points)}
                content = json.dumps(info).encode("utf-8")
                content_type = "application/json"
            elif self.path == "/points.bin":
                content = memoryview(points).cast("B")
                content_type = "application/octet-stream"
            elif self.path == "/grid.bin":
                content = memoryview(grid).cast("B")
                content_type = "application/octet-stream"
            else:
                self.send_error(404)
                return

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    try:
        points, grid, metadata = load_data()
    except (FileNotFoundError, ValueError) as error:
        raise SystemExit(f"データの読み込みに失敗しました: {error}") from error

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(points, grid, metadata))
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"3Dビューア: {url}", flush=True)
    print("終了するには Ctrl+C を押してください。", flush=True)
    threading.Timer(1, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("ビューアを終了します。")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()