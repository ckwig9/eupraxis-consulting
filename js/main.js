/* Eupraxis Consulting site behaviour.
   Dependencies (loaded before this file): GSAP + ScrollTrigger. Optional; the page degrades gracefully. */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var hasGsap = typeof window.gsap !== 'undefined';
  var body = document.body;

  /* ---------- GoHighLevel form endpoint ----------
     Replace with the GHL inbound webhook URL (Automations > Workflows > Inbound Webhook).
     Fields sent as JSON: name, email, phone, message, topic, page, submitted_at. */
  var GHL_WEBHOOK_URL = 'https://services.leadconnectorhq.com/hooks/mKzJ6Xo8E96vdYBZ5QLS/webhook-trigger/84dc6cef-062f-40ce-9d0e-5a930c22b486';

  /* ---------- anchor links ---------- */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href');
      if (id.length < 2) return;
      var el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      closeMenu();
      el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
      history.replaceState(null, '', id);
    });
  });

  /* ---------- nav: scrolled state, hide on scroll down, active link ---------- */
  var nav = document.getElementById('nav');
  var lastY = 0;
  function onScroll() {
    var y = window.scrollY || document.documentElement.scrollTop;
    nav.classList.toggle('is-scrolled', y > 24);
    if (y > 400 && y > lastY + 6 && !body.classList.contains('menu-open')) nav.classList.add('is-hidden');
    else if (y < lastY - 6 || y < 200) nav.classList.remove('is-hidden');
    lastY = y;
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var sections = Array.prototype.slice.call(document.querySelectorAll('main section[id]'));
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.nav-links a[href^="#"]'));
  if (sections.length && 'IntersectionObserver' in window) {
    var activeObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        navLinks.forEach(function (l) { l.classList.toggle('is-active', l.getAttribute('href') === '#' + en.target.id); });
      });
    }, { rootMargin: '-40% 0px -55% 0px' });
    sections.forEach(function (s) { activeObs.observe(s); });
  }

  /* ---------- mobile menu ---------- */
  var burger = document.getElementById('burger');
  var menu = document.getElementById('mobile-menu');
  function closeMenu() {
    if (!menu) return;
    menu.classList.remove('is-open');
    burger.classList.remove('is-open');
    burger.setAttribute('aria-expanded', 'false');
    body.classList.remove('menu-open');
  }
  if (burger && menu) {
    burger.addEventListener('click', function () {
      var open = !menu.classList.contains('is-open');
      menu.classList.toggle('is-open', open);
      burger.classList.toggle('is-open', open);
      burger.setAttribute('aria-expanded', String(open));
      body.classList.toggle('menu-open', open);
    });
  }

  /* ---------- reveal on scroll ---------- */
  var revealEls = document.querySelectorAll('[data-reveal]');
  if (reduce || !('IntersectionObserver' in window)) {
    revealEls.forEach(function (el) { el.classList.add('r-in'); });
  } else {
    var seen = 0;
    var revObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target;
        var delay = Math.min((seen++ % 6) * 70, 350);
        el.style.transitionDelay = delay + 'ms';
        el.classList.add('r-in');
        revObs.unobserve(el);
      });
      setTimeout(function () { seen = 0; }, 100);
    }, { threshold: 0.12, rootMargin: '0px 0px -8% 0px' });
    revealEls.forEach(function (el) { revObs.observe(el); });
  }

  /* ---------- hero: line reveal + photo parallax ---------- */
  if (hasGsap && !reduce) {
    var lines = document.querySelectorAll('.hero h1 .line > span');
    if (lines.length) {
      gsap.set(lines, { yPercent: 110 });
      gsap.to(lines, { yPercent: 0, duration: 1.3, ease: 'power4.out', stagger: 0.11, delay: 0.15 });
    }
    var heroImg = document.querySelector('.hero-photo img');
    if (heroImg && window.ScrollTrigger) {
      gsap.registerPlugin(ScrollTrigger);
      gsap.fromTo(heroImg, { yPercent: -6 }, {
        yPercent: 6, ease: 'none',
        scrollTrigger: { trigger: '.hero-photo', start: 'top bottom', end: 'bottom top', scrub: true }
      });
    }
  }

  /* ---------- whiteboard sketches: draw when scrolled into view ---------- */
  function prepDraw(svg) {
    var paths = svg.querySelectorAll('path.draw:not(.dash)');
    var texts = svg.querySelectorAll('text');
    paths.forEach(function (p) {
      var L = p.getTotalLength();
      p.style.strokeDasharray = L;
      p.style.strokeDashoffset = L;
    });
    texts.forEach(function (t) { t.style.opacity = 0; });
    return { paths: paths, texts: texts };
  }
  function playDraw(parts, totalMs) {
    var per = totalMs / Math.max(parts.paths.length, 1);
    parts.paths.forEach(function (p, i) {
      p.style.transition = 'stroke-dashoffset ' + Math.max(per * 1.6, 500) + 'ms cubic-bezier(.4,0,.2,1) ' + (i * per) + 'ms';
      p.style.strokeDashoffset = 0;
    });
    parts.texts.forEach(function (t, i) {
      t.style.transition = 'opacity .6s ease ' + (totalMs * 0.55 + i * 120) + 'ms';
      t.style.opacity = 1;
    });
  }
  var sketches = document.querySelectorAll('#cycle, #timeline');
  if (!reduce && 'IntersectionObserver' in window) {
    var drawObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        playDraw(en.target.__parts, en.target.id === 'cycle' ? 2600 : 1600);
        drawObs.unobserve(en.target);
      });
    }, { threshold: 0.35 });
    sketches.forEach(function (svg) { svg.__parts = prepDraw(svg); drawObs.observe(svg); });
  }

  /* ---------- counters ---------- */
  var counters = document.querySelectorAll('[data-count]');
  if (counters.length && !reduce && 'IntersectionObserver' in window) {
    var cObs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var el = en.target, end = parseInt(el.getAttribute('data-count'), 10), start = performance.now(), dur = 1400;
        (function tick(now) {
          var p = Math.min((now - start) / dur, 1), e = 1 - Math.pow(1 - p, 3);
          el.textContent = Math.round(end * e);
          if (p < 1) requestAnimationFrame(tick);
        })(start);
        cObs.unobserve(el);
      });
    }, { threshold: 0.6 });
    counters.forEach(function (c) { cObs.observe(c); });
  }

  /* ---------- magnetic primary buttons (desktop only) ---------- */
  if (!reduce && window.matchMedia('(hover:hover) and (pointer:fine)').matches) {
    document.querySelectorAll('.btn-primary, .btn-dark').forEach(function (btn) {
      btn.addEventListener('mousemove', function (e) {
        var r = btn.getBoundingClientRect();
        var x = (e.clientX - r.left - r.width / 2) * 0.18;
        var y = (e.clientY - r.top - r.height / 2) * 0.28;
        btn.style.transform = 'translate(' + x + 'px,' + y + 'px)';
      });
      btn.addEventListener('mouseleave', function () { btn.style.transform = ''; });
    });
  }

  /* ---------- contact modal ---------- */
  var modal = document.getElementById('contact-modal');
  var form = document.getElementById('contact-form');
  var lastFocus = null;
  function openModal(topic) {
    if (!modal) return;
    lastFocus = document.activeElement;
    closeMenu();
    if (topic) document.getElementById('f-topic').value = topic;
    modal.classList.add('is-open');
    modal.setAttribute('aria-hidden', 'false');
    body.style.overflow = 'hidden';
    if (hasGsap && !reduce) {
      gsap.fromTo('.modal-card', { y: 24, opacity: 0, scale: 0.98 }, { y: 0, opacity: 1, scale: 1, duration: 0.55, ease: 'power3.out' });
      gsap.fromTo('.modal-backdrop', { opacity: 0 }, { opacity: 1, duration: 0.4 });
    }
    setTimeout(function () { var f = document.getElementById('f-name'); if (f) f.focus(); }, 60);
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove('is-open');
    modal.setAttribute('aria-hidden', 'true');
    body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  document.querySelectorAll('.js-contact').forEach(function (b) {
    b.addEventListener('click', function () { openModal(b.getAttribute('data-topic') || 'Website inquiry'); });
  });
  if (modal) {
    modal.querySelectorAll('[data-close]').forEach(function (c) { c.addEventListener('click', closeModal); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && modal.classList.contains('is-open')) closeModal(); });
  }
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var ok = true;
      form.querySelectorAll('[required]').forEach(function (f) {
        var valid = f.checkValidity();
        f.style.borderColor = valid ? '' : '#c0392b';
        if (!valid) ok = false;
      });
      if (!ok) return;
      var data = {};
      new FormData(form).forEach(function (v, k) { data[k] = v; });
      data.page = location.href;
      data.submitted_at = new Date().toISOString();
      var btn = form.querySelector('[type=submit]');
      btn.disabled = true; btn.textContent = 'Sending…';
      var done = function () { form.classList.add('is-done'); };
      if (GHL_WEBHOOK_URL) {
        var fail = function () {
          btn.disabled = false; btn.textContent = 'Try again';
          var note = form.querySelector('.fine');
          if (note) note.innerHTML = 'That didn&#8217;t go through. Please email <a href="mailto:craig@eupraxisconsulting.com">craig@eupraxisconsulting.com</a> directly.';
        };
        fetch(GHL_WEBHOOK_URL, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
          .then(function (r) { if (r.ok) { done(); } else { fail(); } }).catch(fail);
      } else {
        // No endpoint configured yet: simulate success so the UX can be reviewed.
        console.info('[Eupraxis] Form data (GHL webhook not configured):', data);
        setTimeout(done, 500);
      }
    });
  }

  /* ---------- blog filters ---------- */
  var filters = document.querySelectorAll('.filters button');
  var entries = document.querySelectorAll('.entry');
  filters.forEach(function (b) {
    b.addEventListener('click', function () {
      filters.forEach(function (x) { x.classList.remove('is-active'); });
      b.classList.add('is-active');
      var cat = b.getAttribute('data-cat');
      entries.forEach(function (en) {
        en.classList.toggle('is-hidden', !(cat === 'all' || en.getAttribute('data-cat') === cat));
      });
      if (window.ScrollTrigger) ScrollTrigger.refresh();
    });
  });

  var yr = document.getElementById('year');
  if (yr) yr.textContent = new Date().getFullYear();
})();
