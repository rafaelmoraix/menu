/* 153 Filmes — interações */
(() => {
  // Contatos do botão "Vamos conversar" — preencha com os dados reais
  const CONTACT = {
    whatsapp: '', // ex.: '5511999999999' (somente números, com DDI e DDD)
    email: '',    // ex.: 'contato@153filmes.com.br'
  };

  const body = document.body;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  /* Entrada do hero */
  const start = () => requestAnimationFrame(() => body.classList.add('is-ready'));
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start);
  setTimeout(start, 1500);

  /* Header: fundo ao rolar, esconde ao descer */
  const header = document.querySelector('.header');
  let lastY = window.scrollY;
  const onScroll = () => {
    const y = window.scrollY;
    header.classList.toggle('is-scrolled', y > 30);
    header.classList.toggle('is-hidden', y > lastY && y > 400 && !body.classList.contains('menu-open'));
    lastY = y;
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* Menu mobile */
  const burger = document.querySelector('.burger');
  const closeMenu = () => { body.classList.remove('menu-open'); burger.setAttribute('aria-expanded', 'false'); burger.setAttribute('aria-label', 'Abrir menu'); };
  burger.addEventListener('click', () => {
    const open = body.classList.toggle('menu-open');
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  });
  document.querySelectorAll('.nav__link').forEach((link) => link.addEventListener('click', closeMenu));

  /* Link ativo na navegação */
  const navLinks = [...document.querySelectorAll('.nav__link')];
  const sectionObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      navLinks.forEach((l) => l.classList.toggle('is-active', l.getAttribute('href') === `#${entry.target.id}`));
    });
  }, { rootMargin: '-45% 0px -50% 0px' });
  document.querySelectorAll('main section[id]').forEach((s) => sectionObserver.observe(s));

  /* Revelação ao rolar + marca-texto */
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-in');
      revealObserver.unobserve(entry.target);
    });
  }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
  document.querySelectorAll('.reveal, .reveal-stagger, .process, [data-mark]').forEach((el) => revealObserver.observe(el));

  /* Contador (30+) */
  const countObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      const target = Number(el.dataset.count);
      const duration = reduceMotion ? 0 : 1600;
      const t0 = performance.now();
      const tick = (now) => {
        const t = duration ? Math.min((now - t0) / duration, 1) : 1;
        el.textContent = Math.round(target * (1 - Math.pow(1 - t, 4)));
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
      countObserver.unobserve(el);
    });
  }, { threshold: 0.6 });
  document.querySelectorAll('[data-count]').forEach((el) => countObserver.observe(el));

  /* Timecode do hero (24 fps) */
  const timecode = document.querySelector('[data-timecode]');
  if (timecode) {
    const t0 = performance.now();
    const pad = (n) => String(n).padStart(2, '0');
    const render = (now) => {
      const frames = Math.floor(((now - t0) / 1000) * 24);
      const s = Math.floor(frames / 24);
      timecode.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}:${pad(frames % 24)}`;
      requestAnimationFrame(render);
    };
    requestAnimationFrame(render);
  }

  /* Showreel do hero: pausa fora da tela, respeita movimento reduzido */
  const heroVideo = document.querySelector('.hero__video');
  if (heroVideo) {
    if (reduceMotion) heroVideo.pause();
    new IntersectionObserver(([e]) => {
      if (reduceMotion) return;
      if (e.isIntersecting) heroVideo.play().catch(() => {}); else heroVideo.pause();
    }).observe(heroVideo);
  }

  /* Trabalhos: prévia ao passar o mouse (ou ao aparecer na tela no celular) */
  const cards = [...document.querySelectorAll('.work__card')];
  const playPreview = (card) => {
    const v = card.querySelector('video');
    if (!v || reduceMotion) return;
    if (!v.src) v.src = v.dataset.preview;
    v.currentTime = 0;
    v.play().then(() => card.classList.add('is-previewing')).catch(() => {});
  };
  const stopPreview = (card) => {
    const v = card.querySelector('video');
    card.classList.remove('is-previewing');
    if (v) v.pause();
  };
  if (canHover) {
    cards.forEach((card) => {
      card.addEventListener('mouseenter', () => playPreview(card));
      card.addEventListener('mouseleave', () => stopPreview(card));
      card.addEventListener('focus', () => playPreview(card));
      card.addEventListener('blur', () => stopPreview(card));
    });
  } else {
    const previewObserver = new IntersectionObserver((entries) => {
      entries.forEach((e) => (e.isIntersecting ? playPreview(e.target) : stopPreview(e.target)));
    }, { threshold: 0.75 });
    cards.forEach((c) => previewObserver.observe(c));
  }

  /* Player */
  const player = document.querySelector('.player');
  const playerVideo = player.querySelector('.player__video');
  const openPlayer = (card) => {
    stopPreview(card);
    player.querySelector('.player__title').textContent = card.dataset.title;
    player.querySelector('.player__meta').textContent = card.dataset.meta || '';
    player.classList.toggle('is-vertical', card.hasAttribute('data-vertical'));
    playerVideo.src = card.dataset.video;
    playerVideo.poster = card.querySelector('img').getAttribute('src');
    if (typeof player.showModal === 'function') player.showModal(); else player.setAttribute('open', '');
    playerVideo.play().catch(() => {});
  };
  const closePlayer = () => {
    playerVideo.pause();
    playerVideo.removeAttribute('src');
    playerVideo.load();
    if (player.open) player.close();
  };
  cards.forEach((card) => card.addEventListener('click', () => openPlayer(card)));
  player.querySelector('.player__close').addEventListener('click', closePlayer);
  player.addEventListener('click', (e) => { if (e.target === player) closePlayer(); });
  player.addEventListener('close', () => { playerVideo.pause(); });

  /* Filtros (trabalhos e trajetória) */
  const setupFilter = (buttons, items, attr, renumber) => {
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const cat = btn.dataset[attr];
        buttons.forEach((b) => { const on = b === btn; b.classList.toggle('is-active', on); b.setAttribute('aria-selected', String(on)); });
        items.forEach((p) => p.classList.add('is-fading'));
        setTimeout(() => {
          let n = 0;
          items.forEach((p) => {
            const show = cat === 'all' || p.dataset.cat === cat;
            p.classList.toggle('is-hidden', !show);
            if (show && renumber) p.querySelector('.project__num').textContent = String(++n).padStart(2, '0');
          });
          requestAnimationFrame(() => items.forEach((p) => p.classList.remove('is-fading')));
        }, reduceMotion ? 0 : 250);
      });
    });
  };
  setupFilter([...document.querySelectorAll('[data-filter]')], [...document.querySelectorAll('.work')], 'filter', false);
  const projects = [...document.querySelectorAll('.project')];
  setupFilter([...document.querySelectorAll('[data-tfilter]')], projects, 'tfilter', true);

  /* Trajetória: acordeão */
  projects.forEach((project) => {
    const head = project.querySelector('.project__head');
    head.addEventListener('click', () => {
      const open = !project.classList.contains('is-open');
      projects.forEach((p) => { p.classList.remove('is-open'); p.querySelector('.project__head').setAttribute('aria-expanded', 'false'); });
      project.classList.toggle('is-open', open);
      head.setAttribute('aria-expanded', String(open));
    });
  });

  /* Botões de contato */
  document.querySelectorAll('[data-contact]').forEach((btn) => {
    const type = btn.dataset.contact;
    if (type === 'whatsapp' && CONTACT.whatsapp) {
      btn.href = `https://wa.me/${CONTACT.whatsapp}?text=${encodeURIComponent('Olá! Vim pelo site da 153 Filmes e gostaria de conversar sobre um projeto.')}`;
      btn.target = '_blank';
      btn.rel = 'noopener';
    } else if (type === 'email' && CONTACT.email) {
      btn.href = `mailto:${CONTACT.email}?subject=${encodeURIComponent('Projeto audiovisual — via site')}`;
    } else {
      btn.href = '#contato'; // contato ainda não configurado em CONTACT
    }
  });

  /* Ano no rodapé */
  document.querySelectorAll('[data-year]').forEach((el) => (el.textContent = new Date().getFullYear()));
})();
