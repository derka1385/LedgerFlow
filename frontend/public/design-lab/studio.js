const launch=document.querySelector('#launch'),replay=document.querySelector('#replay'),skip=document.querySelector('#skip'),theme=document.querySelector('#theme');
let endTimer,hideTimer;
function closeLaunch(){clearTimeout(endTimer);launch.classList.add('leaving');hideTimer=setTimeout(()=>{launch.hidden=true;replay.focus();},matchMedia('(prefers-reduced-motion: reduce)').matches?0:300);}
function play(){clearTimeout(endTimer);clearTimeout(hideTimer);launch.hidden=true;launch.classList.remove('leaving');requestAnimationFrame(()=>{launch.hidden=false;skip.focus();endTimer=setTimeout(closeLaunch,matchMedia('(prefers-reduced-motion: reduce)').matches?450:1550);});}
replay.addEventListener('click',play);skip.addEventListener('click',closeLaunch);document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!launch.hidden)closeLaunch();if(e.key==='Tab'&&!launch.hidden){e.preventDefault();skip.focus();}});
theme.addEventListener('click',()=>{const light=document.body.classList.toggle('light-mode');theme.setAttribute('aria-pressed',String(light));theme.textContent=light?'Apparence sombre':'Apparence claire';});
if(location.hash!=='#waves') play();

const threadToggle=document.querySelector('#threads-toggle');
threadToggle.addEventListener('click',()=>{const paused=threadToggle.getAttribute('aria-pressed')!=='true';threadToggle.setAttribute('aria-pressed',String(paused));threadToggle.textContent=paused?'Reprendre les animations':'Mettre en pause';document.querySelectorAll('[data-motion]').forEach(img=>{img.src=paused?img.dataset.motion.replace('.svg','-still.svg'):img.dataset.motion;});});

const wavesToggle=document.querySelector('#waves-toggle');
wavesToggle.addEventListener('click',()=>{const paused=wavesToggle.getAttribute('aria-pressed')!=='true';wavesToggle.setAttribute('aria-pressed',String(paused));wavesToggle.textContent=paused?'Reprendre les vagues':'Mettre les vagues en pause';document.querySelectorAll('[data-motion="flow-field.svg"]').forEach(img=>{img.src=paused?'flow-field-still.svg':'flow-field.svg';});});
