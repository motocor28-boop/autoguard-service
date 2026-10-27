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
  const isDemo=x=>!!x&&(String(x.id||'').startsWith('q1-')||x.provenance?.kind==='synthetic-training'||x.data?.provenance?.kind==='synthetic-training');
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
      received.push(...res.records.filter(x=>x&&typeof x.id==='string'&&!isDemo(x)));
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
    const existing=localRecords(),map=new Map(existing.filter(x=>!isDemo(x)).map(x=>[x.id,x]));
    const retired=existing.length-map.size;
    let changed=retired>0,conflicts=0;
    for(const remote of cloud){
      if(isDemo(remote))continue;
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
    const all=localRecords(),ack=safeRead(ACK,{}),send=all.filter(x=>x&&x.id&&!isDemo(x)&&ack[x.id]!==stamp(x));
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
      const pending=localRecords().filter(x=>!isDemo(x)&&ack[x.id]!==stamp(x)).length;
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
  async function channelCode(){
    if(!secret||!keyPattern.test(secret))return 'SIN CANAL';
    try{
      const data=Uint8Array.from(atob(secret.replace(/-/g,'+').replace(/_/g,'/')+'='),c=>c.charCodeAt(0));
      const hash=new Uint8Array(await crypto.subtle.digest('SHA-256',data));
      return Array.from(hash.slice(0,6),x=>x.toString(16).padStart(2,'0')).join('');
    }catch{return 'NO IDENTIFICADO';}
  }
  function localTotals(){
    const list=localRecords().filter(x=>!isDemo(x)),kinds={};
    let photos=0;
    for(const row of list){
      kinds[row.type]=(kinds[row.type]||0)+1;
      photos+=Array.isArray(row.data?.stagePhotos)?row.data.stagePhotos.filter(x=>x?.dataUrl||x?.src).length:0;
      if(row.photo)photos++;
    }
    return {total:list.length,jobs:kinds.job||0,progress:kinds.progress||0,photos};
  }
  function checkBridge(){
    if(isMobile)return 'Informe KPI: no corresponde al teléfono';
    const bridge=window.EECR_INFORME_KPI_PC?.status?.();
    if(!bridge)return 'Informe KPI: puente PC no cargado';
    if(bridge.problem)return 'Informe KPI: pendiente · '+String(bridge.problem).slice(0,130);
    if(bridge.good)return 'Informe KPI: enlace local activo desde '+new Date(bridge.good).toLocaleTimeString('es-CL');
    return 'Informe KPI: recepción no confirmada';
  }
  async function refreshDiagnostics(){
    const box=panel?.querySelector('#eecr-channel-check');if(!box)return;
    const code=await channelCode(),counts=localTotals();
    if(!panel||!box.isConnected)return;
    box.textContent='Canal de este equipo: '+code+' · Registros locales: '+counts.total+' · OT: '+counts.jobs+' · Avances: '+counts.progress+' · Fotos por etapa: '+counts.photos+'\n'+checkBridge();
  }
  function close(){panel?.remove();panel=null;}
  function openPanel(){
    if(panel)return;
    panel=document.createElement('div');
    panel.style.cssText='position:fixed;inset:0;z-index:200000;background:#081723df;display:grid;place-items:center;padding:16px';
    panel.innerHTML='<section style="background:#1a3547;border:1px solid #6992a8;border-radius:12px;color:white;width:min(430px,100%);padding:22px;font:15px Arial;display:grid;gap:14px">'+
      '<h2 style="margin:0">Sincronización automática MantPro</h2>'+
      '<p style="margin:0">Los registros se transmiten por Internet y se conservan en el dispositivo si la conexión falla.</p>'+
      '<p style="margin:0">'+(secret?'Canal de datos configurado.':'Este dispositivo todavía no tiene un canal de datos asociado.')+'</p>'+
      '<p style="margin:0">Última transferencia correcta: <b id="eecr-last-ok">'+(lastOk?new Date(lastOk).toLocaleString('es-CL'):'Sin confirmar')+'</b></p>'+
      '<button type="button" id="eecr-check-now" style="padding:12px">Verificar entrega</button>'+
      '<p id="eecr-check-result" role="status"></p>'+
      '<p id="eecr-channel-check" style="white-space:pre-line;background:#0e283a;padding:12px;border-radius:8px;font-size:13px">Comprobando identificador de canal...</p>'+
      '<button type="button" id="eecr-close-sync" style="padding:11px">Cerrar</button></section>';
    document.body.append(panel);
    panel.querySelector('#eecr-close-sync').onclick=close;
    refreshDiagnostics();
    panel.querySelector('#eecr-check-now').onclick=async()=>{
      const n=panel?.querySelector('#eecr-check-result');if(n)n.textContent='Verificando…';
      const result=await sync();if(n)n.textContent=result?.ok?'Entrega confirmada con la nube.':('Pendiente: '+(result?.error||'comprobar registros sin enviar'));
      if(panel&&lastOk)panel.querySelector('#eecr-last-ok').textContent=new Date(lastOk).toLocaleString('es-CL');
      await refreshDiagnostics();
    };
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
  // Solo el flujo de autorización cifrada puede invocar este cambio de grupo.
  // Conservar los registros originales; restablecer solo el cursor y los ACK del canal anterior.
  async function adoptAuthorizedChannel(value){
    if(!keyPattern.test(value))throw Error('Canal de grupo inválido.');
    if(secret===value)return;
    for(let attempts=0;inFlight&&attempts<40;attempts++)await new Promise(resolve=>setTimeout(resolve,150));
    if(inFlight)throw Error('Hay una sincronización en curso. Vuelve a intentar la asociación.');
    localStorage.setItem(PAIR,value);
    secret=value;
    localStorage.removeItem(ACK);
    localStorage.removeItem(SINCE);
    lastOk=null;
    status('Grupo autorizado · preparando sincronización…','warn');
    // Los datos existentes nunca se borran; se sincronizarán con el grupo autorizado.
    await sync();
  }
  window.EECR_DEVICE_SYNC={sync,openPanel,hasPair:()=>!!secret,lastSuccess:()=>lastOk,adoptAuthorizedChannel};
  window.EECR_DEVICE_SYNC_BOOTING=false;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();