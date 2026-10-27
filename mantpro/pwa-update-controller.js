/* EECR: actualización PWA sin limpiar datos ni cachés antes de instalar la nueva versión. */
(()=>{
  'use strict';
  const BUILD='20261026-limpieza-pin-v1';
  const SW='sw.js?build='+BUILD;
  window.EECR_ACTIVE_BUILD=BUILD;
  async function update(){
    if(!('serviceWorker' in navigator)||!navigator.onLine)return;
    try{
      const registration=await navigator.serviceWorker.register(SW,{scope:'./',updateViaCache:'none'});
      await registration.update();
      if(registration.waiting)registration.waiting.postMessage({type:'SKIP_WAITING'});
    }catch(error){console.warn('EECR actualización PWA pendiente:',error);}
  }
  window.addEventListener('load',update,{once:true});
  navigator.serviceWorker?.addEventListener?.('controllerchange',()=>{
    if(sessionStorage.getItem('eecr-controller-reloaded')===BUILD)return;
    sessionStorage.setItem('eecr-controller-reloaded',BUILD);
    location.reload();
  });
  window.EECR_PWA_BUILD=BUILD;
})();