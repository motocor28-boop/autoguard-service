/* Reintento controlado del puente MANTPRO web -> MANTPRO local (INFORME KPI). */
(()=>{
  'use strict';
  let tries=0,timer=null;
  async function run(){
    if(!window.MANTPRO_Q1_CASES?.bridge||/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
    tries++;
    try{if(await window.MANTPRO_Q1_CASES.bridge()){if(timer)clearInterval(timer);timer=null;return}}catch{}
    if(tries>=20&&timer){clearInterval(timer);timer=null}
  }
  const start=()=>{run();if(!timer)timer=setInterval(run,15000)};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('focus',run);
  window.addEventListener('online',run);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)run()});
})();
