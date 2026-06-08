(function () {
  const root = document.getElementById('globalAi');
  if (!root || root.dataset.initialized === 'true') return;
  root.dataset.initialized = 'true';

  const drawer = document.getElementById('globalAiDrawer');
  const frame = document.getElementById('globalAiFrame');
  const frameFallback = document.getElementById('globalAiFrameFallback');
  const resizer = document.getElementById('globalAiResizer');
  const backdrop = document.getElementById('globalAiBackdrop');
  const modal = document.getElementById('globalAiSettingsModal');
  const bubble = root.querySelector('[data-global-ai-toggle]');
  const avatarImg = root.querySelector('[data-global-ai-avatar]');
  const avatarOptionsWrap = modal.querySelector('[data-global-ai-avatar-options]');
  const transparencyInput = modal.querySelector('[data-global-ai-input="transparency"]');
  const transparencyLabel = modal.querySelector('[data-global-ai-transparency-label]');
  const animationsInput = modal.querySelector('[data-global-ai-input="animations_enabled"]');

  const endpoint = root.dataset.preferencesUrl;
  const chatPath = root.dataset.chatUrl;
  const clearUrl = root.dataset.clearUrl;
  const sizeMap = { small: 56, medium: 68, large: 82, xlarge: 96 };
  const borderMap = {
    mentore_blue: '#2196c9',
    green: '#10b981',
    purple: '#7c3aed',
    gray: '#94a3b8',
    black: '#111827',
    none: 'transparent'
  };
  const shadowMap = {
    none: 'none',
    soft: '0 8px 22px rgba(13,45,66,.12)',
    medium: '0 14px 34px rgba(13,45,66,.18)',
    intense: '0 20px 52px rgba(13,45,66,.28)'
  };

  let state = null;
  let saveTimer = null;
  let completeTimer = null;
  let frameReady = false;
  let frameLoadTimer = null;
  let resizeSaveTimer = null;
  let isResizing = false;

  function drawerLimits() {
    const maxWidth = Math.floor(window.innerWidth * 0.5);
    const minWidth = window.innerWidth <= 900 ? 320 : 360;
    return {
      min: Math.min(minWidth, maxWidth),
      max: Math.max(minWidth, maxWidth)
    };
  }

  function clampDrawerWidth(width) {
    const limits = drawerLimits();
    return Math.max(limits.min, Math.min(limits.max, Math.round(width)));
  }

  function applyDrawerWidth(width) {
    const nextWidth = clampDrawerWidth(width);
    document.documentElement.style.setProperty('--global-ai-drawer-width', nextWidth + 'px');
    if (state && state.preference) {
      state.preference.drawer_width = nextWidth;
    }
    return nextWidth;
  }

  function saveDrawerWidth(width) {
    window.clearTimeout(resizeSaveTimer);
    resizeSaveTimer = window.setTimeout(function () {
      scheduleSave({ drawer_width: clampDrawerWidth(width) }, 0);
    }, 220);
  }

  function csrfToken() {
    const match = document.cookie.match(/csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : root.dataset.csrfToken;
  }

  async function requestPreferences(payload) {
    const options = payload ? {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken()
      },
      body: JSON.stringify(payload)
    } : { credentials: 'same-origin' };
    const response = await fetch(endpoint, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'No se pudo guardar la configuracion');
    return data;
  }

  function scheduleSave(patch, delay) {
    if (!state) {
      requestPreferences(patch)
        .then(function (data) {
          state = data;
          applyPreference();
        })
        .catch(function (err) {
          console.warn(err);
        });
      return;
    }
    state.preference = Object.assign({}, state.preference, patch);
    applyPreference();
    window.clearTimeout(saveTimer);
    saveTimer = window.setTimeout(async function () {
      try {
        state = await requestPreferences(state.preference);
        applyPreference();
      } catch (err) {
        console.warn(err);
      }
    }, delay == null ? 180 : delay);
  }

  function applyPreference() {
    if (!state) return;
    const pref = state.preference;
    const avatar = state.avatar_options.find(item => item.id === pref.avatar) || state.avatar_options[0];
    const size = sizeMap[pref.size] || sizeMap.medium;
    const transparency = Math.max(0, Math.min(100, Number(pref.transparency || 0)));

    root.classList.toggle('is-hidden', !pref.is_visible);
    root.classList.toggle('is-left', pref.position === 'bottom_left');
    root.classList.toggle('no-animations', !pref.animations_enabled);
    root.classList.remove('avatar-avatar_a', 'avatar-avatar_b');
    root.classList.add('avatar-' + pref.avatar);
    root.classList.remove('effect-halo', 'effect-glow', 'effect-pulse', 'effect-none');
    root.classList.add('effect-' + pref.activity_effect);
    root.style.setProperty('--gai-size', size + 'px');
    root.style.setProperty('--gai-opacity', String(1 - transparency / 100));
    root.style.setProperty('--gai-border', borderMap[pref.border_color] || borderMap.mentore_blue);
    root.style.setProperty('--gai-shadow', shadowMap[pref.shadow] || shadowMap.medium);
    applyDrawerWidth(pref.drawer_width || 520);

    avatarImg.classList.remove('has-error');
    avatarImg.src = avatar.url;
    avatarImg.alt = '';

    bubble.setAttribute('aria-expanded', drawer.classList.contains('is-open') ? 'true' : 'false');
    renderControls();
  }

  function renderControls() {
    const pref = state.preference;
    avatarOptionsWrap.innerHTML = state.avatar_options.map(function (avatar) {
      return '<button type="button" class="global-ai-avatar-option ' + (avatar.id === pref.avatar ? 'is-active' : '') + '" data-avatar="' + avatar.id + '">' +
        '<img src="' + avatar.url + '" alt="" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'inline-flex\';">' +
        '<span class="global-ai-avatar-preview-fallback" style="display:none;"><i class="' + avatar.fallback_icon + '"></i></span>' +
        '<span>' + avatar.label + '</span>' +
      '</button>';
    }).join('');

    modal.querySelectorAll('[data-global-ai-field]').forEach(function (group) {
      const field = group.dataset.globalAiField;
      group.querySelectorAll('[data-value]').forEach(function (btn) {
        btn.classList.toggle('is-active', btn.dataset.value === String(pref[field]));
      });
    });

    transparencyInput.value = pref.transparency;
    transparencyLabel.textContent = pref.transparency + '%';
    animationsInput.checked = !!pref.animations_enabled;
  }

  function buildChatUrl() {
    const url = new URL(chatPath, window.location.origin);
    url.searchParams.set('embed', 'global_assistant');
    return url.toString();
  }

  function ensureFrame() {
    const target = buildChatUrl();
    const current = frame.getAttribute('src') ? new URL(frame.getAttribute('src'), window.location.origin).toString() : '';
    if (current !== target) {
      frameReady = false;
      frameFallback.hidden = true;
      frame.src = target;
    }
    window.clearTimeout(frameLoadTimer);
    frameLoadTimer = window.setTimeout(function () {
      if (!frameReady) frameFallback.hidden = false;
    }, 4500);
  }

  function openDrawer() {
    ensureFrame();
    drawer.classList.add('is-open');
    document.body.classList.add('global-ai-drawer-open');
    drawer.setAttribute('aria-hidden', 'false');
    backdrop.hidden = true;
    bubble.setAttribute('aria-expanded', 'true');
    sessionStorage.setItem('mentoreGlobalAiDrawerOpen', '1');
    setTimeout(function () {
      drawer.querySelector('[data-global-ai-close]').focus();
    }, 50);
  }

  function closeDrawer() {
    drawer.classList.remove('is-open');
    document.body.classList.remove('global-ai-drawer-open', 'global-ai-resizing');
    drawer.setAttribute('aria-hidden', 'true');
    backdrop.hidden = true;
    bubble.setAttribute('aria-expanded', 'false');
    sessionStorage.removeItem('mentoreGlobalAiDrawerOpen');
    bubble.focus();
  }

  function openModal() {
    modal.hidden = false;
    setTimeout(function () {
      modal.querySelector('[data-global-ai-settings-close]').focus();
    }, 30);
  }

  function closeModal() {
    modal.hidden = true;
    bubble.focus();
  }

  function setAiActivity(status) {
    window.clearTimeout(completeTimer);
    if (status === 'working') {
      root.classList.add('is-working');
      root.classList.remove('is-complete');
      return;
    }
    if (status === 'complete') {
      root.classList.remove('is-working');
      root.classList.add('is-complete');
      completeTimer = window.setTimeout(function () {
        root.classList.remove('is-complete');
      }, 800);
      return;
    }
    root.classList.remove('is-working', 'is-complete');
  }

  avatarImg.addEventListener('error', function () {
    avatarImg.classList.add('has-error');
  });

  bubble.addEventListener('click', function () {
    drawer.classList.contains('is-open') ? closeDrawer() : openDrawer();
  });

  root.querySelector('[data-global-ai-settings]').addEventListener('click', openModal);
  root.querySelector('[data-global-ai-hide]').addEventListener('click', function () {
    scheduleSave({ is_visible: false }, 0);
  });

  root.ownerDocument.querySelector('[data-global-ai-clear]').addEventListener('click', async function () {
    if (!window.confirm('¿Limpiar el historial del chat de IA?')) return;
    try {
      await fetch(clearUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': csrfToken() }
      });
      frameReady = false;
      frameFallback.hidden = true;
      frame.src = buildChatUrl();
    } catch (err) {
      console.warn(err);
    }
  });

  document.querySelectorAll('[data-global-ai-close]').forEach(function (btn) {
    btn.addEventListener('click', closeDrawer);
  });

  modal.querySelector('[data-global-ai-settings-close]').addEventListener('click', closeModal);
  modal.addEventListener('click', function (event) {
    if (event.target === modal) closeModal();
  });

  modal.addEventListener('click', function (event) {
    const avatarButton = event.target.closest('[data-avatar]');
    if (avatarButton) {
      scheduleSave({ avatar: avatarButton.dataset.avatar });
      return;
    }
    const valueButton = event.target.closest('[data-value]');
    if (!valueButton) return;
    const group = valueButton.closest('[data-global-ai-field]');
    if (!group) return;
    scheduleSave({ [group.dataset.globalAiField]: valueButton.dataset.value });
  });

  transparencyInput.addEventListener('input', function () {
    transparencyLabel.textContent = transparencyInput.value + '%';
    scheduleSave({ transparency: Number(transparencyInput.value) }, 240);
  });

  animationsInput.addEventListener('change', function () {
    scheduleSave({ animations_enabled: animationsInput.checked });
  });

  function beginResize(event) {
    if (window.innerWidth <= 760 || event.button !== 0) return;
    event.preventDefault();
    isResizing = true;
    document.body.classList.add('global-ai-resizing');
    resizer.setPointerCapture(event.pointerId);
  }

  function moveResize(event) {
    if (!isResizing) return;
    const width = window.innerWidth - event.clientX;
    applyDrawerWidth(width);
  }

  function endResize(event) {
    if (!isResizing) return;
    isResizing = false;
    document.body.classList.remove('global-ai-resizing');
    try { resizer.releasePointerCapture(event.pointerId); } catch (err) { /* ignore */ }
    const current = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--global-ai-drawer-width'), 10) || 520;
    saveDrawerWidth(current);
  }

  if (resizer) {
    resizer.addEventListener('pointerdown', beginResize);
    resizer.addEventListener('pointermove', moveResize);
    resizer.addEventListener('pointerup', endResize);
    resizer.addEventListener('pointercancel', endResize);
    resizer.addEventListener('keydown', function (event) {
      if (window.innerWidth <= 760 || (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight')) return;
      event.preventDefault();
      const current = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--global-ai-drawer-width'), 10) || 520;
      const delta = event.key === 'ArrowLeft' ? 24 : -24;
      const next = applyDrawerWidth(current + delta);
      saveDrawerWidth(next);
    });
  }

  window.addEventListener('resize', function () {
    if (!state || !state.preference) return;
    applyDrawerWidth(state.preference.drawer_width || 520);
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    if (!modal.hidden) {
      closeModal();
    } else if (drawer.classList.contains('is-open')) {
      closeDrawer();
    }
  });

  window.addEventListener('message', function (event) {
    if (event.origin !== window.location.origin) return;
    if (!event.data || event.data.type !== 'mentore-ai-state') return;
    if (event.data.state === 'ready') {
      frameReady = true;
      frameFallback.hidden = true;
      return;
    }
    setAiActivity(event.data.state);
  });

  document.addEventListener('mentoreGlobalAssistantVisibility', function (event) {
    scheduleSave({ is_visible: !!event.detail.visible }, 0);
  });

  requestPreferences()
    .then(function (data) {
      state = data;
      applyPreference();
      if (sessionStorage.getItem('mentoreGlobalAiDrawerOpen') === '1') {
        openDrawer();
      }
    })
    .catch(function (err) {
      console.warn(err);
    });
})();
