/* EECR: autorizaciones desde el telefono usando numero identificador, sin enlaces. */
(()=>{
'use strict';
if(!/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
const API='https://gecrjlkfrcrlsjhanfjz.supabase.co/functions/v1/eecr-phone-enrolment';
const STORE='eecr-pair-phone-v1';
const secret=()=>localStorage.getItem('eecr-device-pair-v1')||'';
let phone=localStorage.getItem(STORE)||'',pending=[],working=false,panel=null;
const esc=t=>String(t??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[x]));
async function call(action,extra={}){
 const response=await fetch(API,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,phone,secret:secret(),...extra})});
 const result=await response.json();
 if(!response.ok||!result.ok)throw Error(result.error||'Error de comunicación');
 return result;
}
function close(){panel?.remove();panel=null;}
function openSetup(){
 close();panel=document.createElement('div');panel.id='eecr-phone-setup';
 panel.style.cssText='position:fixed;inset:0;z-index:210000;background:#09131dd9;display:grid;place-items:center;padding:16px';
 panel.innerHTML='<form style="width:min(420px,100%);background:#183044;color:#fff;border:1px solid #8bb1c6;padding:22px;border-radius:12px;display:grid;gap:14px"><h2 style="margin:0">Conectar Informe KPI por número</h2><p style="margin:0">Ingresa una sola vez el número de este teléfono. Los computadores podrán solicitar acceso usando el mismo número, y tú aprobarás cada equipo desde aquí. No se enviarán SMS ni se utilizará el número como contraseña.</p><label>Número telefónico<input type="tel" name="phone" autocomplete="tel" required value="'+esc(phone)+'" placeholder="+56 9 1234 5678" style="width:100%;padding:12px;box-sizing:border-box"></label><small>En la nube solo se guarda un identificador cifrado del número. No compartas tus registros con equipos desconocidos.</small><p role="status" id="eecr-phone-feedback"></p><div style="display:flex;gap:10px"><button type="submit" style="padding:12px;background:#1976bd;color:white;border:0">Guardar número</button><button type="button" id="eecr-phone-close" style="padding:12px">Cerrar</button></div></form>';
 document.body.append(panel);
 panel.querySelector('#eecr-phone-close').onclick=close;
 panel.querySelector('form').onsubmit=async event=>{
  event.preventDefault();const message=panel.querySelector('#eecr-phone-feedback');
  const value=panel.querySelector('[name=phone]').value.trim();
  try{if(!secret())throw Error('Abre primero la sincronización del teléfono.');const old=phone;phone=value;
   try{await call('bind_phone');}catch(e){phone=old;throw e;}
   localStorage.setItem(STORE,phone);close();await poll(true);
  }catch(e){message.textContent='No se guardó el número: '+e.message;}
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
 el.innerHTML='<h3 style="margin:0 0 8px">Informe KPI solicita conexión</h3><p>Aprueba solamente computadores que reconoces. No requiere copiar enlaces ni ingresar códigos.</p>'+pending.map((r,i)=>'<div style="border-top:1px solid #8298a9;padding:9px 0"><b>'+esc(r.device_label||'Informe KPI Windows')+'</b><p style="font-size:12px;margin:5px 0">Solicitado '+esc(new Date(r.requested_at).toLocaleString('es-CL'))+'</p><button data-action="approve" data-i="'+i+'" style="padding:9px;background:#298353;color:#fff;border:0;margin-right:7px">Autorizar equipo</button><button data-action="reject" data-i="'+i+'" style="padding:9px">Rechazar</button></div>').join('');
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
  banner.innerHTML='<span>Conectar Informe KPI en varios computadores</span> <button id="eecr-phone-activate" style="padding:7px;background:#ecad41;border:0;border-radius:4px;font-weight:bold">Configurar número</button> <button id="eecr-phone-hide" style="padding:7px">×</button>';
  document.body.append(banner);
  banner.querySelector('#eecr-phone-activate').onclick=()=>{banner.remove();openSetup();};
  banner.querySelector('#eecr-phone-hide').onclick=()=>banner.remove();
 }
 if(status)status.title='Toca para sincronizar o vincular Informe KPI por número';
 setInterval(()=>poll(false),12000);
 window.addEventListener('focus',()=>poll(true));
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll(true);});
 if(phone)setTimeout(()=>poll(true),1500);
}
window.EECR_PHONE_BINDING={openSetup,poll,status:()=>({configured:!!phone,pending:pending.length})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initial,{once:true});else initial();
})();