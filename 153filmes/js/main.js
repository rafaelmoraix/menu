/* 153 Filmes — interações */
(() => {
  // Contatos do botão "Vamos conversar" — preencha com os dados reais
  const CONTACT = {
    whatsapp: '', // ex.: '5511999999999' (somente números, com DDI e DDD)
    email: '',    // ex.: 'contato@153filmes.com.br'
  };

  const body = document.body;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* Intro */
  const finishIntro = () => {
    body.classList.remove('is-loading');
    requestAnimationFrame(() => body.classList.add('is-ready'));
  };
  window.addEventListener('load', () => setTimeout(finishIntro, reduceMotion ? 0 : 1500));
  setTimeout(finishIntro, 4000); // fallback caso alguma fonte demore

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
  burger.addEventListener('click', () => {
    const open = body.classList.toggle('menu-open');
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Fechar menu' : 'Abrir menu');
  });
  document.querySelectorAll('.nav__link').forEach((link) =>
    link.addEventListener('click', () => {
      body.classList.remove('menu-open');
      burger.setAttribute('aria-expanded', 'false');
    })
  );

  /* Link ativo na navegação */
  const navLinks = [...document.querySelectorAll('.nav__link')];
  const sectionObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((l) => l.classList.toggle('is-active', l.getAttribute('href') === `#${entry.target.id}`));
      });
    },
    { rootMargin: '-45% 0px -50% 0px' }
  );
  document.querySelectorAll('main section[id]').forEach((s) => sectionObserver.observe(s));

  /* Revelação ao rolar */
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-in');
        revealObserver.unobserve(entry.target);
      });
    },
    { rootMargin: '0px 0px -8% 0px', threshold: 0.08 }
  );
  document.querySelectorAll('.reveal, .reveal-stagger, .process__step').forEach((el) => revealObserver.observe(el));

  /* Contador (30+) */
  const countObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        const el = entry.target;
        const target = Number(el.dataset.count);
        const duration = reduceMotion ? 0 : 1600;
        const start = performance.now();
        const tick = (now) => {
          const t = duration ? Math.min((now - start) / duration, 1) : 1;
          el.textContent = Math.round(target * (1 - Math.pow(1 - t, 4)));
          if (t < 1) requestAnimationFrame(tick);
        };
        requestAnimationFrame(tick);
        countObserver.unobserve(el);
      });
    },
    { threshold: 0.6 }
  );
  document.querySelectorAll('[data-count]').forEach((el) => countObserver.observe(el));

  /* Timecode do quadro do hero (24 fps) */
  const timecode = document.querySelector('[data-timecode]');
  if (timecode) {
    const t0 = performance.now();
    const pad = (n) => String(n).padStart(2, '0');
    const renderTimecode = (now) => {
      const totalFrames = Math.floor(((now - t0) / 1000) * 24);
      const f = totalFrames % 24;
      const s = Math.floor(totalFrames / 24);
      timecode.textContent = `${pad(Math.floor(s / 3600))}:${pad(Math.floor(s / 60) % 60)}:${pad(s % 60)}:${pad(f)}`;
      requestAnimationFrame(renderTimecode);
    };
    requestAnimationFrame(renderTimecode);
  }

  /* Inclinação 3D do quadro + brilho que segue o cursor */
  const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  if (finePointer && !reduceMotion) {
    const frame = document.querySelector('[data-tilt]');
    if (frame) {
      frame.addEventListener('mousemove', (e) => {
        const r = frame.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width - 0.5;
        const y = (e.clientY - r.top) / r.height - 0.5;
        frame.style.transform = `rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`;
      });
      frame.addEventListener('mouseleave', () => (frame.style.transform = ''));
    }

    const glow = document.querySelector('.cursor-glow');
    let gx = -999, gy = -999, cx = gx, cy = gy;
    window.addEventListener('mousemove', (e) => { gx = e.clientX; gy = e.clientY; }, { passive: true });
    const follow = () => {
      cx += (gx - cx) * 0.12;
      cy += (gy - cy) * 0.12;
      glow.style.transform = `translate3d(${cx}px, ${cy}px, 0)`;
      requestAnimationFrame(follow);
    };
    follow();
  }

  /* Destaque que segue o mouse nos cards de parceiros */
  document.querySelectorAll('.partner').forEach((card) => {
    card.addEventListener('mousemove', (e) => {
      const r = card.getBoundingClientRect();
      card.style.setProperty('--mx', `${e.clientX - r.left}px`);
      card.style.setProperty('--my', `${e.clientY - r.top}px`);
    });
  });

  /* Projetos: acordeão */
  const projects = [...document.querySelectorAll('.project')];
  projects.forEach((project) => {
    const head = project.querySelector('.project__head');
    head.addEventListener('click', () => {
      const open = !project.classList.contains('is-open');
      projects.forEach((p) => {
        p.classList.remove('is-open');
        p.querySelector('.project__head').setAttribute('aria-expanded', 'false');
      });
      project.classList.toggle('is-open', open);
      head.setAttribute('aria-expanded', String(open));
    });
  });

  /* Projetos: filtros */
  const filters = [...document.querySelectorAll('.filter')];
  filters.forEach((btn) => {
    btn.addEventListener('click', () => {
      const cat = btn.dataset.filter;
      filters.forEach((b) => {
        const active = b === btn;
        b.classList.toggle('is-active', active);
        b.setAttribute('aria-selected', String(active));
      });
      projects.forEach((p) => p.classList.add('is-fading'));
      setTimeout(() => {
        let n = 0;
        projects.forEach((p) => {
          const show = cat === 'all' || p.dataset.cat === cat;
          p.classList.toggle('is-hidden', !show);
          if (show) p.querySelector('.project__num').textContent = String(++n).padStart(2, '0');
        });
        requestAnimationFrame(() => projects.forEach((p) => p.classList.remove('is-fading')));
      }, reduceMotion ? 0 : 250);
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
