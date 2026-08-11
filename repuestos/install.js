(()=>{
  'use strict';
  const btn=document.getElementById('install-app');
  const msg=document.getElementById('install-help');
  let deferredPrompt=null;
  const standalone=()=>window.matchMedia('(display-mode: standalone)').matches||window.navigator.standalone===true;
  const isiOS=()=>/iphone|ipad|ipod/i.test(navigator.userAgent);
  const isAndroid=()=>/android/i.test(navigator.userAgent);
  function setVisible(){
    if(!btn)return;
    btn.hidden=standalone();
    if(!btn.hidden){
      btn.textContent=deferredPrompt?'⬇ Instalar aplicación':(isiOS()?'＋ Instalar en iPhone':'⬇ Instalar en este teléfono');
    }
  }
  async function registerSW(){
    if(!('serviceWorker' in navigator))return;
    try{
      await navigator.serviceWorker.register('./sw.js',{scope:'./'});
      await navigator.serviceWorker.ready;
    }catch(err){console.warn('No fue posible registrar PWA',err)}
  }
  function help(text){
    if(msg){msg.textContent=text;msg.hidden=false;clearTimeout(help.t);help.t=setTimeout(()=>msg.hidden=true,9000)}
    else alert(text);
  }
  window.addEventListener('beforeinstallprompt',e=>{
    e.preventDefault();
    deferredPrompt=e;
    setVisible();
  });
  window.addEventListener('appinstalled',()=>{
    deferredPrompt=null;
    if(btn)btn.hidden=true;
    help('Aplicación instalada correctamente. Ya puede abrirla desde el icono del teléfono.');
  });
  btn?.addEventListener('click',async()=>{
    if(standalone()){btn.hidden=true;return}
    if(deferredPrompt){
      deferredPrompt.prompt();
      const choice=await deferredPrompt.userChoice;
      deferredPrompt=null;
      if(choice.outcome==='accepted')btn.hidden=true; else setVisible();
      return;
    }
    if(isiOS()){
      help('En iPhone/iPad: abra esta página en Safari → Compartir → Añadir a pantalla de inicio → Añadir.');
      return;
    }
    if(isAndroid()){
      help('Chrome aún está preparando la instalación. Abra el menú ⋮ y pulse “Instalar aplicación” o “Agregar a pantalla principal”. Si no aparece, recargue esta página una vez.');
      return;
    }
    help('En Chrome o Edge abra el menú del navegador y seleccione “Instalar aplicación”.');
  });
  registerSW().finally(()=>setVisible());
  setVisible();
})();
