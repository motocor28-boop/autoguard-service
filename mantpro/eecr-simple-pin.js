/* EECR: vinculación sencilla de móviles y PC a un canal existente mediante PIN temporal. */
(()=>{'use strict';
const C=window.MANTPRO_CONFIG||{},api=String(C.supabaseUrl||'').replace(/\/$/,'')+'/functions/v1/eecr-pin-sync',SECRET='eecr-device-pair-v1';
const b64=x=>btoa(String.fromCharCode(...x)),un64=x=>Uint8Array.from(atob(x),c=>c.charCodeAt(0));
let view=null;
const esc=s=>String(s??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[x]));
async function call(action,data={}){
 const r=await fetch(api,{method:'POST',cache:'no-store',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,...data})});
 const x=await r.json().catch(()=>({error:'Respuesta incorrecta'}));
 if(!r.ok||!x.ok)throw Error(({pin_expired:'PIN incorrecto, usado o vencido',too_many_attempts:'Demasiados intentos. Intenta más tarde',service_unavailable:'Servidor temporalmente no disponible'}[x.error])||x.error||'Error HTTP '+r.status);
 return x;
}
const secret=()=>localStorage.getItem(SECRET)||'';
function close(){view?.remove();view=null;}
function message(t,ok=false){const m=view?.querySelector('#eecr-pin-message');if(m){m.textContent=t;m.style.color=ok?'#7ff5ab':'#ffce87';}}
async function create(){
 try{const key=secret();if(!/^[A-Za-z0-9_-]{43}$/.test(key))throw Error('Este equipo aún no tiene un canal MantPro');
 message('Generando PIN…');
 const d=await call('create',{secret:key});const p=view?.querySelector('#eecr-pin-code');if(p)p.textContent=d.pin;
 message('Introduce este PIN en el otro equipo. Vence en 5 minutos y funciona una sola vez.',true);
 }catch(e){message(e.message);}
}
async function join(){
 const pin=view?.querySelector('#eecr-pin-value')?.value.replace(/\s/g,'')||'';
 if(!/^\d{8}$/.test(pin)){message('Introduce los ocho dígitos del PIN');return;}
 try{
 message('Autorizando canal…');
 const keys=await crypto.subtle.generateKey({name:'RSA-OAEP',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['encrypt','decrypt']);
 const pub=await crypto.subtle.exportKey('jwk',keys.publicKey);
 const result=await call('join',{pin,publicKey:pub});
 const bytes=await crypto.subtle.decrypt({name:'RSA-OAEP'},keys.privateKey,un64(result.ciphertext));
 const channel=b64(new Uint8Array(bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
 if(!/^[A-Za-z0-9_-]{43}$/.test(channel))throw Error('El PIN no contiene un canal válido');
 if(channel!==secret()){
  const rows=JSON.parse(localStorage.getItem('mantpro-records-v3')||'[]');
  const live=Array.isArray(rows)?rows.filter(x=>!String(x?.id||'').startsWith('q1-')&&x?.provenance?.kind!=='synthetic-training'&&x?.data?.provenance?.kind!=='synthetic-training'):[];
  if(live.length&&!confirm('Este equipo tiene '+live.length+' registros existentes. Se conservarán y se incorporarán al grupo del PIN. ¿Continuar?'))throw Error('La conexión se canceló; ningún registro se modificó');
 }
 await window.EECR_DEVICE_SYNC?.adoptAuthorizedChannel(channel);
 if(localStorage.getItem(SECRET)!==channel)throw Error('La versión instalada no admite la vinculación. Actualiza MantPro.');
 message('Equipo conectado. Ya comparte el canal con el otro dispositivo.',true);
 view.querySelector('#eecr-pin-value').value='';
 window.setTimeout(close,1900);
 }catch(e){message(e.message);}
}
function open(){
 if(view)return;
 view=document.createElement('div');view.id='eecr-simple-pin-dialog';
 view.style.cssText='position:fixed;inset:0;background:#04111ddc;z-index:240000;display:grid;place-items:center;padding:15px';
 view.innerHTML='<section role="dialog" aria-label="Sincronizar equipos con PIN" style="width:min(420px,100%);background:#18364a;color:#fff;padding:20px;border-radius:12px;font:15px Arial;display:grid;gap:12px;box-shadow:0 15px 40px #0009"><h2 style="margin:0">Sincronizar por PIN</h2><p style="margin:0">En un equipo pulsa <b>Generar PIN</b>. En el otro escribe esos 8 números y pulsa <b>Conectar</b>. Luego se sincronizarán automáticamente por Internet.</p><button id="eecr-pin-create" style="padding:12px">Generar PIN en este equipo</button><div id="eecr-pin-code" style="font-size:32px;letter-spacing:4px;text-align:center;color:#f4c16f;font-weight:bold" aria-live="polite"></div><input type="text" id="eecr-pin-value" inputmode="numeric" pattern="[0-9]{8}" maxlength="8" placeholder="Escribe aquí los 8 dígitos" style="padding:13px;font-size:19px;letter-spacing:3px"><button id="eecr-pin-join" style="padding:12px;background:#eeb454;color:#142d41;border:0;font-weight:bold">Conectar este equipo</button><p id="eecr-pin-message" role="status" style="min-height:20px;margin:0"></p><button id="eecr-pin-close" style="padding:10px">Cerrar</button></section>';
 document.body.append(view);
 view.querySelector('#eecr-pin-create').onclick=create;view.querySelector('#eecr-pin-join').onclick=join;view.querySelector('#eecr-pin-close').onclick=close;
}
function start(){
 window.EECR_DEVICE_SYNC && (window.EECR_DEVICE_SYNC.openPanel=open);
 const e=document.querySelector('#state');if(e){e.onclick=open;e.title='Conectar otro teléfono o PC mediante PIN';}
 const top=document.querySelector('.topbar');if(top&&!document.getElementById('eecr-pin-nav')){
  const b=document.createElement('button');b.id='eecr-pin-nav';b.type='button';b.textContent='PIN';
  b.setAttribute('aria-label','Vincular mediante PIN');b.style.cssText='border:1px solid #9ca8b4;color:white;background:#264e66;padding:8px;border-radius:6px;font-weight:bold;cursor:pointer';b.onclick=open;top.append(b);
 }
}
window.EECR_SIMPLE_PIN={open,create,join};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();