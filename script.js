function setLang(lang){
  document.documentElement.classList.toggle('lang-en', lang === 'en');
  document.documentElement.setAttribute('lang', lang);
  document.querySelectorAll('.lang-toggle button').forEach(function(b){
    b.classList.toggle('active', b.dataset.lang === lang);
  });
  try{ localStorage.setItem('site-lang', lang); }catch(e){}
}

document.addEventListener('DOMContentLoaded', function(){
  var saved = 'de';
  try{ saved = localStorage.getItem('site-lang') || 'de'; }catch(e){}
  setLang(saved);
  document.querySelectorAll('.lang-toggle button').forEach(function(btn){
    btn.addEventListener('click', function(){ setLang(btn.dataset.lang); });
  });
});
