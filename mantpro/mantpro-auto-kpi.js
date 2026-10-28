/* MANTPRO móvil → Informe KPI EHS: sincronización local incremental, sin Internet. */
(()=>{'use strict';
if(!/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
const IPKEY='hepi-kpi-local-ip-v2',ORIGIN=ip=>'http://'+ip+':8765';
const TYPES=new Set(['job','progress','safety','walk','technician','kpi','talk_signed']);
let ip=localStorage.getItem(IPKEY)||'',win=null,direct=false,connected=false,busy=false,lastOK=null,lastError='',seq=0;
const requests=new Map(),recent=new Map();
const validIP=s=>/^(?:\d{1,3}\.){3}\d{1,3}$/.test(s)&&s.split('.').every(t=>Number(t)<256);
const real=r=>r&&typeof r.id==='string'&&r.id.length>=8&&TYPES.has(r.type)&&!(/^(q1-|demo-|test-)/i.test(r.id))&&r.simulation!==true&&r.demo!==true&&r.data?.simulation!==true&&r.provenance?.kind!=='synthetic-training'&&r.data?.provenance?.kind!=='synthetic-training';
function records(){try{const a=window.MANTPRO?.records?.()||JSON.parse(localStorage.getItem('mantpro-records-v3')||'[]');return Array.isArray(a)?a.filter(real):[]}catch{return[]}}
function state(s){const x=document.getElementById('hepi-direct-state');if(x)x.textContent=s;}
function panel(){
 const app=document.querySelector('#app');if(!app||document.getElementById('hepi-direct-box'))return;
 const section=document.createElement('section');section.id='hepi-direct-box';section.style.cssText='margin:10px 4px;padding:15px;background:#15394e;border-radius:10px;color:white;border:1px solid #719aad;font:14px Arial';
 section.innerHTML='<h3>Informe KPI · SIN INTERNET</h3><p>Conecta el computador a la zona Wi-Fi del teléfono. Se enviarán OT y fotografías nuevas automáticamente mientras MantPro esté abierto.</p><button id="hepi-direct-start" style="width:100%;padding:14px;background:#eeb74e;border:0;border-radius:6px;font-weight:bold">Conectar y sincronizar</button><button id="hepi-direct-change" style="width:100%;padding:8px;margin-top:7px;background:#23475d;color:white;border:1px solid #97b3c5">Cambiar computador</button><p id="hepi-direct-state">Sin conexión local. Los registros permanecen en el teléfono.</p>';
 app.prepend(section);
 section.querySelector('#hepi-direct-start').onclick=connect;
 section.querySelector('#hepi-direct-change').onclick=()=>{ip='';connected=false;direct=false;localStorage.removeItem(IPKEY);state('Dirección anterior olvidada. Pulsa Conectar y sincronizar.')};
}
window.addEventListener('message',e=>{
 if(!win||e.source!==win||e.origin!==ORIGIN(ip)||!e.data?.hepiOffline)return;
 if(e.data.event==='ready'){connected=true;state('PC detectado. Transfiriendo registros…');sync();return;}
 if(e.data.event==='response'){const job=requests.get(e.data.id);if(job){requests.delete(e.data.id);clearTimeout(job.timer);if(e.data.error)job.reject(Error(e.data.error));else job.resolve(e.data.data);}}
});
async function request(action,records){
 if(direct){const endpoint=action==='manifest'?'/manifest':'/ingest';
  const options={mode:'cors',cache:'no-store',targetAddressSpace:'local',signal:AbortSignal.timeout(20000)};
  if(action==='send'){options.method='POST';options.headers={'Content-Type':'application/json'};options.body=JSON.stringify({records});}
  const result=await fetch(ORIGIN(ip)+endpoint,options),data=await result.json();
  if(!result.ok||!data.ok)throw Error(data.error||'Comunicación local no disponible');return data;}
 if(!win||win.closed)throw Error('Abre nuevamente la conexión del PC');
 const id='req-'+(++seq);
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{requests.delete(id);reject(Error('PC sin respuesta'))},23000);
 requests.set(id,{resolve,reject,timer});win.postMessage({hepiOffline:true,id,action,records},ORIGIN(ip));});
}
function connect(){
 if(!ip){const answer=prompt('Introduce la dirección IP del PC, mostrada en Informe KPI. Solo se configura una vez.','');if(answer===null)return;ip=answer.trim();}
 if(!validIP(ip)){state('Dirección IP incorrecta. Comprueba la IP de Informe KPI.');ip='';return;}
 localStorage.setItem(IPKEY,ip);
 if(direct){connected=true;sync();return;}
 if(win&&!win.closed){connected=true;sync();return;}
 win=window.open(ORIGIN(ip)+'/','HEPI_KPI_OFFLINE','width=520,height=660');
 if(!win){state('El navegador bloqueó la ventana local. Permite ventanas emergentes para MantPro.');return;}
 state('Conectando con Informe KPI…');
}
async function sync(){
 if(busy||!connected)return;busy=true;let queued=0,pending=0,oversized=0;
 try{
  const manifest=(await request('manifest')).manifest||{},newRows=[];
  for(const r of records()){
   const bytes=new TextEncoder().encode(JSON.stringify(r)).length,stamp=String(r.updatedAt||r.at||'');
   if(manifest[r.id]?.stamp===stamp&&manifest[r.id]?.bytes===bytes)continue;
   if(bytes>10*1024*1024){oversized++;continue;}
   const mark=r.id+'|'+stamp+'|'+bytes;
   if(recent.has(mark)&&Date.now()-recent.get(mark)<180000){pending++;continue;}
   newRows.push({r,mark,bytes});
  }
  let batch=[],n=0;
  async function flush(){if(!batch.length)return;const answer=await request('send',batch.map(x=>x.r));if(!answer?.queued)throw Error('PC no confirmó el envío');
   for(const x of batch)recent.set(x.mark,Date.now());queued+=batch.length;batch=[];n=0;
   state('Enviado al PC: '+queued+' registros. Esperando incorporación en Informe KPI…');}
  for(const x of newRows){if(batch.length>=6||n+x.bytes>9*1024*1024)await flush();batch.push(x);n+=x.bytes;}await flush();
  lastOK=new Date();lastError='';
  state(queued||pending||oversized?'PC recibió: '+queued+' · pendientes: '+pending+' · fotos grandes: '+oversized+'\nSe confirmará al incorporarlos en Informe KPI.':'SINCRONIZACIÓN COMPLETA: '+records().length+' registros incorporados y confirmados por el PC.');
 }catch(e){lastError=e.message||String(e);state('Transferencia pendiente: '+lastError+'. No se borró ninguna OT.');}
 finally{busy=false;}
}
function init(){
 const app=document.querySelector('#app')||document.body;new MutationObserver(()=>{if(!document.getElementById('hepi-direct-box'))panel();}).observe(app,{childList:true});panel();
 if(validIP(ip)){setTimeout(async()=>{try{const r=await fetch(ORIGIN(ip)+'/manifest',{mode:'cors',cache:'no-store',targetAddressSpace:'local',signal:AbortSignal.timeout(3500)});if(r.ok&&(await r.json()).ok){direct=true;connected=true;sync();}}catch{}},2200);}
 setInterval(()=>{if(connected)sync();},22000);
 document.addEventListener('visibilitychange',()=>{if(!document.hidden&&connected)sync()});
}
window.MANTPRO_KPI_LOCAL={connect,sync,status:()=>({connected,direct,lastOK,lastError})};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();