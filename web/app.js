(function () {
  // ---- Counter animation ----
  function animateCounter(el, target) {
    const dur = 1400; // ms
    const start = performance.now();
    function tick(now) {
      const t = Math.min(1, (now - start) / dur);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - t, 3);
      el.textContent = Math.floor(target * eased);
      if (t < 1) requestAnimationFrame(tick);
      else el.textContent = target;
    }
    requestAnimationFrame(tick);
  }

  const counters = document.querySelectorAll('.stat-num');
  if (counters.length && 'IntersectionObserver' in window) {
    const seen = new WeakSet();
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting || seen.has(e.target)) continue;
        seen.add(e.target);
        const t = parseInt(e.target.dataset.target || '0', 10);
        animateCounter(e.target, t);
      }
    }, { threshold: 0.6 });
    counters.forEach(c => io.observe(c));
  } else {
    // Fallback: animate on load
    counters.forEach(c => animateCounter(c, parseInt(c.dataset.target || '0', 10)));
  }

  // ---- Quote carousel ----
  const quotes = Array.from(document.querySelectorAll('.quote'));
  if (quotes.length > 1) {
    let i = 0;
    setInterval(() => {
      quotes[i].classList.remove('active');
      i = (i + 1) % quotes.length;
      quotes[i].classList.add('active');
    }, 4000);
  }

  // ---- Tap-to-celebrate canvas ----
  const canvas = document.getElementById('emoji-canvas');
  const ctx = canvas.getContext('2d');
  function resize() {
    const dpr = window.devicePixelRatio || 1;
    canvas.width = innerWidth * dpr;
    canvas.height = innerHeight * dpr;
    canvas.style.width = innerWidth + 'px';
    canvas.style.height = innerHeight + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  resize();
  addEventListener('resize', resize);

  const particles = [];
  function spawn(glyph, n, originX) {
    for (let k = 0; k < n; k++) {
      const size = 24 + Math.random() * 24;
      particles.push({
        glyph,
        x: originX + (Math.random() - 0.5) * 80,
        y: innerHeight - 40,
        vy: -(320 + Math.random() * 160),
        vx: (Math.random() - 0.5) * 60,
        size,
        rot: (Math.random() - 0.5) * 0.5,
        rotV: (Math.random() - 0.5) * 1.2,
        born: performance.now(),
        life: 1500 + Math.random() * 800,
        sway: Math.random() * Math.PI * 2,
      });
    }
  }

  let lastFrame = performance.now();
  function frame(now) {
    const dt = Math.min(0.05, (now - lastFrame) / 1000);
    lastFrame = now;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      const age = now - p.born;
      if (age > p.life || p.y < -p.size) { particles.splice(i, 1); continue; }
      p.sway += dt * 2.5;
      p.y += p.vy * dt;
      p.x += (p.vx + Math.sin(p.sway) * 25) * dt;
      p.rot += p.rotV * dt;
      const lf = age / p.life;
      const fadeLife = lf > 0.7 ? 1 - (lf - 0.7) / 0.3 : 1;
      ctx.save();
      ctx.globalAlpha = Math.max(0, Math.min(1, fadeLife));
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.font = `${p.size}px system-ui, "Apple Color Emoji", "Segoe UI Emoji"`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(p.glyph, 0, 0);
      ctx.restore();
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);

  // Buttons
  document.querySelectorAll('.rxn').forEach(b => {
    b.addEventListener('pointerdown', (e) => {
      const rect = b.getBoundingClientRect();
      spawn(b.dataset.glyph || '🎉', 4, rect.left + rect.width / 2);
      b.classList.remove('burst');
      void b.offsetWidth;
      b.classList.add('burst');
      if (navigator.vibrate) navigator.vibrate(8);
    }, { passive: true });
  });

  // Auto-celebrate when podium first scrolls into view
  const podium = document.querySelector('.podium');
  if (podium && 'IntersectionObserver' in window) {
    let fired = false;
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting && !fired) {
          fired = true;
          // Burst from the centre
          for (let k = 0; k < 5; k++) {
            setTimeout(() => {
              const g = ['🎉', '🏏', '🔥', '⭐', '🙌'][k];
              spawn(g, 4, innerWidth / 2);
            }, k * 180);
          }
        }
      }
    }, { threshold: 0.4 });
    io.observe(podium);
  }

  // ──── Pre-event mode: reactions sender ────
  // Only activates when the body has data-mode="pre-event" and emoji
  // buttons exist (data-id attribute, vs the celebration mode's data-glyph).
  if (document.body.dataset.mode === 'pre-event') {
    const API = document.body.dataset.api || '';
    const FLUSH_MS = 250;
    const pending = Object.create(null);
    const status = document.getElementById('status');
    document.querySelectorAll('.btn[data-id]').forEach(b => {
      b.addEventListener('pointerdown', () => {
        const id = b.dataset.id;
        pending[id] = (pending[id] || 0) + 1;
        b.classList.remove('burst');
        void b.offsetWidth;
        b.classList.add('burst');
        if (navigator.vibrate) navigator.vibrate(8);
      }, { passive: true });
    });

    let inFlight = false;
    async function flush() {
      if (inFlight || !API) return;
      const keys = Object.keys(pending);
      if (keys.length === 0) return;
      inFlight = true;
      try {
        for (const id of keys) {
          let remaining = pending[id];
          delete pending[id];
          while (remaining > 0) {
            remaining -= 1;
            const res = await fetch(`${API}/reactions/send`, {
              method: 'POST',
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify({ e: id, n: 1 }),
              keepalive: true,
            });
            if (res.status === 429) { setStatus('slow down', false); return; }
            if (!res.ok) throw new Error('HTTP ' + res.status);
          }
        }
        setStatus('live', true);
      } catch { setStatus('offline', false); }
      finally { inFlight = false; }
    }
    function setStatus(text, live) {
      if (!status) return;
      status.textContent = text;
      status.classList.toggle('live', !!live);
    }
    setInterval(flush, FLUSH_MS);
  }
})();
