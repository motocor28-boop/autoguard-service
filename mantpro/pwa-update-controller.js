/* EECR — renovación forzada de PWA sin borrar datos operacionales. */
(()=>{
  'use strict';
  const BUILD='20260921-q1-cases-v6';
  const SW=`sw.js?build=${BUILD}`;
  const originalRegister=navigator.serviceWorker?.register?.bind(navigator.serviceWorker);

  async function purgeOldCaches(){
    if(!('caches' in window))return;
    try{
      const keys=await caches.keys();
      await Promise.all(keys.filter(k=>k.startsWith('eecr-supervision-')).map(k=>caches.delete(k)));
    }catch(error){console.warn('EECR limpieza cache:',error)}
  }

  async function update(){
    await purgeOldCaches();
    if(!originalRegister)return;
    try{
      const regs=await navigator.serviceWorker.getRegistrations();
      for(const reg of regs){
        const url=reg.active?.scriptURL||reg.waiting?.scriptURL||reg.installing?.scriptURL||'';
        if(url.includes('/mantpro/sw.js'))await reg.unregister();
      }
      const registration=await originalRegister(SW,{scope:'./',updateViaCache:'none'});
      await registration.update();
      if(registration.waiting)registration.waiting.postMessage({type:'SKIP_WAITING'});
    }catch(error){console.warn('EECR actualización PWA:',error)}
  }

  window.addEventListener('load',update,{once:true});
  navigator.serviceWorker?.addEventListener?.('controllerchange',()=>{
    if(sessionStorage.getItem('eecr-controller-reloaded')===BUILD)return;
    sessionStorage.setItem('eecr-controller-reloaded',BUILD);
    location.reload();
  });
  window.EECR_PWA_BUILD=BUILD;
})();
