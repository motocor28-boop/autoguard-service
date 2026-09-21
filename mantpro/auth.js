/* Sesión segura Supabase con recuperación y establecimiento de contraseña. */
(()=>{
  const C=window.MANTPRO_CONFIG||{}, base=(C.supabaseUrl||'').replace(/\/$/,''), KEY='mantpro-cloud-session-v2';
  const rawFetch=window.fetch.bind(window);
  const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}};
  const write=s=>s?localStorage.setItem(KEY,JSON.stringify(s)):localStorage.removeItem(KEY);
  const token=()=>read()?.access_token||'';
  const emit=(name,detail)=>window.dispatchEvent(new CustomEvent(name,{detail}));
  const headers=(extra={})=>({'apikey':C.supabaseAnonKey||'',...extra});

  async function authFetch(path,options={}){
    const h=new Headers(options.headers||{}); h.set('apikey',C.supabaseAnonKey||'');
    if(token())h.set('Authorization','Bearer '+token());
    return rawFetch(base+path,{...options,headers:h});
  }

  async function refresh(){
    const s=read(); if(!s?.refresh_token)return false;
    try{
      const r=await rawFetch(base+'/auth/v1/token?grant_type=refresh_token',{
        method:'POST',
        headers:headers({'Content-Type':'application/json'}),
        body:JSON.stringify({refresh_token:s.refresh_token})
      });
      if(!r.ok)throw Error('Sesión vencida');
      const n=await r.json();
      write({...n,expires_at:Date.now()+(Number(n.expires_in)||3600)*1000});
      emit('mantpro-auth-changed',{signedIn:true});
      return true;
    }catch{
      write(null);emit('mantpro-auth-changed',{signedIn:false});return false;
    }
  }

  async function ensure(){
    const s=read(); if(!s)return false;
    if((s.expires_at||0)-Date.now()<120000)return refresh();
    return true;
  }

  window.fetch=async(url,options={})=>{
    if(typeof url==='string'&&base&&url.startsWith(base)){
      await ensure();
      const h=new Headers(options.headers||{});
      h.set('apikey',C.supabaseAnonKey||'');
      if(token())h.set('Authorization','Bearer '+token());
      return rawFetch(url,{...options,headers:h});
    }
    return rawFetch(url,options);
  };

  function overlay(){
    if(document.getElementById('auth-overlay'))return;
    const box=document.createElement('div');
    box.id='auth-overlay';box.className='auth-overlay';
    box.innerHTML='<form id="auth-form" class="auth-card">'
      +'<span class="eyebrow">Acceso privado</span>'
      +'<h1>Ingresar a MANTPRO IA</h1>'
      +'<p class="muted">Usa el mismo usuario y contraseña en el computador y teléfono.</p>'
      +'<label>Usuario<input required autocomplete="username" name="username" value="'+(C.username||'esteban')+'"></label>'
      +'<label>Contraseña<input required minlength="8" autocomplete="current-password" type="password" name="password" placeholder="Mínimo 8 caracteres"></label>'
      +'<p id="auth-message" class="muted">Si no recuerdas la clave, usa “Establecer / restablecer contraseña”.</p>'
      +'<button class="primary">Ingresar</button>'
      +'<button type="button" id="auth-reset" class="outline">Establecer / restablecer contraseña</button>'
      +'<button type="button" id="auth-register" class="outline">Crear usuario por primera vez</button>'
      +'</form>';
    document.body.appendChild(box);
    box.querySelector('#auth-form').onsubmit=login;
    box.querySelector('#auth-reset').onclick=requestPasswordReset;
    box.querySelector('#auth-register').onclick=register;
  }

  function credentials(form){
    const d=new FormData(form);
    return{
      username:String(d.get('username')||'').trim().toLowerCase(),
      password:String(d.get('password')||'')
    };
  }

  function accept(data){
    write({...data,expires_at:Date.now()+(Number(data.expires_in)||3600)*1000});
    document.getElementById('auth-overlay')?.remove();
    emit('mantpro-auth-changed',{signedIn:true});
  }

  async function login(e){
    e.preventDefault();
    const form=e.currentTarget,{username,password}=credentials(form),
      msg=document.getElementById('auth-message'),btn=form.querySelector('button.primary');
    if(username!==(C.username||'esteban').toLowerCase()){
      msg.className='auth-error';msg.textContent='Usuario incorrecto.';return;
    }
    btn.disabled=true;msg.className='muted';msg.textContent='Verificando acceso…';
    try{
      const r=await rawFetch(base+'/auth/v1/token?grant_type=password',{
        method:'POST',
        headers:headers({'Content-Type':'application/json'}),
        body:JSON.stringify({email:C.allowedEmail,password})
      });
      const detail=await r.json().catch(()=>({}));
      if(!r.ok)throw Error(detail.msg||detail.message||('Error '+r.status));
      accept(detail);
    }catch(err){
      msg.className='auth-error';
      msg.textContent=/invalid login/i.test(err.message||'')
        ?'Usuario o contraseña incorrectos. Puedes establecer una nueva contraseña con el botón de recuperación.'
        :'No fue posible ingresar: '+(err.message||'error desconocido');
    }finally{btn.disabled=false}
  }

  async function register(){
    const form=document.getElementById('auth-form'),
      {username,password}=credentials(form),
      msg=document.getElementById('auth-message'),
      btn=document.getElementById('auth-register');
    if(username!==(C.username||'esteban').toLowerCase()){
      msg.className='auth-error';msg.textContent='Usa el usuario esteban.';return;
    }
    if(password.length<8){
      msg.className='auth-error';msg.textContent='Crea una contraseña de al menos 8 caracteres.';return;
    }
    btn.disabled=true;msg.className='muted';msg.textContent='Creando usuario seguro…';
    try{
      const r=await rawFetch(base+'/auth/v1/signup',{
        method:'POST',
        headers:headers({'Content-Type':'application/json'}),
        body:JSON.stringify({email:C.allowedEmail,password,data:{name:C.supervisor,username:C.username}})
      });
      const detail=await r.json().catch(()=>({}));
      if(!r.ok)throw Error(detail.msg||detail.message||('Error '+r.status));
      if(detail.access_token)accept(detail);
      else{
        msg.className='auth-ok';
        msg.textContent='Usuario creado. Intenta ingresar con la misma contraseña.';
      }
    }catch(err){
      msg.className='auth-error';
      msg.textContent=/already registered/i.test(err.message||'')
        ?'El usuario ya existe. Usa “Establecer / restablecer contraseña”.'
        :'No fue posible crear el usuario: '+(err.message||'error desconocido');
    }finally{btn.disabled=false}
  }

  async function requestPasswordReset(){
    const form=document.getElementById('auth-form'),
      {username}=credentials(form),
      msg=document.getElementById('auth-message'),
      btn=document.getElementById('auth-reset');
    if(username!==(C.username||'esteban').toLowerCase()){
      msg.className='auth-error';msg.textContent='Usa el usuario esteban.';return;
    }
    btn.disabled=true;msg.className='muted';msg.textContent='Preparando cambio de contraseña…';
    try{
      const redirect=location.origin+location.pathname;
      const r=await rawFetch(base+'/auth/v1/recover?redirect_to='+encodeURIComponent(redirect),{
        method:'POST',
        headers:headers({'Content-Type':'application/json'}),
        body:JSON.stringify({email:C.allowedEmail})
      });
      const detail=await r.json().catch(()=>({}));
      if(!r.ok)throw Error(detail.msg||detail.message||('Error '+r.status));
      msg.className='auth-ok';
      msg.textContent='Revisa tu correo. Abre el enlace de recuperación de MANTPRO para establecer una contraseña nueva.';
    }catch(err){
      msg.className='auth-error';
      msg.textContent='No fue posible iniciar la recuperación: '+(err.message||'error desconocido');
    }finally{btn.disabled=false}
  }

  function passwordOverlay(){
    document.getElementById('auth-overlay')?.remove();
    const box=document.createElement('div');
    box.id='auth-overlay';box.className='auth-overlay';
    box.innerHTML='<form id="password-form" class="auth-card">'
      +'<span class="eyebrow">Seguridad MANTPRO</span>'
      +'<h1>Establecer nueva contraseña</h1>'
      +'<p class="muted">Crea una clave de al menos 8 caracteres. Será la misma para computador y teléfono.</p>'
      +'<label>Nueva contraseña<input required minlength="8" autocomplete="new-password" type="password" name="password" placeholder="Mínimo 8 caracteres"></label>'
      +'<label>Repetir contraseña<input required minlength="8" autocomplete="new-password" type="password" name="confirm" placeholder="Repite la contraseña"></label>'
      +'<p id="auth-message" class="muted">El cambio se aplicará inmediatamente.</p>'
      +'<button class="primary">Guardar nueva contraseña</button>'
      +'</form>';
    document.body.appendChild(box);
    box.querySelector('#password-form').onsubmit=updatePassword;
  }

  async function updatePassword(e){
    e.preventDefault();
    const form=e.currentTarget,
      d=new FormData(form),
      password=String(d.get('password')||''),
      confirm=String(d.get('confirm')||''),
      msg=document.getElementById('auth-message'),
      btn=form.querySelector('button.primary');
    if(password.length<8){
      msg.className='auth-error';msg.textContent='La contraseña debe tener al menos 8 caracteres.';return;
    }
    if(password!==confirm){
      msg.className='auth-error';msg.textContent='Las contraseñas no coinciden.';return;
    }
    if(!token()){
      msg.className='auth-error';msg.textContent='El enlace de recuperación venció. Solicita uno nuevo.';return;
    }
    btn.disabled=true;msg.className='muted';msg.textContent='Guardando nueva contraseña…';
    try{
      const r=await rawFetch(base+'/auth/v1/user',{
        method:'PUT',
        headers:headers({'Authorization':'Bearer '+token(),'Content-Type':'application/json'}),
        body:JSON.stringify({password})
      });
      const detail=await r.json().catch(()=>({}));
      if(!r.ok)throw Error(detail.msg||detail.message||('Error '+r.status));
      msg.className='auth-ok';
      msg.textContent='Contraseña actualizada correctamente. Abriendo MANTPRO…';
      emit('mantpro-auth-changed',{signedIn:true,passwordUpdated:true});
      setTimeout(()=>location.reload(),900);
    }catch(err){
      msg.className='auth-error';
      msg.textContent='No fue posible guardar la contraseña: '+(err.message||'error desconocido');
      btn.disabled=false;
    }
  }

  function finishCallback(){
    const hash=new URLSearchParams(location.hash.slice(1));
    if(hash.get('access_token')){
      const type=hash.get('type')||'';
      write({
        access_token:hash.get('access_token'),
        refresh_token:hash.get('refresh_token'),
        token_type:hash.get('token_type')||'bearer',
        expires_at:Date.now()+(Number(hash.get('expires_in'))||3600)*1000
      });
      history.replaceState({},'',location.pathname+location.search);
      return{authenticated:true,recovery:type==='recovery'};
    }
    const url=new URL(location.href),code=url.searchParams.get('code');
    if(code){
      url.searchParams.delete('code');
      history.replaceState({},'',url.pathname+url.search);
    }
    return{authenticated:false,recovery:false};
  }

  async function signOut(){
    try{await authFetch('/auth/v1/logout',{method:'POST'})}catch{}
    write(null);location.reload();
  }

  async function start(){
    if(location.hostname==='127.0.0.1'||location.hostname==='localhost'){
      emit('mantpro-auth-ready',{signedIn:true,localTest:true});return;
    }
    if(C.requireAuth===false){
      document.getElementById('auth-overlay')?.remove();
      emit('mantpro-auth-ready',{signedIn:false,openMode:true});return;
    }
    const callback=finishCallback();
    if(callback.recovery){
      passwordOverlay();
      emit('mantpro-auth-ready',{signedIn:false,recovery:true});
      return;
    }
    let ok=callback.authenticated||await ensure();
    if(!ok)overlay();else document.getElementById('auth-overlay')?.remove();
    emit('mantpro-auth-ready',{signedIn:ok});
  }

  window.MANTPRO_AUTH={
    token,session:read,ensure,authFetch,signOut,showLogin:overlay,
    requestPasswordReset,passwordOverlay
  };
  start();
  setInterval(()=>ensure(),60000);
})();
