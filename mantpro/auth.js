/* MANTPRO IA — acceso abierto controlado. No muestra ni exige autenticación. */
(()=>{
  'use strict';
  const C=window.MANTPRO_CONFIG||{};
  const base=(C.supabaseUrl||'').replace(/\/$/,'');
  const emit=(name,detail)=>window.dispatchEvent(new CustomEvent(name,{detail}));

  function removeOverlay(){
    const el=document.getElementById('auth-overlay');
    if(el)el.remove();
  }

  // Elimina sólo la sesión de autenticación anterior. No toca OT, fotos ni registros de MANTPRO.
  try{localStorage.removeItem('mantpro-cloud-session-v2')}catch{}

  const token=()=>'';
  const session=()=>null;
  const ensure=async()=>true;

  async function authFetch(path,options={}){
    const headers=new Headers(options.headers||{});
    if(C.supabaseAnonKey)headers.set('apikey',C.supabaseAnonKey);
    return fetch(base+path,{...options,headers});
  }

  async function signOut(){
    removeOverlay();
    emit('mantpro-auth-changed',{signedIn:false,openMode:true});
  }

  function openMode(){
    removeOverlay();
    document.documentElement.dataset.mantproOpenAccess='true';
    emit('mantpro-auth-ready',{signedIn:false,openMode:true,bypass:true});
    emit('mantpro-auth-changed',{signedIn:false,openMode:true,bypass:true});
  }

  // Si alguna versión antigua intenta volver a insertar el cuadro de acceso, se elimina automáticamente.
  const observer=new MutationObserver(removeOverlay);
  observer.observe(document.documentElement,{childList:true,subtree:true});

  window.MANTPRO_AUTH={
    token,session,ensure,authFetch,signOut,
    showLogin:openMode,
    requestPasswordReset:openMode,
    passwordOverlay:openMode
  };

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',openMode,{once:true});
  else openMode();
  setTimeout(openMode,0);
  setTimeout(openMode,500);
})();
