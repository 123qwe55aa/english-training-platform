'use strict';
let toastTimer;
function toast(text){const el=document.querySelector('#toast');el.textContent=text;el.classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.classList.remove('visible'),4000);}
document.querySelectorAll('[data-speak]').forEach(button=>button.addEventListener('click',()=>{if(!('speechSynthesis' in window)){toast('这个浏览器暂不支持朗读，请由老师示范。');return;}speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(button.dataset.speak);utterance.lang='en-US';utterance.rate=.82;speechSynthesis.speak(utterance);toast('浏览器合成朗读，可配合老师示范一起练习。');}));
const translations=document.querySelector('[data-toggle-translations]');if(translations)translations.addEventListener('click',()=>{const hide=translations.textContent==='隐藏中文';document.querySelectorAll('.translation').forEach(el=>el.hidden=hide);translations.textContent=hide?'显示中文':'隐藏中文';});
document.querySelectorAll('[data-seek]').forEach(button=>button.addEventListener('click',()=>{const video=document.querySelector('video');if(video){video.currentTime=Number(button.dataset.seek);video.play().catch(()=>toast('请点击视频播放按钮继续。'));video.scrollIntoView({behavior:'smooth',block:'center'});}}));
