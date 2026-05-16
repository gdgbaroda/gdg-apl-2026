// Renderer-side: subscribes to apl-api /host WS and animates emoji particles
// on a fullscreen transparent canvas above the webview + quiz iframe.
//
// Config is injected by main.cjs into window.__APL__ before this script runs.
(async function () {
  // Config is injected by main.cjs after did-finish-load; wait for it.
  const cfg = await new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      const c = window.__APL__;
      if (c && c.apiBase && c.hostSecret) return resolve(c);
      if (Date.now() - start > 5000) return resolve(null);
      setTimeout(tick, 50);
    };
    tick();
  });
  if (!cfg) {
    console.warn("[reactions] missing config; overlay disabled");
    return;
  }

  const GLYPHS = {
    heart: "❤️", fire: "🔥", party: "🎉", clap: "👏", bat: "🏏",
    six: "6️⃣", four: "4️⃣", laugh: "😂", shock: "😱", raise: "🙌",
  };

  const canvas = document.getElementById("reactions-canvas");
  if (!canvas) { console.warn("[reactions] no canvas"); return; }
  const ctx = canvas.getContext("2d");

  function resize() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(window.innerWidth * dpr);
    canvas.height = Math.floor(window.innerHeight * dpr);
    canvas.style.width = window.innerWidth + "px";
    canvas.style.height = window.innerHeight + "px";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  window.addEventListener("resize", resize);

  const MAX_PARTICLES = 400;
  const particles = [];

  function spawn(glyph, n) {
    const W = window.innerWidth;
    const H = window.innerHeight;
    const burstCap = Math.min(n, 25); // per-message cap; visual is enough
    for (let i = 0; i < burstCap; i++) {
      if (particles.length >= MAX_PARTICLES) break;
      const size = 24 + Math.random() * 20;
      particles.push({
        glyph,
        x: Math.random() * W,
        y: H + size,
        vy: -(300 + Math.random() * 160),
        vx: (Math.random() - 0.5) * 40,
        size,
        rot: (Math.random() - 0.5) * 0.4,
        rotV: (Math.random() - 0.5) * 1.0,
        born: performance.now(),
        life: 1100 + Math.random() * 600,            // ms (was 1800-2700)
        sway: Math.random() * Math.PI * 2,
      });
    }
  }

  let lastFrame = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - lastFrame) / 1000);
    lastFrame = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const H = window.innerHeight;

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      const age = now - p.born;
      if (age > p.life || p.y < -p.size) {
        particles.splice(i, 1);
        continue;
      }
      p.sway += dt * 2;
      p.y += p.vy * dt;
      p.x += (p.vx + Math.sin(p.sway) * 15) * dt;
      p.rot += p.rotV * dt;

      // Fade in last 30% of life, plus when nearing top.
      const lifeFrac = age / p.life;
      const fadeLife = lifeFrac > 0.7 ? 1 - (lifeFrac - 0.7) / 0.3 : 1;
      const fadeTop = p.y < H * 0.2 ? Math.max(0, p.y / (H * 0.2)) : 1;
      const alpha = Math.max(0, Math.min(1, fadeLife * fadeTop));

      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.font = `${p.size}px system-ui, "Apple Color Emoji", "Segoe UI Emoji"`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(p.glyph, 0, 0);
      ctx.restore();
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // ---- WS with reconnect ----
  let ws = null;
  let backoff = 1000;
  function connect() {
    const wsUrl = cfg.apiBase.replace(/^http/, "ws") + "/host?key=" + encodeURIComponent(cfg.hostSecret);
    try { ws = new WebSocket(wsUrl); } catch (e) { scheduleReconnect(); return; }
    ws.addEventListener("open", () => {
      backoff = 1000;
      console.log("[reactions] ws open");
    });
    ws.addEventListener("message", (ev) => {
      let msg;
      try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.type !== "reactions" || !msg.buckets) return;
      for (const [id, count] of Object.entries(msg.buckets)) {
        const glyph = GLYPHS[id];
        if (glyph) spawn(glyph, count);
      }
    });
    ws.addEventListener("close", scheduleReconnect);
    ws.addEventListener("error", () => { try { ws.close(); } catch {} });
  }
  function scheduleReconnect() {
    setTimeout(connect, backoff);
    backoff = Math.min(backoff * 2, 15000);
  }
  connect();
})();
