/* EECR/MantPro: sesión OTP persistente, uso offline y acceso autenticado a Supabase. */
(()=>{
  'use strict';
  const C=window.MANTPRO_CONFIG||{}, base=String(C.supabaseUrl||'').replace(/\/$/,'');
  const KEY='mantpro-cloud-session-v2';
  const notify=(name,detail)=>window.dispatchEvent(new CustomEvent(name,{detail}));
  const html=s=>String(s??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  let session=null,refreshing=null;
  try{const stored=JSON.parse(localStorage.getItem(KEY)||'null');if(stored?.access_token)session=stored;}catch{}
  function save(s){session=s;try{if(s)localStorage.setItem(KEY,JSON.stringify(s));else localStorage.removeItem(KEY);}catch{}}
  function active(){return session?.access_token&&Date.now()<Number(session.expires_at||0)-15000;}
  const token=()=>active()?session.access_token:'';
  const currentSession=()=>session;
  async function api(path,body){
    if(!base||!C.supabaseAnonKey)throw Error('Falta configurar el servidor de sincronización.');
    const r=await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json','apikey':C.supabaseAnonKey},body:JSON.stringify(body)});
    let result={};try{result=await r.json();}catch{}
    if(!r.ok)throw Error(result.msg||result.error_description||result.message||('HTTP '+r.status));
    return result;
  }
  function installTokens(data){
    if(!data?.access_token||!data?.refresh_token)throw Error('Respuesta de sesión incompleta.');
    save({...data,expires_at:Date.now()+Math.max(30,Number(data.expires_in)||3600)*1000});
    notify('mantpro-auth-ready',{authenticated:true});notify('mantpro-auth-changed',{authenticated:true});
  }
  async function ensure(){
    if(active())return true;
    if(!session?.refresh_token||!navigator.onLine)return false;
    if(!refreshing)refreshing=(async()=>{
      try{installTokens(await api('/auth/v1/token?grant_type=refresh_token',{refresh_token:session.refresh_token}));return true;}
      catch(e){console.warn('EECR: renovación de sesión fallida',e.message);return false;}
      finally{refreshing=null;}
    })();
    return refreshing;
  }
  async function authFetch(path,options={}){
    if(!await ensure())throw Error('Inicia sesión para sincronizar. Los registros locales se conservaron.');
    const headers=new Headers(options.headers||{});
    headers.set('apikey',C.supabaseAnonKey);
    headers.set('Authorization','Bearer '+token());
    return fetch(base+path,{...options,headers});
  }
  function close(){document.getElementById('eecr-cloud-login')?.remove();}
  function overlay(){
    let el=document.getElementById('eecr-cloud-login');if(el)return el;
    el=document.createElement('div');el.id='eecr-cloud-login';
    el.setAttribute('role','dialog');el.setAttribute('aria-label','Vincular sincronización EECR');
    el.style.cssText='position:fixed;inset:0;z-index:100000;background:#000b;display:grid;place-items:center;padding:20px;color:#e8f0f6;font:16px Arial,sans-serif';
    el.innerHTML='<form id="eecr-cloud-form" style="width:min(410px,100%);padding:24px;background:#1c2832;border:1px solid #536574;border-radius:14px;display:grid;gap:14px">'+
      '<h2 style="margin:0">Vincular EECR / MantPro</h2>'+
      '<p style="margin:0">Los datos guardados en este dispositivo permanecen intactos. La conexión requiere una verificación de correo una sola vez por dispositivo.</p>'+
      '<label>Correo autorizado<input id="eecr-cloud-email" type="email" required style="width:100%;padding:10px;box-sizing:border-box" value="'+html(C.allowedEmail||'')+'"></label>'+
      '<button id="eecr-cloud-send" type="button" style="padding:12px">Enviar enlace o código</button>'+
      '<label>Código de 6 dígitos (solo si el correo incluye un código)<input id="eecr-cloud-code" inputmode="numeric" maxlength="8" autocomplete="one-time-code" style="width:100%;padding:10px;box-sizing:border-box"></label>'+
      '<button type="submit" style="padding:12px;background:#ff8e17;color:#171b22;border:0;border-radius:5px;font-weight:bold">Activar sincronización</button>'+
      '<div id="eecr-cloud-message" role="status" style="font-size:14px"></div>'+
      '<button id="eecr-cloud-close" type="button" style="background:none;color:inherit;border:0;text-decoration:underline">Seguir trabajando sin conexión</button></form>';
    document.body.append(el);
    const form=el.querySelector('form'), msg=el.querySelector('#eecr-cloud-message'), em=el.querySelector('#eecr-cloud-email');
    const checkEmail=()=>{const email=em.value.trim().toLowerCase();if(C.allowedEmail&&email!==String(C.allowedEmail).toLowerCase())throw Error('Este correo no está autorizado para EECR.');return email;};
    el.querySelector('#eecr-cloud-close').onclick=close;
    el.querySelector('#eecr-cloud-send').onclick=async()=>{
      try{msg.textContent='Enviando…';await api('/auth/v1/otp?redirect_to='+encodeURIComponent(new URL('./',location.href).href),{email:checkEmail(),create_user:false});msg.textContent='Revisa el mensaje más reciente: si contiene un enlace, ábrelo una sola vez en este teléfono; si contiene un código de seis dígitos, introdúcelo aquí.';}
      catch(e){msg.textContent='Error de envío: '+e.message;}
    };
    form.onsubmit=async e=>{
      e.preventDefault();
      try{msg.textContent='Verificando…';const email=checkEmail(),code=el.querySelector('#eecr-cloud-code').value.trim();if(!/^[0-9]{6,8}$/.test(code))throw Error('Escribe el código recibido en el correo.');
        const result=await api('/auth/v1/verify',{email,token:code,type:'email'});
        installTokens(result);close();
      }catch(error){msg.textContent='No se pudo vincular: '+(/token has expired|token.*invalid/i.test(error.message)?'Código o enlace caducado o ya utilizado. Solicita uno nuevo y usa el correo más reciente.':error.message);}
    };
    return el;
  }
  async function signOut(){save(null);notify('mantpro-auth-changed',{authenticated:false});}
  function linkFromEmail(){
    try{
      const hash=new URLSearchParams(location.hash.slice(1));
      if(hash.get('access_token')&&hash.get('refresh_token')){
        installTokens({access_token:hash.get('access_token'),refresh_token:hash.get('refresh_token'),expires_in:Number(hash.get('expires_in')||3600)});
        history.replaceState(null,'',location.pathname+location.search);
      }
    }catch(e){console.warn('EECR: enlace de acceso inválido',e);}
  }
  window.MANTPRO_AUTH={token,session:currentSession,ensure,authFetch,signOut,showLogin:overlay,requestPasswordReset:overlay,passwordOverlay:overlay};
  linkFromEmail();
  // Iniciar sin bloquear trabajo offline ni solicitar contraseña al abrir.
  Promise.resolve().then(()=>ensure()).then(ok=>{if(ok)notify('mantpro-auth-ready',{authenticated:true});});
})();