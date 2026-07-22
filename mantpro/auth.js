/* Sesión segura Supabase con enlace mágico, renovación automática y acceso persistente. */
(()=>{
  const C=window.MANTPRO_CONFIG||{}, base=(C.supabaseUrl||'').replace(/\/$/,''), KEY='mantpro-cloud-session-v2';
  const rawFetch=window.fetch.bind(window);
  const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}};
  const write=s=>s?localStorage.setItem(KEY,JSON.stringify(s)):localStorage.removeItem(KEY);
  const token=()=>read()?.access_token||'';
  const emit=(name,detail)=>window.dispatchEvent(new CustomEvent(name,{detail}));
  async function authFetch(path,options={}){
    const headers=new Headers(options.headers||{}); headers.set('apikey',C.supabaseAnonKey||'');
    if(token())headers.set('Authorization','Bearer '+token());
    return rawFetch(base+path,{...options,headers});
  }
  async function refresh(){
    const s=read(); if(!s?.refresh_token)return false;
    try{
      const r=await rawFetch(base+'/auth/v1/token?grant_type=refresh_token',{method:'POST',headers:{apikey:C.supabaseAnonKey,'Content-Type':'application/json'},body:JSON.stringify({refresh_token:s.refresh_token})});
      if(!r.ok)throw Error('Sesión vencida'); const n=await r.json();
      write({...n,expires_at:Date.now()+(Number(n.expires_in)||3600)*1000}); emit('mantpro-auth-changed',{signedIn:true}); return true;
    }catch{write(null);emit('mantpro-auth-changed',{signedIn:false});return false}
  }
  async function ensure(){const s=read();if(!s)return false;if((s.expires_at||0)-Date.now()<120000)return refresh();return true}
  window.fetch=async(url,options={})=>{
    if(typeof url==='string'&&base&&url.startsWith(base)){
      await ensure(); const headers=new Headers(options.headers||{});headers.set('apikey',C.supabaseAnonKey||'');if(token())headers.set('Authorization','Bearer '+token());return rawFetch(url,{...options,headers});
    }
    return rawFetch(url,options);
  };
  function overlay(){
    if(document.getElementById('auth-overlay'))return;
    const box=document.createElement('div');box.id='auth-overlay';box.className='auth-overlay';
    box.innerHTML='<form id="auth-form" class="auth-card"><span class="eyebrow">Acceso privado</span><h1>Vincular MANTPRO IA</h1><p class="muted">Ingresa el correo autorizado. Recibirás un enlace seguro y este dispositivo recordará la sesión.</p><label>Correo electrónico<input required autocomplete="email" type="email" name="email" value="'+(C.allowedEmail||'')+'"></label><p id="auth-message" class="muted">No se solicita contraseña.</p><button class="primary">Enviar enlace de acceso</button><button type="button" id="auth-retry" class="outline">Ya abrí el enlace</button></form>';
    document.body.appendChild(box);box.querySelector('#auth-form').onsubmit=requestLink;box.querySelector('#auth-retry').onclick=()=>location.reload();
  }
  async function requestLink(e){
    e.preventDefault();const form=e.currentTarget,email=String(new FormData(form).get('email')||'').trim().toLowerCase(),msg=document.getElementById('auth-message'),btn=form.querySelector('button.primary');
    if(C.allowedEmail&&email!==C.allowedEmail.toLowerCase()){msg.className='auth-error';msg.textContent='Este correo no está autorizado.';return}
    btn.disabled=true;msg.className='muted';msg.textContent='Enviando enlace seguro…';
    try{
      const redirect=location.origin+location.pathname;
      const r=await rawFetch(base+'/auth/v1/otp',{method:'POST',headers:{apikey:C.supabaseAnonKey,'Content-Type':'application/json'},body:JSON.stringify({email,create_user:true,options:{emailRedirectTo:redirect}})});
      const detail=await r.json().catch(()=>({}));if(!r.ok)throw Error(detail.msg||detail.message||('Error '+r.status));
      msg.className='auth-ok';msg.textContent='Enlace enviado. Revisa Gmail y abre el mensaje de Supabase.';
    }catch(err){
      const rate=/rate limit/i.test(err.message||'');msg.className='auth-error';msg.textContent=rate?'Supabase alcanzó temporalmente su límite de correos. Espera unos minutos y pulsa nuevamente una sola vez.':'No fue posible enviar el enlace: '+(err.message||'error desconocido');
    }finally{btn.disabled=false}
  }
  function finishCallback(){
    const hash=new URLSearchParams(location.hash.slice(1));
    if(hash.get('access_token')){
      write({access_token:hash.get('access_token'),refresh_token:hash.get('refresh_token'),token_type:hash.get('token_type')||'bearer',expires_at:Date.now()+(Number(hash.get('expires_in'))||3600)*1000});
      history.replaceState({},'',location.pathname+location.search);return true;
    }
    const url=new URL(location.href),code=url.searchParams.get('code');
    if(code){url.searchParams.delete('code');history.replaceState({},'',url.pathname+url.search);}
    return false;
  }
  async function signOut(){try{await authFetch('/auth/v1/logout',{method:'POST'})}catch{}write(null);location.reload()}
  async function start(){
    if(location.hostname==='127.0.0.1'||location.hostname==='localhost'){emit('mantpro-auth-ready',{signedIn:true,localTest:true});return}
    const callback=finishCallback();let ok=await ensure();if(callback)ok=true;
    if(!ok)overlay();else document.getElementById('auth-overlay')?.remove();
    emit('mantpro-auth-ready',{signedIn:ok});
  }
  window.MANTPRO_AUTH={token,session:read,ensure,authFetch,signOut,showLogin:overlay};
  start();setInterval(()=>ensure(),60000);
})();

