/* MantPro móvil: comunicación cifrada con Informe KPI por el hotspot, sin Internet. */
(()=>{
'use strict';
if(!/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
const HOST='eecr-lan-ip-v1',SECRET='eecr-device-pair-v1',DATA='mantpro-records-v3';
const TYPES=new Set(['job','progress','safety','walk','technician','kpi','talk_signed']);
const synthetic=r=>/^(q1-|eecr-demo-|demo-|test-)/i.test(String(r?.id||''))||r?.provenance?.kind==='synthetic-training'||r?.data?.provenance?.kind==='synthetic-training';
const records=()=>{try{const v=JSON.parse(localStorage.getItem(DATA)||'[]');return Array.isArray(v)?v:[]}catch{return []}};
let win=null,address='',busy=false,done=false,at='',seq=0,timer=null;const pending=new Map();
const b64=x=>btoa(String.fromCharCode(...x));
const from64=x=>Uint8Array.from(atob(x),v=>v.charCodeAt(0));
const stamp=x=>Date.parse(x?.updatedAt||x?.at||'')||0;
async function key(){const s=localStorage.getItem(SECRET)||'';if(!/^[A-Za-z0-9_-]{43}$/.test(s))throw Error('Primero vincula el grupo de MantPro');return crypto.subtle.importKey('raw',from64(s.replace(/-/g,'+').replace(/_/g,'/')+'='),'AES-GCM',false,['encrypt','decrypt']);}
async function seal(obj){const k=await key(),iv=crypto.getRandomValues(new Uint8Array(12));const v=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},k,new TextEncoder().encode(JSON.stringify(obj))));return {iv:b64(iv),data:b64(v.slice(0,-16)),tag:b64(v.slice(-16))};}
async function unseal(p){const k=await key(),iv=from64(p.iv),data=from64(p.data),tag=from64(p.tag),all=new Uint8Array(data.length+tag.length);all.set(data);all.set(tag,data.length);return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv},k,all)));}
async function call(action,rest={}){
 if(!win||win.closed)throw Error('La ventana Wi-Fi está cerrada');
 const requestId='eecr-'+(++seq),packet=await seal({action,...rest});
 return new Promise((resolve,reject)=>{const timeout=setTimeout(()=>{pending.delete(requestId);reject(Error('El PC no respondió'))},12000);
 pending.set(requestId,{resolve,reject,timeout});try{win.postMessage({eecrLanRequest:true,requestId,packet},address);}catch(e){clearTimeout(timeout);pending.delete(requestId);reject(e);}
 });
}
function state(message){const el=document.querySelector('#eecr-lan-state');if(el)el.textContent=message;}
function merge(remote){
 const previous=records(),all=new Map(previous.filter(x=>x?.id).map(x=>[x.id,x]));let changed=0,conflicts=0;
 for(const r of remote){if(!r||!r.id||!TYPES.has(r.type)||synthetic(r))continue;
 const old=all.get(r.id);if(!old){all.set(r.id,r);changed++;}else if(stamp(r)>stamp(old)){all.set(r.id,{...old,...r});changed++;}else if(stamp(r)===stamp(old)&&JSON.stringify(r)!==JSON.stringify(old)){conflicts++;}}
 if(changed){localStorage.setItem(DATA,JSON.stringify([...all.values()]));window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{source:'wifi-directo',changed}}));window.MANTPRO?.render?.();}
 return {changed,conflicts};
}
async function sync(){
 if(busy||!win||win.closed)return false;busy=true;
 try{state('Wi-Fi directo: sincronizando…');let sent=0,skipped=0,part=[],size=0;
 async function flush(){if(!part.length)return;const r=await call('push',{records:part});sent+=r.accepted||0;skipped+=r.skipped||0;part=[];size=0;}
 for(const r of records().filter(x=>x?.id&&TYPES.has(x.type)&&!synthetic(x))){const n=JSON.stringify(r).length;
 if(n>1000000){skipped++;continue;}if(part.length>=8||size+n>1250000)await flush();part.push(r);size+=n;}await flush();
 let offset=0,remote=[];
 for(let i=0;i<3200;i++){const r=await call('pull',{offset});if(!Array.isArray(r.records))throw Error('Datos de recepción incorrectos');remote.push(...r.records);if(r.nextOffset===null)break;if(r.nextOffset<=offset)throw Error('Paginación incorrecta');offset=r.nextOffset;}
 const result=merge(remote);at=new Date().toISOString();state('Wi-Fi directo: '+(skipped||result.conflicts?'PARCIAL':'correcto')+' · recibidos '+result.changed+' · pendientes '+(skipped+result.conflicts));return {ok:!skipped&&!result.conflicts,sent,received:result.changed};
 }catch(e){state('Wi-Fi directo pendiente: '+(e.message||e));return false;}finally{busy=false;}
}
window.addEventListener('message',async e=>{
 if(!win||e.source!==win||e.origin!==address)return;
 if(e.data?.eecrLanReady){if(!done){done=true;sync();}return;}
 if(!e.data?.eecrLanReply)return;
 const t=pending.get(e.data.requestId);if(!t)return;clearTimeout(t.timeout);pending.delete(e.data.requestId);
 try{if(e.data.error)throw Error(e.data.error);const x=await unseal(e.data.packet);if(!x.ok)throw Error(x.error||'Operación rechazada');t.resolve(x);}catch(err){t.reject(err);}
});
function connect(){
 const original=localStorage.getItem(HOST)||'';
 const answer=prompt('Dirección Wi-Fi del computador (visible en Informe KPI). Introduce solo la IP:',original);
 if(answer===null)return;const ip=answer.trim();if(!/^(?:\d{1,3}\.){3}\d{1,3}$/.test(ip)||ip.split('.').some(x=>+x>255)){state('IP del computador no válida');return;}
 localStorage.setItem(HOST,ip);address='http://'+ip+':8789';done=false;
 win=window.open(address+'/','EECR_WiFi','noopener=no');
 if(!win){state('Permite abrir ventanas desde MantPro en el navegador');return;}
 state('Conectando al PC '+ip+'…');
 if(!timer)timer=setInterval(()=>{if(win&&!win.closed&&!document.hidden)sync();},26000);
}
function start(){
 const bar=document.createElement('div');bar.style.cssText='position:fixed;left:9px;right:9px;bottom:93px;z-index:12000;padding:9px;background:#163b50;color:white;border-radius:9px;font:13px Arial;display:flex;gap:8px;align-items:center;box-shadow:0 2px 12px #0006';
 bar.innerHTML='<button id="eecr-lan-connect" type="button" style="background:#f2b33b;color:#122c42;padding:10px;border:0;border-radius:6px;font-weight:700">Wi-Fi directo con PC</button><span id="eecr-lan-state">Sincronización local disponible</span><button id="eecr-lan-close" type="button">×</button>';
 document.body.append(bar);
 bar.querySelector('#eecr-lan-connect').onclick=connect;bar.querySelector('#eecr-lan-close').onclick=()=>bar.remove();
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
window.EECR_LAN_WIFI={connect,sync,status:()=>({connected:!!win&&!win.closed,lastSuccess:at})};
})();