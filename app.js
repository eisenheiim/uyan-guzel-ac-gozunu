import {
  FaceLandmarker,
  FilesetResolver,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/+esm";

const EYES_CLOSED_SECONDS = 2.0;
const FACE_GONE_SECONDS = 0.8;
const AWAKE_CONFIRM_SECONDS = 0.4;
const EAR_THRESHOLD = 0.21;
const AUDIO_FACE_GONE_START = 15;
const AUDIO_EYES_CLOSED_START = 41;

const LEFT_EYE = [33, 160, 158, 133, 153, 144];
const RIGHT_EYE = [362, 385, 387, 263, 373, 380];

const ASSETS = {
  faceGone: {
    image: "assets/wake.png",
    audio: "assets/wake.mp3",
    start: AUDIO_FACE_GONE_START,
    label: "yüz kayboldu",
  },
  eyesClosed: {
    image: "assets/wake2.jpeg",
    audio: "assets/wake2.mp3",
    start: AUDIO_EYES_CLOSED_START,
    label: "gözler kapalı",
  },
};

const gate = document.getElementById("gate");
const stage = document.getElementById("stage");
const gateHint = document.getElementById("gateHint");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const statusEl = document.getElementById("status");
const viewport = document.getElementById("viewport");
const wakePanel = document.getElementById("wakePanel");
const wakeImage = document.getElementById("wakeImage");
const video = document.getElementById("video");
const overlay = document.getElementById("overlay");
const countdown = document.getElementById("countdown");
const audio = document.getElementById("audio");

const ctx = overlay.getContext("2d");

let faceLandmarker = null;
let stream = null;
let rafId = 0;
let lastVideoTime = -1;

let eyesClosedSince = null;
let faceGoneSince = null;
let awakeSince = null;
let sleeping = false;
let running = false;

function dist(a, b) {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return Math.hypot(dx, dy);
}

function eyeAspectRatio(landmarks, indices) {
  const pts = indices.map((i) => landmarks[i]);
  const v1 = dist(pts[1], pts[5]);
  const v2 = dist(pts[2], pts[4]);
  const h = dist(pts[0], pts[3]);
  if (h < 1e-6) return 0;
  return (v1 + v2) / (2 * h);
}

function setStatus(text) {
  statusEl.textContent = text;
}

function enterSleep(kind) {
  const pack = ASSETS[kind];
  sleeping = true;
  wakeImage.src = pack.image;
  wakePanel.hidden = false;
  viewport.classList.add("sleeping");
  audio.src = pack.audio;
  audio.currentTime = pack.start;
  audio.play().catch(() => {
    setStatus("müzik engellendi — tarayıcı etkileşimi gerekebilir");
  });
  setStatus(`uyku · ${pack.label}`);
}

function exitSleep() {
  sleeping = false;
  eyesClosedSince = null;
  faceGoneSince = null;
  awakeSince = null;
  audio.pause();
  audio.removeAttribute("src");
  audio.load();
  wakePanel.hidden = true;
  viewport.classList.remove("sleeping");
  countdown.hidden = true;
}

async function createLandmarker() {
  const vision = await FilesetResolver.forVisionTasks(
    "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm"
  );
  return FaceLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: "models/face_landmarker.task",
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numFaces: 1,
    minFaceDetectionConfidence: 0.5,
    minFacePresenceConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
}

function resizeOverlay() {
  const rect = video.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  overlay.width = Math.max(1, Math.floor(rect.width * dpr));
  overlay.height = Math.max(1, Math.floor(rect.height * dpr));
  overlay.style.width = `${rect.width}px`;
  overlay.style.height = `${rect.height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}

function drawEyes(landmarks) {
  const w = overlay.clientWidth;
  const h = overlay.clientHeight;
  ctx.clearRect(0, 0, w, h);
  if (!landmarks) return;

  ctx.fillStyle = "rgba(220, 220, 220, 0.85)";
  for (const idx of [...LEFT_EYE, ...RIGHT_EYE]) {
    const p = landmarks[idx];
    ctx.beginPath();
    ctx.arc(p.x * w, p.y * h, 1.4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function processFrame() {
  if (!running) return;
  rafId = requestAnimationFrame(processFrame);

  if (video.readyState < 2) return;
  if (video.currentTime === lastVideoTime) return;
  lastVideoTime = video.currentTime;

  const result = faceLandmarker.detectForVideo(video, performance.now());
  const now = performance.now() / 1000;
  let facePresent = false;
  let eyesClosed = false;
  let ear = 0;
  let landmarks = null;

  if (result.faceLandmarks?.length) {
    facePresent = true;
    faceGoneSince = null;
    landmarks = result.faceLandmarks[0];
    const left = eyeAspectRatio(landmarks, LEFT_EYE);
    const right = eyeAspectRatio(landmarks, RIGHT_EYE);
    ear = (left + right) / 2;
    eyesClosed = ear < EAR_THRESHOLD;

    if (eyesClosed) {
      if (eyesClosedSince == null) eyesClosedSince = now;
      const closedFor = now - eyesClosedSince;
      const remain = Math.max(0, EYES_CLOSED_SECONDS - closedFor);
      setStatus(`göz kapalı ${closedFor.toFixed(1)}s · EAR ${ear.toFixed(2)}`);
      if (!sleeping && remain > 0) {
        countdown.hidden = false;
        countdown.textContent = `uyku: ${remain.toFixed(1)}s`;
      } else {
        countdown.hidden = true;
      }
      if (!sleeping && closedFor >= EYES_CLOSED_SECONDS) {
        enterSleep("eyesClosed");
      }
    } else {
      eyesClosedSince = null;
      countdown.hidden = true;
      if (!sleeping) setStatus(`uyanık · EAR ${ear.toFixed(2)}`);
    }
  } else {
    eyesClosedSince = null;
    countdown.hidden = true;
    if (faceGoneSince == null) faceGoneSince = now;
    const goneFor = now - faceGoneSince;
    if (!sleeping) setStatus(`yüz yok ${goneFor.toFixed(1)}s`);
    if (!sleeping && goneFor >= FACE_GONE_SECONDS) {
      enterSleep("faceGone");
    }
  }

  drawEyes(landmarks);

  const isAwake = facePresent && !eyesClosed;
  if (sleeping) {
    if (isAwake) {
      if (awakeSince == null) awakeSince = now;
      if (now - awakeSince >= AWAKE_CONFIRM_SECONDS) {
        exitSleep();
        setStatus(`uyanık · EAR ${ear.toFixed(2)}`);
      }
    } else {
      awakeSince = null;
    }
  } else {
    awakeSince = null;
  }
}

async function start() {
  startBtn.disabled = true;
  gateHint.classList.remove("error");
  gateHint.textContent = "model yükleniyor…";

  try {
    if (!faceLandmarker) {
      faceLandmarker = await createLandmarker();
    }

    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();

    gate.classList.add("hidden");
    stage.classList.remove("hidden");
    running = true;
    lastVideoTime = -1;
    eyesClosedSince = null;
    faceGoneSince = null;
    awakeSince = null;
    sleeping = false;
    resizeOverlay();
    setStatus("uyanık — kameraya bak");
    rafId = requestAnimationFrame(processFrame);
  } catch (err) {
    console.error(err);
    gateHint.classList.add("error");
    gateHint.textContent =
      err?.name === "NotAllowedError"
        ? "Kamera izni reddedildi. Tarayıcı ayarlarından izin ver."
        : "Kamera açılamadı. HTTPS veya localhost gerekir; izinleri kontrol et.";
    startBtn.disabled = false;
  }
}

function stop() {
  running = false;
  cancelAnimationFrame(rafId);
  exitSleep();
  if (stream) {
    for (const track of stream.getTracks()) track.stop();
    stream = null;
  }
  video.srcObject = null;
  ctx.clearRect(0, 0, overlay.width, overlay.height);
  stage.classList.add("hidden");
  gate.classList.remove("hidden");
  startBtn.disabled = false;
  gateHint.classList.remove("error");
  gateHint.textContent = "Kamera izni gerekir · tarayıcıda çalışır";
}

startBtn.addEventListener("click", start);
stopBtn.addEventListener("click", stop);
window.addEventListener("resize", () => {
  if (running) resizeOverlay();
});
video.addEventListener("loadedmetadata", resizeOverlay);
