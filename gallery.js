(function(){
  var grid = document.getElementById('shotGrid');
  var box  = document.getElementById('lightbox');
  if (!grid || !box) return;

  var items = Array.prototype.slice.call(grid.querySelectorAll('.shot-item'));
  if (!items.length) return;

  /* ---------- Sprache ---------------------------------------------------- */
  /* Die Sprache steht in der Adresse (/ bzw. /en/) und aendert sich zur
     Laufzeit nicht mehr — einmal ablesen genuegt. */
  var EN = document.documentElement.lang === 'en';
  function t(de, en){ return EN ? en : de; }

  /* ---------- Lightbox --------------------------------------------------- */
  var img = document.getElementById('lbImg');
  var capExif  = document.getElementById('lbExif');
  var capCount = document.getElementById('lbCount');
  var bClose = document.getElementById('lbClose');
  var bPrev  = document.getElementById('lbPrev');
  var bNext  = document.getElementById('lbNext');
  var visible = [];      // alle Treffer des Filters, ueber alle Seiten — die Lightbox blaettert durch diese
  var idx = 0;
  var opener = null;

  function show(i){
    if (!visible.length) return;
    idx = (i + visible.length) % visible.length;
    var btn = visible[idx].querySelector('.shot');
    img.src = btn.dataset.large;
    // Die Beschreibung bleibt im alt-Text — sichtbar steht sie im Raster unter
    // dem Bild. Die Unterschrift hat zwei Zeilen: oben Kamera und Aufnahme-
    // daten, darunter die Position im Durchlauf.
    img.alt = btn.dataset.alt || '';
    var zeile = [];
    if (btn.dataset.cam)  zeile.push(btn.dataset.cam);
    if (btn.dataset.exif) zeile.push(btn.dataset.exif);
    capExif.textContent  = zeile.join('  ·  ');
    capCount.textContent = (idx + 1) + '/' + visible.length;
  }
  function open(item){
    var i = visible.indexOf(item);
    if (i < 0) return;
    opener = document.activeElement;
    box.hidden = false;
    document.body.classList.add('lb-open');
    show(i);
    bClose.focus();
  }
  function close(){
    box.hidden = true;
    document.body.classList.remove('lb-open');
    img.src = '';
    // In der Lightbox kann man ueber die Seitengrenze hinaus blaettern. Dann
    // beim Schliessen auf die Seite des zuletzt gezeigten Bildes wechseln,
    // sonst laege der Fokus auf einem ausgeblendeten Bild.
    var cur = visible[idx];
    var p = cur ? Math.floor(idx / PER_PAGE) + 1 : page;
    if (p !== page) {
      setPage(p, true);
      cur.querySelector('.shot').focus();
      cur.scrollIntoView({ block: 'center' });
    } else if (opener) opener.focus();
  }

  grid.addEventListener('click', function(e){
    var btn = e.target.closest('.shot');
    if (btn) open(btn.closest('.shot-item'));
  });
  bClose.addEventListener('click', close);
  bPrev.addEventListener('click', function(){ show(idx - 1); });
  bNext.addEventListener('click', function(){ show(idx + 1); });
  box.addEventListener('click', function(e){ if (e.target === box) close(); });

  document.addEventListener('keydown', function(e){
    if (box.hidden) return;
    if (e.key === 'Escape') close();
    else if (e.key === 'ArrowLeft')  show(idx - 1);
    else if (e.key === 'ArrowRight') show(idx + 1);
    else if (e.key === 'Tab'){
      var f = [bClose, bPrev, bNext];
      var i = f.indexOf(document.activeElement);
      e.preventDefault();
      f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus();
    }
  });

  /* ---------- Filter ----------------------------------------------------- */
  var form   = document.getElementById('filters');
  var qEl    = document.getElementById('fSearch');
  var yearEl = document.getElementById('fYear');
  var placeEl= document.getElementById('fPlace');
  var sortEl = document.getElementById('fSort');
  var tagsEl = document.getElementById('fTags');
  var countEl= document.getElementById('fCount');
  var emptyEl= document.getElementById('fEmpty');
  var resetEl= document.getElementById('fReset');

  var pagerEl= document.getElementById('fPager');

  pagerEl.setAttribute('aria-label', t('Seiten', 'Pages'));

  var activeTags = [];

  /* ---------- Seiten ----------------------------------------------------- */
  /* Nur die Bilder der aktuellen Seite sind sichtbar. Die Vorschaubilder
     haben loading="lazy" — ausgeblendete laedt der Browser gar nicht erst.
     Die Seite steht in der Adresse (#seite-2 bzw. #page-2), damit Zurueck-
     Taste, Neuladen und geteilte Links funktionieren. */
  var PER_PAGE = 27;
  var HASH = EN ? 'page-' : 'seite-';
  var page = 1;

  function pageFromHash(){
    var m = location.hash.match(/^#(?:seite|page)-(\d+)$/);
    return m ? parseInt(m[1], 10) : 1;
  }

  // Auswahllisten aus den vorhandenen Bildern aufbauen
  var years  = [], places = [], tagIds = [], tagLabels = {};
  items.forEach(function(it){
    var y = it.dataset.year;
    if (y && years.indexOf(y) < 0) years.push(y);
    var p = it.dataset.place;
    if (p && places.indexOf(p) < 0) places.push(p);
    (it.dataset.tags || '').split(/\s+/).filter(Boolean).forEach(function(id, n){
      if (tagIds.indexOf(id) < 0) tagIds.push(id);
    });
    it.querySelectorAll('.shot-tag').forEach(function(chip, n){
      var id = (it.dataset.tags || '').split(/\s+/).filter(Boolean)[n];
      if (id && !tagLabels[id]) tagLabels[id] = chip.textContent.trim() || id;
    });
  });
  years.sort().reverse();
  places.sort(function(a, b){ return a.localeCompare(b, 'de'); });
  tagIds.sort(function(a, b){
    return (tagLabels[a] || a).localeCompare(tagLabels[b] || b, 'de');
  });

  var undated = items.some(function(it){ return !it.dataset.date; });
  var noPlace = items.some(function(it){ return !it.dataset.place; });

  function fillSelects(){
    var y = yearEl.value, p = placeEl.value, s = sortEl.value || 'new';

    yearEl.innerHTML = '';
    yearEl.appendChild(new Option(t('Alle Jahre', 'All years'), ''));
    years.forEach(function(v){ yearEl.appendChild(new Option(v, v)); });
    if (undated) yearEl.appendChild(new Option(t('ohne Datum', 'no date'), '__none__'));
    yearEl.value = y || '';

    placeEl.innerHTML = '';
    placeEl.appendChild(new Option(t('Alle Orte', 'All places'), ''));
    places.forEach(function(v){ placeEl.appendChild(new Option(v, v)); });
    if (noPlace) placeEl.appendChild(new Option(t('ohne Ortsangabe', 'no place given'), '__none__'));
    placeEl.value = p || '';

    sortEl.innerHTML = '';
    sortEl.appendChild(new Option(t('Neueste zuerst', 'Newest first'), 'new'));
    sortEl.appendChild(new Option(t('Älteste zuerst', 'Oldest first'), 'old'));
    sortEl.value = s;

    if (qEl.dataset.phDe) qEl.placeholder = t(qEl.dataset.phDe, qEl.dataset.phEn);
  }

  function buildTagChips(){
    tagsEl.innerHTML = '';
    tagIds.forEach(function(id){
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'tag-chip';
      b.dataset.tag = id;
      b.textContent = tagLabels[id] || id;
      b.setAttribute('aria-pressed', activeTags.indexOf(id) >= 0 ? 'true' : 'false');
      b.addEventListener('click', function(){
        var i = activeTags.indexOf(id);
        if (i >= 0) activeTags.splice(i, 1); else activeTags.push(id);
        b.setAttribute('aria-pressed', activeTags.indexOf(id) >= 0 ? 'true' : 'false');
        refilter();
      });
      tagsEl.appendChild(b);
    });
  }

  function apply(){
    var q     = (qEl.value || '').trim().toLowerCase();
    var year  = yearEl.value;
    var place = placeEl.value;

    visible = [];
    items.forEach(function(it){
      var ok = true;
      if (q && (it.dataset.search || '').indexOf(q) < 0) ok = false;
      if (ok && year) {
        ok = (year === '__none__') ? !it.dataset.date : it.dataset.year === year;
      }
      if (ok && place) {
        ok = (place === '__none__') ? !it.dataset.place : it.dataset.place === place;
      }
      if (ok && activeTags.length) {
        var mine = (it.dataset.tags || '').split(/\s+/);
        ok = activeTags.every(function(tg){ return mine.indexOf(tg) >= 0; });
      }
      it.hidden = !ok;
      if (ok) visible.push(it);
    });

    // Sortierung: undatierte immer ans Ende
    var asc = sortEl.value === 'old';
    visible.slice().sort(function(a, b){
      var da = a.dataset.date, db = b.dataset.date;
      if (!da && !db) return 0;
      if (!da) return 1;
      if (!db) return -1;
      return asc ? da.localeCompare(db) : db.localeCompare(da);
    }).forEach(function(it){ grid.appendChild(it); });
    visible = items.filter(function(it){ return !it.hidden; })
                   .sort(function(a, b){
                     return Array.prototype.indexOf.call(grid.children, a) -
                            Array.prototype.indexOf.call(grid.children, b);
                   });

    emptyEl.hidden = visible.length > 0;
  }

  function pageCount(){ return Math.max(1, Math.ceil(visible.length / PER_PAGE)); }

  function render(){
    var pages = pageCount();
    if (page > pages) page = pages;
    if (page < 1) page = 1;
    var from = (page - 1) * PER_PAGE, to = from + PER_PAGE;
    visible.forEach(function(it, i){ it.hidden = i < from || i >= to; });

    var n = visible.length, total = items.length;
    var txt = (n === total)
      ? t(total + ' Bilder', total + ' images')
      : t(n + ' von ' + total + ' Bildern', n + ' of ' + total + ' images');
    if (pages > 1) txt += t(' · Seite ' + page + ' von ' + pages, ' · page ' + page + ' of ' + pages);
    countEl.textContent = txt;

    buildPager(pages);
  }

  function pagerButton(label, target, opts){
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'pager-btn' + (opts.cls ? ' ' + opts.cls : '');
    b.textContent = label;
    if (opts.aria) b.setAttribute('aria-label', opts.aria);
    if (opts.current) b.setAttribute('aria-current', 'page');
    if (opts.disabled) b.disabled = true;
    else b.addEventListener('click', function(){ goTo(target); });
    return b;
  }

  function buildPager(pages){
    pagerEl.innerHTML = '';
    pagerEl.hidden = pages < 2;
    if (pages < 2) return;
    pagerEl.appendChild(pagerButton('←', page - 1, {
      cls: 'pager-step', aria: t('Vorherige Seite', 'Previous page'), disabled: page === 1 }));
    for (var p = 1; p <= pages; p++) {
      pagerEl.appendChild(pagerButton(String(p), p, {
        aria: t('Seite ', 'Page ') + p, current: p === page }));
    }
    pagerEl.appendChild(pagerButton('→', page + 1, {
      cls: 'pager-step', aria: t('Nächste Seite', 'Next page'), disabled: page === pages }));
  }

  // Seite wechseln: ueber die Adresse, damit ein Eintrag in der History entsteht
  function goTo(p){
    if (p === page) return;
    location.hash = p > 1 ? HASH + p : '';
  }

  function setPage(p, quiet){
    page = p;
    render();
    if (p > 1) history.replaceState(null, '', '#' + HASH + p);
    else if (location.hash) history.replaceState(null, '', location.pathname + location.search);
    if (!quiet) {
      // zum Anfang des Rasters, unter den fixierten Kopf
      var head = document.querySelector('header.site');
      var y = grid.getBoundingClientRect().top + window.pageYOffset -
              (head ? head.offsetHeight : 0) - 16;
      window.scrollTo(0, Math.max(0, y));
    }
  }

  window.addEventListener('hashchange', function(){
    var p = pageFromHash();
    if (p !== page) setPage(p);
  });

  // Filter geaendert: zurueck auf Seite 1
  function refilter(){
    apply();
    setPage(1, true);
  }

  qEl.addEventListener('input', refilter);
  yearEl.addEventListener('change', refilter);
  placeEl.addEventListener('change', refilter);
  sortEl.addEventListener('change', refilter);
  form.addEventListener('submit', function(e){ e.preventDefault(); });
  resetEl.addEventListener('click', function(){
    qEl.value = ''; yearEl.value = ''; placeEl.value = ''; sortEl.value = 'new';
    activeTags = [];
    tagsEl.querySelectorAll('.tag-chip').forEach(function(b){ b.setAttribute('aria-pressed','false'); });
    refilter();
    qEl.focus();
  });

  fillSelects();
  buildTagChips();
  apply();
  page = pageFromHash();
  render();
  form.hidden = false;   // erst jetzt einblenden — ohne JS bleibt die Leiste weg
})();
