/* EECR: autorizaciones desde el telefono usando numero identificador, sin enlaces. */
(()=>{
'use strict';
if(!/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
const API='https://gecrjlkfrcrlsjhanfjz.supabase.co/functions/v1/eecr-phone-enrolment';
const STORE='eecr-pair-phone-v1';
const secret=()=>localStorage.getItem('eecr-device-pair-v1')||'';
let phone=localStorage.getItem(STORE)||'',pending=[],working=false,panel=null,joining=false;
const JOIN_STORE='eecr-mobile-join-request-v1';
let waiting=null;
try{waiting=JSON.parse(localStorage.getItem(JOIN_STORE)||'null')}catch{}
const random32=()=>btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(32)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
const parseBytes=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const esc=t=>String(t??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[x]));
async function call(action,extra={}){
 const response=await fetch(API,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,phone,secret:secret(),...extra})});
 const result=await response.json();
 if(!response.ok||!result.ok)throw Error(result.error||'Error de comunicación');
 return result;
}

function finishJoin(){waiting=null;localStorage.removeItem(JOIN_STORE);}
async function requestJoin(value,message){
 if(waiting){
  if(waiting.phone!==value)throw Error('Ya existe una solicitud con otro número. Cancélala o espera a que venza.');
  message.textContent='El grupo existe. Solicitud pendiente: autorízala desde otro teléfono del mismo grupo.';
  return;
 }
 const keys=await crypto.subtle.generateKey({name:'RSA-OAEP',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['encrypt','decrypt']);
 const publicKey=await crypto.subtle.exportKey('jwk',keys.publicKey);
 const privateKey=await crypto.subtle.exportKey('jwk',keys.privateKey);
 const token=random32();
 const platform=/Android/i.test(navigator.userAgent)?'Android':/iPhone/i.test(navigator.userAgent)?'iPhone':'Móvil';
 const deviceLabel='MantPro '+platform+' · equipo '+token.slice(0,5).toUpperCase();
 const response=await call('request_join',{phone:value,token,publicKey,deviceLabel});
 waiting={phone:value,token,requestId:response.requestId,privateKey,expiresAt:response.expiresAt};
 localStorage.setItem(JOIN_STORE,JSON.stringify(waiting));
 message.textContent='Solicitud enviada. Desde otro teléfono ya vinculado a este número, toca «Autorizar equipo». No necesitas enlaces ni códigos.';
}
async function checkJoin(){
 if(!waiting||joining||!navigator.onLine)return;
 joining=true;
 try{
  const response=await call('poll_join',{requestId:waiting.requestId,token:waiting.token});
  if(response.status==='pending')return;
  if(response.status==='expired'||response.status==='rejected'){
   const msg=response.status==='expired'?'La solicitud venció; vuelve a ingresar el número.':'El equipo fue rechazado desde el grupo.';
   finishJoin();
   const label=panel?.querySelector('#eecr-phone-feedback');if(label)label.textContent=msg;
   return;
  }
  if(response.status!=='approved'||!response.ciphertext)return;
  const privateKey=await crypto.subtle.importKey('jwk',waiting.privateKey,{name:'RSA-OAEP',hash:'SHA-256'},false,['decrypt']);
  const plaintext=await crypto.subtle.decrypt({name:'RSA-OAEP'},privateKey,parseBytes(response.ciphertext));
  const key=new TextDecoder().decode(plaintext);
  if(!/^[A-Za-z0-9_-]{43}$/.test(key))throw Error('La autorización del grupo es inválida.');
  if(!window.EECR_DEVICE_SYNC?.adoptAuthorizedChannel)throw Error('Actualiza MantPro móvil para completar la conexión.');
  await window.EECR_DEVICE_SYNC.adoptAuthorizedChannel(key);
  phone=waiting.phone;
  localStorage.setItem(STORE,phone);
  finishJoin();
  close();
  await poll(true);
  const status=document.querySelector('#state');if(status)status.title='Grupo compartido configurado';
 }catch(e){
  console.warn('EECR grupo móvil:',e.message);
  const label=panel?.querySelector('#eecr-phone-feedback');if(label)label.textContent='Conexión pendiente: '+e.message;
 }finally{joining=false;}
}
function close(){panel?.remove();panel=null;}
function openSetup(){
 close();panel=document.createElement('div');panel.id='eecr-phone-setup';
 panel.style.cssText='position:fixed;inset:0;z-index:210000;background:#09131dd9;display:grid;place-items:center;padding:16px';
 panel.innerHTML='<form style="width:min(420px,100%);background:#183044;color:#fff;border:1px solid #8bb1c6;padding:22px;border-radius:12px;display:grid;gap:14px"><h2 style="margin:0">Conectar teléfonos y PC por número</h2><p style="margin:0">Ingresa el número que identificará al grupo. Todos los teléfonos MantPro y PC Informe KPI autorizados con ese mismo número compartirán los registros. Si el grupo existe, solicita acceso desde otro dispositivo autorizado. No se usan correos, enlaces ni códigos.</p><label>Número telefónico<input type="tel" name="phone" autocomplete="tel" required value="'+esc(phone)+'" placeholder="+56 9 1234 5678" style="width:100%;padding:12px;box-sizing:border-box"></label><small>En la nube solo se guarda un identificador cifrado del número. No compartas tus registros con equipos desconocidos.</small><p role="status" id="eecr-phone-feedback"></p><div style="display:flex;gap:10px"><button type="submit" style="padding:12px;background:#1976bd;color:white;border:0">Conectar al grupo</button><button type="button" id="eecr-phone-close" style="padding:12px">Cerrar</button></div></form>';
 document.body.append(panel);
 panel.querySelector('#eecr-phone-close').onclick=close;
 panel.querySelector('form').onsubmit=async event=>{
  event.preventDefault();const message=panel.querySelector('#eecr-phone-feedback');
  const value=panel.querySelector('[name=phone]').value.trim();
  try{
   if(!secret())throw Error('Abre primero MantPro móvil.');
   if(phone&&phone.replace(/[^0-9]/g,'')!==value.replace(/[^0-9]/g,''))throw Error('Este teléfono ya pertenece a otro grupo. No se mezclan datos entre números. Conserva su grupo actual y crea un respaldo antes de cualquier migración.');
   const previous=phone;
   phone=value;
   try{
    await call('bind_phone');
    localStorage.setItem(STORE,phone);
    close();await poll(true);
   }catch(e){
    phone=previous;
    if(e.message==='phone_already_assigned')await requestJoin(value,message);
    else throw e;
   }
  }catch(e){message.textContent='Conexión pendiente: '+e.message;}
 };
}
function dismiss(){document.querySelector('#eecr-phone-requests')?.remove();}
async function approve(request){
 const pub=await crypto.subtle.importKey('jwk',request.public_key,{name:'RSA-OAEP',hash:'SHA-256'},false,['encrypt']);
 const encrypted=await crypto.subtle.encrypt({name:'RSA-OAEP'},pub,new TextEncoder().encode(secret()));
 const c=btoa(String.fromCharCode(...new Uint8Array(encrypted)));
 const result=await call('approve_join',{requestId:request.id,ciphertext:c});
 if(!result.approved)throw Error('Esta solicitud ya no está disponible.');
}
function draw(){
 dismiss();if(!pending.length)return;
 const el=document.createElement('div');el.id='eecr-phone-requests';
 el.style.cssText='position:fixed;top:12px;left:12px;right:12px;z-index:190000;background:#163548;color:white;border:2px solid #f4b23d;border-radius:12px;padding:14px;box-shadow:0 10px 35px #0009;max-height:70vh;overflow:auto;font:14px Arial';
 el.innerHTML='<h3 style="margin:0 0 8px">Nuevo dispositivo solicita conexión</h3><p>Aprueba solo teléfonos y computadores que reconoces. El número identifica el grupo, pero no permite entrar sin autorización.</p>'+pending.map((r,i)=>'<div style="border-top:1px solid #8298a9;padding:9px 0"><b>'+esc(r.device_label||'Teléfono o computador')+'</b><p style="font-size:12px;margin:5px 0">Solicitado '+esc(new Date(r.requested_at).toLocaleString('es-CL'))+'</p><button data-action="approve" data-i="'+i+'" style="padding:9px;background:#298353;color:#fff;border:0;margin-right:7px">Autorizar equipo</button><button data-action="reject" data-i="'+i+'" style="padding:9px">Rechazar</button></div>').join('');
 document.body.append(el);
 for(const btn of el.querySelectorAll('button[data-action]'))btn.onclick=async()=>{
  btn.disabled=true;const r=pending[Number(btn.dataset.i)];
  try{if(btn.dataset.action==='approve')await approve(r);else await call('reject_join',{requestId:r.id});
   pending=pending.filter(x=>x.id!==r.id);draw();
  }catch(e){btn.disabled=false;alert('No se pudo procesar la solicitud: '+e.message);}
 };
}
async function poll(force=false){
 if(!phone||!secret()||working||(!force&&document.hidden)||!navigator.onLine)return;
 working=true;
 try{const result=await call('pending_joins');const received=Array.isArray(result.requests)?result.requests:[];
  if(JSON.stringify(received.map(x=>x.id))!==JSON.stringify(pending.map(x=>x.id))){pending=received;draw();}
 }catch(e){console.warn('EECR: autorizaciones pendientes',e.message);}
 finally{working=false;}
}
function initial(){
 const status=document.querySelector('#state');
 // El acceso queda en el panel normal de sincronización; esta banda solo aparece si falta configurar.
 if(!phone){
  const banner=document.createElement('div');banner.id='eecr-phone-prompt';
  banner.style.cssText='position:fixed;left:10px;right:10px;bottom:88px;z-index:1100;background:#153a4a;color:white;padding:9px 14px;border-radius:9px;box-shadow:0 4px 12px #0005;font:13px Arial';
  banner.innerHTML='<span>Compartir registros con otros teléfonos y PC</span> <button id="eecr-phone-activate" style="padding:7px;background:#ecad41;border:0;border-radius:4px;font-weight:bold">Configurar número</button> <button id="eecr-phone-hide" style="padding:7px">×</button>';
  document.body.append(banner);
  banner.querySelector('#eecr-phone-activate').onclick=()=>{banner.remove();openSetup();};
  banner.querySelector('#eecr-phone-hide').onclick=()=>banner.remove();
 }
 if(status)status.title='Toca para sincronizar o conectar otros teléfonos y PC por número';
 setInterval(()=>poll(false),12000);
 setInterval(()=>checkJoin(),6500);
 window.addEventListener('focus',()=>poll(true));
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll(true);});
 if(phone)setTimeout(()=>poll(true),1500);
 if(waiting)setTimeout(()=>checkJoin(),1400);
}
window.EECR_PHONE_BINDING={openSetup,poll,checkJoin,status:()=>({configured:!!phone,pending:pending.length,waiting:!!waiting})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initial,{once:true});else initial();
})();