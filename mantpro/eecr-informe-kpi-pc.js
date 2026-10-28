/* MantPro PC a Informe KPI: canal cifrado por 127.0.0.1, sin usuario ni enlace. */
(()=>{
'use strict';if(/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
const host='http://127.0.0.1:8789',K='eecr-device-pair-v1',S='mantpro-records-v3';
const kinds=new Set(['job','progress','safety','walk','technician','kpi','talk_signed']);
let busy=false,good=null,problem='',configured=false;
// Convertir AES-GCM a Base64 por bloques: las fotografías superan el límite de argumentos de V8.
const b64=v=>{
  let raw='';
  for(let i=0;i<v.length;i+=8192)raw+=String.fromCharCode(...v.subarray(i,i+8192));
  return btoa(raw);
};
const ub=v=>{
  const raw=atob(v),result=new Uint8Array(raw.length);
  for(let i=0;i<raw.length;i++)result[i]=raw.charCodeAt(i);
  return result;
};
const read=()=>{try{const v=JSON.parse(localStorage.getItem(S)||'[]');return Array.isArray(v)?v:[]}catch{return []}};
const synthetic=r=>/^(q1-|demo-|test-)/.test(String(r?.id||''))||r?.provenance?.kind==='synthetic-training'||r?.data?.provenance?.kind==='synthetic-training';
const time=r=>Date.parse(r?.updatedAt||r?.at||'')||0;
async function secret(){const s=localStorage.getItem(K)||'';if(!/^[a-zA-Z0-9_-]{43}$/.test(s))throw Error('MantPro PC sin grupo');return s;}
async function aes(){const s=await secret();return crypto.subtle.importKey('raw',ub(s.replace(/-/g,'+').replace(/_/g,'/')+'='),'AES-GCM',false,['encrypt','decrypt']);}
async function encrypt(o){const k=await aes(),iv=crypto.getRandomValues(new Uint8Array(12)),d=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv},k,new TextEncoder().encode(JSON.stringify(o))));return {iv:b64(iv),data:b64(d.slice(0,-16)),tag:b64(d.slice(-16))};}
async function decrypt(p){const k=await aes(),c=ub(p.data),tag=ub(p.tag),x=new Uint8Array(c.length+tag.length);x.set(c);x.set(tag,c.length);return JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({name:'AES-GCM',iv:ub(p.iv)},k,x)));}
async function post(path,body){const r=await fetch(host+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),cache:'no-store'});const x=await r.json();if(!r.ok||x.ok!==true)throw Error(x.error||'HTTP '+r.status);return x;}
async function call(action,data={}){const x=await post('/api/relay',await encrypt({action,...data}));return decrypt(x.packet);}
function note(t){let el=document.querySelector('#eecr-informe-pc-status');if(!el){el=document.createElement('div');el.id='eecr-informe-pc-status';el.style.cssText='position:fixed;bottom:60px;right:10px;z-index:7000;background:#204658;color:white;padding:8px;border-radius:6px;font:12px Arial;max-width:300px;pointer-events:none';document.body.append(el);}el.textContent=t;}
function merge(rows){const map=new Map(read().filter(x=>x?.id).map(x=>[x.id,x]));let added=0;
for(const x of rows){if(!x?.id||!kinds.has(x.type)||synthetic(x))continue;const o=map.get(x.id);if(!o||time(x)>time(o)){map.set(x.id,o?{...o,...x}:x);added++;}}
if(added){localStorage.setItem(S,JSON.stringify([...map.values()]));window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{source:'Informe KPI',added}}));window.MANTPRO?.render?.();}return added;}
async function sync(){if(busy)return;busy=true;try{
if(!configured){
 let linked=false;
 try{await post('/api/browser-pair',{secret:await secret()});linked=true;}
 catch(error){throw Error('Informe KPI local no disponible o pertenece a otro grupo. No se modificaron registros.');}
 if(linked)configured=true;
}
let b=[],size=0,pending=0,transferred=0;
async function send(){if(b.length){const ans=await call('push',{records:b});if(!ans.ok)throw Error('Rechazado');transferred+=b.length;b=[];size=0;}}
for(const r of read()){if(!r?.id||!kinds.has(r.type)||synthetic(r))continue;const n=JSON.stringify(r).length;if(n>900000){pending++;continue;}if(b.length>=4||size+n>600000)await send();b.push(r);size+=n;}await send();
let all=[],offset=0,done=false;for(let i=0;i<3200;i++){const x=await call('pull',{offset});if(!x.ok||!Array.isArray(x.records))throw Error('Recepción inválida');all.push(...x.records);if(x.nextOffset===null){done=true;break;}if(x.nextOffset<=offset)throw Error('Cursor inválido');offset=x.nextOffset;}
if(!done)throw Error('Recepción incompleta');
const received=merge(all);good=new Date().toISOString();problem='';note((pending?'Informe KPI PARCIAL':'Informe KPI receptor respondió')+' · '+transferred+' enviados · '+received+' recibidos'+(pending?' · '+pending+' registros demasiado grandes, conservados en PC':''));return {ok:!pending,transferred,received,pending};
}catch(e){configured=false;problem=e.message||String(e);note('Informe KPI pendiente · '+problem);return {ok:false,error:problem};}finally{busy=false;}}
function start(){setTimeout(sync,1500);setInterval(()=>{if(!document.hidden)sync();},20000);window.addEventListener('focus',sync);window.addEventListener('online',sync);window.addEventListener('mantpro-sync-complete',()=>setTimeout(sync,800));}
window.EECR_INFORME_KPI_PC={sync,status:()=>({good,problem})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();