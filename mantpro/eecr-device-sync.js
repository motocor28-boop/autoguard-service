/* EECR/MantPro: canal de sincronización privada sin correo.
   Primer enlace dispositivo a dispositivo por clave aleatoria de 256 bits;
   posteriormente envío/recepción automática vía HTTPS, incluso con hotspot Android. */
(()=>{
  'use strict';
  const C=window.MANTPRO_CONFIG||{};
  const STORE='mantpro-records-v3',PAIR='eecr-device-pair-v1',ACK='eecr-device-ack-v1',CONFLICT='eecr-device-conflicts-v1',SINCE='eecr-device-last-pull-v1';
  const API=String(C.supabaseUrl||'').replace(/\/$/,'')+'/functions/v1/eecr-device-sync';
  const isMobile=/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent);
  const $$=s=>document.querySelector(s);
  const keyPattern=/^[a-zA-Z0-9_-]{43}$/;
  const safeRead=(name,defaultValue)=>{try{const val=JSON.parse(localStorage.getItem(name)||'null');return val===null?defaultValue:val;}catch{return defaultValue;}};
  const localRecords=()=>{const v=safeRead(STORE,[]);return Array.isArray(v)?v:[];};
  const stamp=x=>String(x?.updatedAt||x?.at||'');
  const status=(s,kind='')=>{const node=$$('#state');if(node){node.textContent=s;node.className='sync-state '+kind;}};
  let secret=localStorage.getItem(PAIR)||'',inFlight=false,panel=null,lastOk=null,errorCount=0;
  if(secret&&!keyPattern.test(secret))secret='';
  function makeSecret(){
    const bytes=new Uint8Array(32);crypto.getRandomValues(bytes);
    return btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');
  }
  function persistSecret(value){
    if(!keyPattern.test(value))throw Error('El enlace de emparejamiento no es válido.');
    if(secret&&secret!==value)throw Error('Este dispositivo ya pertenece a otro canal. Conserva el canal actual o recupera primero un respaldo.');
    localStorage.setItem(PAIR,value);secret=value;
    localStorage.removeItem(ACK);localStorage.removeItem(SINCE); // Canal nuevo: traer todo antes de sincronizar.
  }
  function pairingUrl(){return location.origin+location.pathname+'#eecrDevice='+encodeURIComponent(secret);}
  function escapeHtml(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  async function call(action,other={}){
    if(!navigator.onLine)throw Error('Sin Internet; los registros siguen en el equipo.');
    if(!secret)throw Error('El dispositivo aún no está emparejado.');
    const response=await fetch(API,{
      method:'POST',mode:'cors',cache:'no-store',
      headers:{'Content-Type':'application/json','apikey':C.supabaseAnonKey||''},
      body:JSON.stringify({action,secret,...other})
    });
    let data={};try{data=await response.json();}catch{}
    if(!response.ok||!data.ok)throw Error(String(data.error||'Error del servidor: '+response.status));
    return data;
  }
  async function pull(){
    let offset=0,received=[],watermark=null;
    const last=localStorage.getItem(SINCE);
    const since=last&&Number.isFinite(Date.parse(last))?new Date(Date.parse(last)-5000).toISOString():null;
    for(let page=0;page<2000;page++){
      const res=await call('pull',{since,offset,limit:8});
      if(!Array.isArray(res.records))throw Error('Respuesta de sincronización inválida');
      received.push(...res.records.filter(x=>x&&typeof x.id==='string'));
      if(res.watermark&&(!watermark||Date.parse(res.watermark)>Date.parse(watermark)))watermark=res.watermark;
      if(res.nextOffset===null)return {records:received,watermark};
      if(!Number.isInteger(res.nextOffset)||res.nextOffset<=offset)throw Error('Cursor sin avance');
      offset=res.nextOffset;
    }
    throw Error('Historial demasiado extenso para una sola sincronización.');
  }
  function rememberConflict(old,newRecord){
    const arr=safeRead(CONFLICT,[]);
    if(!Array.isArray(arr))throw Error('Historial de conflictos inválido');
    if(arr.some(x=>x.id===old.id&&x.localUpdatedAt===stamp(old)))return;
    arr.push({id:old.id,localUpdatedAt:stamp(old),cloudUpdatedAt:stamp(newRecord),savedAt:new Date().toISOString(),local:old});
    // Nunca borrar un conflicto si no es posible guardar su respaldo local.
    localStorage.setItem(CONFLICT,JSON.stringify(arr));
  }
  function merge(cloud,ack){
    const existing=localRecords(),map=new Map(existing.map(x=>[x.id,x]));
    let changed=false,conflicts=0;
    for(const remote of cloud){
      const old=map.get(remote.id);
      if(!old){map.set(remote.id,{...remote,dirty:false,synced:true});changed=true;ack[remote.id]=stamp(remote);continue;}
      const newer=Date.parse(stamp(remote))||0,previous=Date.parse(stamp(old))||0;
      if(newer>previous){
        if(old.dirty){rememberConflict(old,remote);conflicts++;}
        map.set(remote.id,{...remote,dirty:false,synced:true});changed=true;ack[remote.id]=stamp(remote);
      }else if(newer===previous){
        ack[remote.id]=stamp(old);
        if(old.dirty||!old.synced){map.set(old.id,{...old,dirty:false,synced:true});changed=true;}
      }
    }
    if(changed){
      localStorage.setItem(STORE,JSON.stringify([...map.values()]));
      window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{deviceSync:true,fromCloud:true}}));
      if(!document.querySelector('input:focus,textarea:focus,select:focus'))window.MANTPRO?.render?.();
    }
    localStorage.setItem(ACK,JSON.stringify(ack));
    return conflicts;
  }
  async function push(){
    const all=localRecords(),ack=safeRead(ACK,{}),send=all.filter(x=>x&&x.id&&ack[x.id]!==stamp(x));
    let batch=[],size=0,uploaded=0,oversized=0;
    async function flush(){
      if(!batch.length)return;
      const result=await call('push',{records:batch});
      uploaded+=Number(result.accepted)||0;
      batch=[];size=0;
    }
    for(const row of send){
      const bytes=JSON.stringify(row).length;
      if(bytes>1_850_000){oversized++;continue;} // El original permanece guardado.
      if(batch.length>=12||size+bytes>1_850_000)await flush();
      batch.push(row);size+=bytes;
    }
    await flush();
    return {uploaded,oversized};
  }
  async function sync(){
    if(inFlight)return;
    if(!secret){status('Vinculación local pendiente','warn');return;}
    if(!navigator.onLine){status('Sin Internet · guardado local','warn');return;}
    inFlight=true;
    try{
      status('Sincronizando…');
      const up=await push();
      const ack=safeRead(ACK,{});
      const pulled=await pull();
      const conflicts=merge(pulled.records,ack);
      if(pulled.watermark)localStorage.setItem(SINCE,pulled.watermark);
      lastOk=new Date().toISOString();errorCount=0;
      const pending=localRecords().filter(x=>ack[x.id]!==stamp(x)).length;
      if(up.oversized||conflicts||pending)status('Sincronizado parcialmente · revisar '+(pending+up.oversized+conflicts),'warn');
      else status('Sincronizado','ok');
      window.dispatchEvent(new CustomEvent('mantpro-sync-complete',{detail:{count:localRecords().length,conflicts,pending}}));
      return {ok:!pending&&!conflicts&&!up.oversized,up,conflicts,pending};
    }catch(e){
      errorCount++;status('Sincronización pendiente · registros seguros','warn');
      console.warn('EECR conexión pendiente:',e.message);
      return {ok:false,error:e.message};
    }finally{inFlight=false;}
  }
  function close(){panel?.remove();panel=null;}
  function openPanel(){
    if(panel)return;
    panel=document.createElement('div');
    panel.style.cssText='position:fixed;inset:0;z-index:200000;background:#0c1420d9;display:grid;place-items:center;padding:16px;overflow:auto';
    panel.innerHTML='<section style="width:min(440px,100%);color:#eaf1fb;background:#192939;border:1px solid #607688;border-radius:16px;padding:22px;font:15px Arial,sans-serif;display:grid;gap:13px">'+
      '<h2 style="margin:0;font-size:21px">Sincronización automática EECR</h2>'+
      (isMobile?'<p style="margin:0">Conecta Informe KPI por número de teléfono y autoriza cada computador desde este equipo. Después la sincronización es automática con Internet o hotspot.</p>':'<p style="margin:0">Sincronización privada, automática con Internet o hotspot.</p>')+
      (secret?'<p style="margin:0;color:#9ee0bd">Este dispositivo tiene un canal privado configurado.</p>'+
        (isMobile?'':'<button id="eecr-copy-pair" style="padding:12px">Copiar enlace para el otro dispositivo</button><button id="eecr-share-pair" style="padding:12px">Compartir enlace</button>'):
        (!isMobile?'<button id="eecr-create-pair" style="padding:12px;background:#f9a04a;color:#1c1c1c;border:0;border-radius:5px;font-weight:bold">Preparar sincronización del PC</button>':
        '<p style="margin:0">Abre en este teléfono el enlace enviado desde el computador, o pega aquí el enlace recibido.</p>'+
        '<input id="eecr-paste-pair" placeholder="Pegar enlace o clave de emparejamiento" style="width:100%;padding:10px;box-sizing:border-box">'+
        '<button id="eecr-use-pair" style="padding:12px">Conectar este teléfono</button>'))+
      (isMobile?'<button id="eecr-phone-setup-button" style="padding:10px">Conectar Informe KPI por número</button>':'')+ 
      '<button id="eecr-run-sync" style="padding:10px">Comprobar sincronización</button>'+
      '<div id="eecr-pair-feedback" style="font-size:13px;line-height:1.5" role="status"></div>'+
      '<p style="font-size:12px;margin:0;color:#cad4df">Mantén privado el enlace: permite acceder a los datos de mantenimiento. No borres el almacenamiento del navegador ni desinstales sin un respaldo JSON.</p>'+
      '<button id="eecr-close-pair" style="padding:10px;background:transparent;border:1px solid #728496;color:inherit">Cerrar</button></section>';
    document.body.append(panel);
    const $=id=>panel.querySelector('#'+id),feedback=message=>{$('eecr-pair-feedback').textContent=message;};
    $('eecr-close-pair').onclick=close;
    if($('eecr-phone-setup-button'))$('eecr-phone-setup-button').onclick=()=>{close();window.EECR_PHONE_BINDING?.openSetup?.();};
    if($('eecr-create-pair'))$('eecr-create-pair').onclick=()=>{
      try{persistSecret(makeSecret());close();openPanel();sync();}
      catch(e){feedback(e.message);}
    };
    if($('eecr-use-pair'))$('eecr-use-pair').onclick=()=>{
      try{const raw=$('eecr-paste-pair').value.trim();let val=raw;
        if(raw.startsWith('https://'))val=new URL(raw).hash.replace(/^#eecrDevice=/,'').split('&')[0];
        persistSecret(decodeURIComponent(val));close();openPanel();sync();
      }catch(e){feedback('No se pudo conectar: '+e.message);}
    };
    if($('eecr-copy-pair'))$('eecr-copy-pair').onclick=async()=>{
      try{await navigator.clipboard.writeText(pairingUrl());feedback('Enlace copiado. Ábrelo en Chrome del teléfono; no necesitas correo.');}
      catch(e){feedback('No se pudo copiar automáticamente: '+e.message);}
    };
    if($('eecr-share-pair'))$('eecr-share-pair').onclick=async()=>{
      try{if(navigator.share)await navigator.share({title:'Vinculación privada EECR',url:pairingUrl()});
        else{await navigator.clipboard.writeText(pairingUrl());feedback('Enlace copiado: compártelo de forma privada.');}
      }catch(e){feedback(e.message);}
    };
    $('eecr-run-sync').onclick=async()=>{const r=await sync();feedback(r?.ok?'Teléfono y PC conectados con la nube privada.':('Sincronización pendiente: '+(r?.error||'revisar datos pendientes')));};
  }
  function acceptLink(){
    const params=new URLSearchParams(location.hash.replace(/^#/,''));
    const incoming=params.get('eecrDevice');
    if(!incoming)return;
    // Retirar el fragmento para no copiar accidentalmente la clave durante navegación.
    history.replaceState(null,'',location.pathname+location.search);
    try{
      persistSecret(incoming);
      window.setTimeout(()=>{sync();openPanel();},500);
    }catch(e){
      window.setTimeout(()=>{openPanel();const target=panel?.querySelector('#eecr-pair-feedback');if(target)target.textContent=e.message;},500);
    }
  }
  function init(){
    try{
      acceptLink();
      if(!secret){persistSecret(makeSecret());}
      const top=$$('#state');
      if(top){top.onclick=openPanel;}
      status(secret?'Preparando sincronización…':'Vincular sin correo','warn');
      window.addEventListener('online',sync);
      window.addEventListener('focus',sync);
      document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
      window.addEventListener('mantpro-records-changed',()=>{if(secret)window.setTimeout(sync,650);});
      window.setInterval(()=>{if(!document.hidden)sync();},20000);
      if(secret)sync();
    }catch(e){status('Vinculación pendiente · datos locales seguros','warn');console.warn(e);}
  }
  window.EECR_DEVICE_SYNC={sync,openPanel,hasPair:()=>!!secret,lastSuccess:()=>lastOk};
  window.EECR_DEVICE_SYNC_BOOTING=false;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();