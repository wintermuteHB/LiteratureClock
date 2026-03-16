(() => {
  'use strict';

  let allQuotes = [];
  let quotesByTime = {};
  let sortedTimes = [];
  let currentTime = '';
  let browseTime = null; // null = live mode, string = browsing
  let idleTimer = null;
  let navHintTimer = null;

  // --- Format time as HH:MM ---
  function formatTime(date) {
    return String(date.getHours()).padStart(2, '0') + ':' +
           String(date.getMinutes()).padStart(2, '0');
  }

  // --- Index quotes by time ---
  function indexQuotes(quotes) {
    const map = {};
    quotes.forEach(q => {
      if (!map[q.time]) map[q.time] = [];
      map[q.time].push(q);
    });
    return map;
  }

  // --- Pick a random quote for a time ---
  function pickQuote(time) {
    const candidates = quotesByTime[time];
    if (!candidates || candidates.length === 0) return null;
    return candidates[Math.floor(Math.random() * candidates.length)];
  }

  // --- Find nearest time if exact match missing ---
  function findNearest(time) {
    if (quotesByTime[time]) return time;

    const [h, m] = time.split(':').map(Number);
    const totalMin = h * 60 + m;

    let bestTime = null;
    let bestDist = Infinity;

    for (const t of sortedTimes) {
      const [th, tm] = t.split(':').map(Number);
      const tMin = th * 60 + tm;
      const dist = Math.abs(tMin - totalMin);
      if (dist < bestDist) {
        bestDist = dist;
        bestTime = t;
      }
    }
    return bestTime;
  }

  // --- Highlight time expression in quote text ---
  function highlightTime(text, time) {
    const [h, m] = time.split(':').map(Number);
    
    // Build patterns to match
    const patterns = [];
    
    // Digital formats: "10:30", "10.30"
    const hh = String(h).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    const h12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
    
    patterns.push(hh + ':' + mm);
    patterns.push(hh + '.' + mm);
    patterns.push(h + ':' + mm);
    patterns.push(h12 + ':' + mm);
    if (m === 0) {
      patterns.push(h12 + " o'clock");
      patterns.push(h12 + " o'clock");
      patterns.push(h12 + ' oclock');
    }
    
    // AM/PM variants
    const ampm = h < 12 ? 'a\\.?m\\.?' : 'p\\.?m\\.?';
    patterns.push(h12 + ':' + mm + '\\s*' + ampm);
    if (m === 0) {
      patterns.push(h12 + '\\s*' + ampm);
    }
    
    // Word-based times
    const wordNums = [
      'twelve', 'one', 'two', 'three', 'four', 'five', 'six',
      'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve'
    ];
    const hourWord = wordNums[h12];
    const minuteWords = {
      0: null, 15: 'fifteen', 30: 'thirty', 45: 'forty-five',
      10: 'ten', 20: 'twenty', 5: 'five', 25: 'twenty-five',
      35: 'thirty-five', 40: 'forty', 50: 'fifty', 55: 'fifty-five'
    };
    
    if (m === 0) {
      patterns.push(hourWord + " o'clock");
      patterns.push(hourWord + ' o.clock');
    }
    if (m === 30) {
      patterns.push('half\\s+past\\s+' + hourWord);
    }
    if (m === 15) {
      patterns.push('(?:a\\s+)?quarter\\s+past\\s+' + hourWord);
    }
    if (m === 45) {
      const nextHour = wordNums[(h12 % 12) + 1];
      patterns.push('(?:a\\s+)?quarter\\s+to\\s+' + nextHour);
    }
    
    // "noon", "midnight"
    if (h === 12 && m === 0) patterns.push('noon', 'midday');
    if (h === 0 && m === 0) patterns.push('midnight');
    
    // Try each pattern
    for (const pat of patterns) {
      const regex = new RegExp('(' + pat + ')', 'gi');
      if (regex.test(text)) {
        return text.replace(regex, '<span class="time-highlight">$1</span>');
      }
    }
    
    // No match found — return plain text
    return null;
  }

  // --- Display a quote with fade transition ---
  function displayQuote(quote) {
    const container = document.getElementById('quote-container');
    const quoteEl = document.getElementById('quote');
    const authorEl = document.getElementById('author');
    const titleEl = document.getElementById('title');
    const timeEl = document.getElementById('time-display');

    // Fade out
    container.classList.remove('visible');

    setTimeout(() => {
      if (quote) {
        let text = quote.quote;
        if (text.length > 500) {
          text = text.substring(0, 497) + '…';
        }

        // Try to highlight time in quote
        const displayTime = browseTime || currentTime;
        const highlighted = highlightTime(text, displayTime);
        
        if (highlighted) {
          quoteEl.innerHTML = highlighted;
        } else {
          quoteEl.textContent = text;
        }

        quoteEl.classList.toggle('long', text.length > 300);
        authorEl.textContent = quote.author || '';
        titleEl.textContent = quote.title || '';
      } else {
        quoteEl.innerHTML = '';
        authorEl.textContent = '';
        titleEl.textContent = '';
      }

      // Show time with browse indicator
      if (browseTime) {
        timeEl.textContent = browseTime + '  ◆';
        timeEl.style.color = 'var(--accent)';
      } else {
        timeEl.textContent = currentTime;
        timeEl.style.color = '';
      }

      // Fade in
      container.classList.add('visible');
    }, 600);
  }

  // --- Show quote for a specific time ---
  function showTimeQuote(time) {
    const matchTime = findNearest(time);
    const quote = pickQuote(matchTime);
    displayQuote(quote);
  }

  // --- Check time and update (live mode only) ---
  function tick() {
    const now = new Date();
    const time = formatTime(now);

    if (time !== currentTime) {
      currentTime = time;
      if (!browseTime) {
        showTimeQuote(time);
      }
    }
  }

  // --- Navigate to adjacent time slot ---
  function navigateTime(direction) {
    const active = browseTime || currentTime;
    const idx = sortedTimes.indexOf(findNearest(active));
    if (idx === -1) return;

    let newIdx = idx + direction;
    if (newIdx < 0) newIdx = sortedTimes.length - 1;
    if (newIdx >= sortedTimes.length) newIdx = 0;

    browseTime = sortedTimes[newIdx];
    showTimeQuote(browseTime);
    showNavHint();
  }

  // --- Return to live mode ---
  function goLive() {
    browseTime = null;
    currentTime = '';  // force refresh
    tick();
  }

  // --- Show keyboard nav hint briefly ---
  function showNavHint() {
    const hint = document.getElementById('nav-hint');
    if (!hint) return;
    hint.classList.add('visible');
    clearTimeout(navHintTimer);
    navHintTimer = setTimeout(() => {
      hint.classList.remove('visible');
    }, 3000);
  }

  // --- Idle cursor hide ---
  function resetIdle() {
    document.body.classList.remove('idle');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => {
      document.body.classList.add('idle');
    }, 5000);
  }

  // --- Click for next quote at same time ---
  function nextQuote() {
    const time = browseTime || currentTime;
    const matchTime = findNearest(time);
    const candidates = quotesByTime[matchTime];
    if (candidates && candidates.length > 1) {
      showTimeQuote(matchTime);
    }
  }

  // --- Keyboard handler ---
  function onKeyDown(e) {
    switch (e.key) {
      case 'ArrowLeft':
        e.preventDefault();
        navigateTime(-1);
        break;
      case 'ArrowRight':
        e.preventDefault();
        navigateTime(1);
        break;
      case ' ':
        e.preventDefault();
        nextQuote();
        break;
      case 'Escape':
        if (browseTime) {
          e.preventDefault();
          goLive();
        } else if (document.fullscreenElement) {
          document.exitFullscreen();
        }
        break;
      case 'f':
      case 'F':
        e.preventDefault();
        if (!document.fullscreenElement) {
          document.documentElement.requestFullscreen().catch(() => {});
        } else {
          document.exitFullscreen();
        }
        break;
    }
  }

  // --- Theme Toggle ---
  function initTheme() {
    const saved = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    applyTheme(theme);
  }

  function applyTheme(theme) {
    if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    localStorage.setItem('theme', theme);
    updateToggleLabel(theme);
  }

  function updateToggleLabel(theme) {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.textContent = theme === 'dark' ? '☀ Light' : '● Dark';
  }

  function toggleTheme() {
    const current = localStorage.getItem('theme') || 'dark';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  // --- Init ---
  async function init() {
    try {
      const res = await fetch('data/quotes.json');
      allQuotes = await res.json();
    } catch (e) {
      console.error('Failed to load quotes:', e);
      return;
    }

    quotesByTime = indexQuotes(allQuotes);
    sortedTimes = Object.keys(quotesByTime).sort();

    // Initial display
    currentTime = '';
    tick();

    // Check every second
    setInterval(tick, 1000);

    // Click/tap for next quote
    document.getElementById('clock').addEventListener('click', nextQuote);

    // Keyboard navigation
    document.addEventListener('keydown', onKeyDown);

    // Idle cursor
    document.addEventListener('mousemove', resetIdle);
    document.addEventListener('touchstart', resetIdle);
    resetIdle();

    // Fullscreen on double-click
    document.addEventListener('dblclick', () => {
      if (!document.fullscreenElement) {
        document.documentElement.requestFullscreen().catch(() => {});
      } else {
        document.exitFullscreen();
      }
    });

    // Theme toggle
    initTheme();
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

    // Show nav hint on first load for 4 seconds
    setTimeout(() => showNavHint(), 2000);
  }

  // Register Service Worker for offline support
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('./sw.js').catch(() => {});
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
