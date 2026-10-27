/* EECR producción: retiro definitivo del antiguo conjunto demostrativo enero-marzo 2026.
   Solo se eliminan registros con identificador q1- o marca synthetic-training.
   Nunca se filtra exclusivamente por fecha ni se borra un trabajo real. */
(()=>{
'use strict';
const STORE='mantpro-records-v3',ACK='eecr-device-ack-v1',MARK='eecr-q1-demonstration-removed-v1';
const isDemo=x=>!!x&&(String(x.id||'').startsWith('q1-')||x.provenance?.kind==='synthetic-training'||x.data?.provenance?.kind==='synthetic-training');
function clean(){
 try{
  const raw=localStorage.getItem(STORE),list=JSON.parse(raw||'[]');
  if(!Array.isArray(list))return 0;
  const kept=list.filter(x=>!isDemo(x)),removed=list.length-kept.length;
  if(removed){
   // No limpiar toda la base: conservación de registros originales de terreno.
   localStorage.setItem(STORE,JSON.stringify(kept));
   try{const a=JSON.parse(localStorage.getItem(ACK)||'{}');for(const r of list)if(isDemo(r))delete a[r.id];localStorage.setItem(ACK,JSON.stringify(a));}catch{}
   window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{retiredQ1Demo:removed}}));
   window.MANTPRO?.render?.();
  }
  localStorage.setItem(MARK,new Date().toISOString());return removed;
 }catch(error){console.warn('EECR: limpieza Q1 no aplicada:',error);return 0;}
}
function init(){clean();setInterval(clean,90000);}
window.MANTPRO_Q1_CASES={load:()=>0,bridge:async()=>false,records:[],local:{},retire:clean,build:'20261026-q1-retired'};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();