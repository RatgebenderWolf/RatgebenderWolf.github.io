function setLang(lang){
  document.documentElement.setAttribute('data-lang', lang);
  document.documentElement.setAttribute('lang', lang);
  document.querySelectorAll('.lang-toggle button').forEach(function(b){
    b.setAttribute('aria-pressed', String(b.dataset.lang === lang));
  });
  try{ localStorage.setItem('site-lang', lang); }catch(e){}
  // Seiten mit sprachabhaengigen Attributen (z. B. alt-Texte) koennen darauf reagieren
  document.dispatchEvent(new CustomEvent('site-lang-change', { detail:{ lang:lang } }));
}

document.addEventListener('DOMContentLoaded', function(){
  var saved = 'de';
  try{ saved = localStorage.getItem('site-lang') === 'en' ? 'en' : 'de'; }catch(e){}
  setLang(saved);
  document.querySelectorAll('.lang-toggle button').forEach(function(btn){
    btn.addEventListener('click', function(){ setLang(btn.dataset.lang); });
  });
});
