(function(){
  var grid = document.getElementById('shotGrid');
  var box  = document.getElementById('lightbox');
  if (!grid || !box) return;

  var items = Array.prototype.slice.call(grid.querySelectorAll('.shot-item'));
  if (!items.length) return;

  /* ---------- Sprache ---------------------------------------------------- */
  function isEN(){ return document.documentElement.getAttribute('data-lang') === 'en'; }
  function t(de, en){ return isEN() ? en : de; }
  function altOf(el){ return el.getAttribute(isEN() ? 'data-alt-en' : 'data-alt-de') || ''; }

  /* ---------- Lightbox --------------------------------------------------- */
  var img = document.getElementById('lbImg');
  var cap = document.getElementById('lbCap');
  var bClose = document.getElementById('lbClose');
  var bPrev  = document.getElementById('lbPrev');
  var bNext  = document.getElementById('lbNext');
  var visible = [];      // aktuell sichtbare Items — die Lightbox blaettert nur durch diese
  var idx = 0;
  var opener = null;

  function show(i){
    if (!visible.length) return;
    idx = (i + visible.length) % visible.length;
    var btn = visible[idx].querySelector('.shot');
    var text = altOf(btn);
    img.src = btn.dataset.large;
    img.alt = text;
    // Kamera nur in der Unterschrift, nicht im alt-Text: sie beschreibt
    // nicht den Bildinhalt und gehoert damit nicht in die Screenreader-Ausgabe.
    var cam = btn.dataset.cam ? '  ·  ' + btn.dataset.cam : '';
    cap.textContent = text + cam + '  ·  ' + (idx + 1) + '/' + visible.length;
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
    if (opener) opener.focus();
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

  var activeTags = [];

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
      if (!id || tagLabels[id]) return;
      tagLabels[id] = {
        de: (chip.querySelector('.lang-de') || {}).textContent || id,
        en: (chip.querySelector('.lang-en') || {}).textContent || id
      };
    });
  });
  years.sort().reverse();
  places.sort(function(a, b){ return a.localeCompare(b, 'de'); });
  tagIds.sort(function(a, b){
    return (tagLabels[a] ? tagLabels[a].de : a).localeCompare(tagLabels[b] ? tagLabels[b].de : b, 'de');
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
      b.textContent = tagLabels[id] ? t(tagLabels[id].de, tagLabels[id].en) : id;
      b.setAttribute('aria-pressed', activeTags.indexOf(id) >= 0 ? 'true' : 'false');
      b.addEventListener('click', function(){
        var i = activeTags.indexOf(id);
        if (i >= 0) activeTags.splice(i, 1); else activeTags.push(id);
        b.setAttribute('aria-pressed', activeTags.indexOf(id) >= 0 ? 'true' : 'false');
        apply();
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

    var n = visible.length, total = items.length;
    countEl.textContent = (n === total)
      ? t(total + ' Bilder', total + ' images')
      : t(n + ' von ' + total + ' Bildern', n + ' of ' + total + ' images');
    emptyEl.hidden = n > 0;
  }

  qEl.addEventListener('input', apply);
  yearEl.addEventListener('change', apply);
  placeEl.addEventListener('change', apply);
  sortEl.addEventListener('change', apply);
  form.addEventListener('submit', function(e){ e.preventDefault(); });
  resetEl.addEventListener('click', function(){
    qEl.value = ''; yearEl.value = ''; placeEl.value = ''; sortEl.value = 'new';
    activeTags = [];
    tagsEl.querySelectorAll('.tag-chip').forEach(function(b){ b.setAttribute('aria-pressed','false'); });
    apply();
    qEl.focus();
  });

  document.addEventListener('site-lang-change', function(){
    document.querySelectorAll('img[data-alt-de]').forEach(function(el){ el.alt = altOf(el); });
    fillSelects();
    buildTagChips();
    apply();
    if (!box.hidden) show(idx);
  });

  fillSelects();
  buildTagChips();
  apply();
  form.hidden = false;   // erst jetzt einblenden — ohne JS bleibt die Leiste weg
})();
