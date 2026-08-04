/* EECR — actualización controlada de la aplicación instalada sin borrar registros. */
(()=>{
  'use strict';
  const BUILD='20260804-mobile-preview-v3';
  const SW=`sw.js?build=${BUILD}`;
  const originalRegister=navigator.serviceWorker?.register?.bind(navigator.serviceWorker);

  if(originalRegister){
    try{
      navigator.serviceWorker.register=(url,options={})=>{
        const target=/\bsw\.js(?:[?#]|$)/.test(String(url))?SW:url;
        return originalRegister(target,{...options,updateViaCache:'none'});
      };
    }catch{}
  }

  async function update(){
    if(!originalRegister)return;
    try{
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
