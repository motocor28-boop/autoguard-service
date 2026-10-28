/* EECR/MantPro: canal de sincronización privada sin correo.
   Primer enlace dispositivo a dispositivo por clave aleatoria de 256 bits;
   posteriormente envío/recepción automática vía HTTPS, incluso con hotspot Android. */
(()=>{
  'use strict';
  const C=window.MANTPRO_CONFIG||{};
  const STORE='mantpro-records-v3',PAIR='eecr-device-pair-v1',ACK='eecr-device-ack-v1',CONFLICT='eecr-device-conflicts-v1',SINCE='eecr-device-last-pull-v1',PART='eecr-photo-part',FULL_PULL='eecr-device-last-full-pull-v1';
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
  // Fragmentos de sincronización: evitan descartar registros con muchas fotos.
  // Se transportan los bytes JSON originales, sin recomprimir ni recortar imágenes.
  const b64=v=>{let out='';for(let i=0;i<v.length;i+=8192)out+=String.fromCharCode(...v.subarray(i,i+8192));return btoa(out)};
  const unb64=v=>Uint8Array.from(atob(v),c=>c.charCodeAt(0));
  async function photoParts(row){
    const bytes=new TextEncoder().encode(JSON.stringify(row)),piece=360000,total=Math.ceil(bytes.length/piece);
    const digest=new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(row.id)));
    const root=Array.from(digest,b=>b.toString(16).padStart(2,'0')).join('');
    return Array.from({length:total},(_,i)=>({
      id:'eecr-part-'+root+'-'+i,type:PART,title:'Evidencia fotográfica fragmentada',
      at:row.at||stamp(row),updatedAt:stamp(row),
      data:{parentId:row.id,sourceUpdatedAt:stamp(row),index:i,total,encoding:'utf8-base64',
        bytes:b64(bytes.slice(i*piece,(i+1)*piece))}
    }));
  }
  function assemble(raw){
    const regular=[],groups=new Map(),decoder=new TextDecoder('utf-8',{fatal:true});
    for(const item of raw){
      if(item?.type!==PART){regular.push(item);continue}
      const d=item.data||{},id=d.parentId,stampValue=d.sourceUpdatedAt;
      if(typeof id!=='string'||typeof stampValue!=='string'||!Number.isInteger(d.index)||
         !Number.isInteger(d.total)||d.total<1||d.total>10000||d.index<0||d.index>=d.total||
         typeof d.bytes!=='string')continue;
      const key=id+'|'+stampValue;
      if(!groups.has(key))groups.set(key,{id,stampValue,total:d.total,parts:new Map()});
      const group=groups.get(key);
      if(group.total===d.total)group.parts.set(d.index,d.bytes);
    }
    // Solo la revisión más reciente de cada OT cuenta como pendiente.
    // Al reducir el número de fotos pueden quedar fragmentos antiguos en nube.
    const latest=new Map();
    for(const group of groups.values()){
      const old=latest.get(group.id);
      if(!old||Date.parse(group.stampValue)>Date.parse(old.stampValue))latest.set(group.id,group);
    }
    let incomplete=0;
    for(const group of latest.values()){
      if(group.parts.size!==group.total){incomplete++;continue}
      try{
        const bytes=[],lens=[],all=Array.from({length:group.total},(_,i)=>unb64(group.parts.get(i)));
        const sum=all.reduce((n,v)=>n+v.length,0),joined=new Uint8Array(sum);let pos=0;
        for(const part of all){joined.set(part,pos);pos+=part.length}
        const item=JSON.parse(decoder.decode(joined));
        if(item?.id!==group.id||stamp(item)!==group.stampValue||item.type===PART)throw Error('Metadatos de fragmentos inconsistentes');
        regular.push(item);
      }catch(e){incomplete++;console.warn('EECR: fotografía incompleta, sin sobrescribir el registro',e)}
    }
    return {records:regular,incomplete};
  }
  async function pull(forceFull=false){
    let offset=0,received=[],watermark=null;
    const last=forceFull?null:localStorage.getItem(SINCE);
    const since=last&&Number.isFinite(Date.parse(last))?new Date(Date.parse(last)-5000).toISOString():null;
    for(let page=0;page<2000;page++){
      const res=await call('pull',{since,offset,limit:8});
      if(!Array.isArray(res.records))throw Error('Respuesta de sincronización inválida');
      received.push(...res.records.filter(x=>x&&typeof x.id==='string'&&!isDemo(x)));
      if(res.watermark&&(!watermark||Date.parse(res.watermark)>Date.parse(watermark)))watermark=res.watermark;
      if(res.nextOffset===null){const assembled=assemble(received);return {...assembled,watermark:assembled.incomplete?null:watermark};}
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
  // Fotografías se concilian por ID individual, nunca por un folio de OT repetible.
  function combinePhotoLists(local,remote){
    const a=Array.isArray(local?.data?.stagePhotos)?local.data.stagePhotos:[];
    const b=Array.isArray(remote?.data?.stagePhotos)?remote.data.stagePhotos:[];
    const ids=new Set(b.map(p=>p?.id||p?.dataUrl||p?.src).filter(Boolean));
    const missing=a.filter(p=>p&&(p.id||p.dataUrl||p.src)&&!ids.has(p.id||p.dataUrl||p.src));
    if(!missing.length)return {record:remote,changed:false};
    return {record:{...remote,data:{...(remote.data||{}),stagePhotos:[...b,...missing]},
      updatedAt:new Date().toISOString(),dirty:true,synced:false},changed:true};
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
        const combined=combinePhotoLists(old,remote);
        map.set(remote.id,combined.changed?combined.record:{...remote,dirty:false,synced:true});
        changed=true;ack[remote.id]=stamp(remote);
      }else if(newer===previous){
        const combined=combinePhotoLists(old,remote);
        if(combined.changed){
          map.set(old.id,combined.record);changed=true;ack[old.id]=stamp(remote);
        }else{
          ack[remote.id]=stamp(old);
          if(old.dirty||!old.synced){map.set(old.id,{...old,dirty:false,synced:true});changed=true;}
        }
      }else{
        // Si el PC tiene una versión más nueva pero faltan fotografías remotas,
        // unirlas sin reducir el avance ni los textos locales.
        const combined=combinePhotoLists(remote,old);
        if(combined.changed){map.set(old.id,combined.record);changed=true;ack[old.id]=stamp(remote)}
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
      const textSize=JSON.stringify(row).length;
      const parts=textSize>1_500_000?await photoParts(row):[row];
      let sentAll=true;
      for(const part of parts){
        const bytes=JSON.stringify(part).length;
        if(bytes>1_850_000){oversized++;sentAll=false;break}
        if(batch.length>=6||size+bytes>1_650_000)await flush();
        batch.push(part);size+=bytes;
      }
      if(!sentAll)console.warn('EECR: registro demasiado grande, conservado sin borrar',row.id);
    }
    await flush();
    return {uploaded,oversized};
  }
  async function sync(options={}){
    if(inFlight)return {ok:false,error:'Ya existe una sincronización en curso'};
    const forceFull=options.full===true || Date.now()-Number(localStorage.getItem(FULL_PULL)||0)>21600000;
    if(!secret){status('Vinculación local pendiente','warn');return;}
    if(!navigator.onLine){status('Sin Internet · guardado local','warn');return;}
    inFlight=true;
    try{
      status('Sincronizando…');
      const up=await push();
      const ack=safeRead(ACK,{});
      const pulled=await pull(forceFull);
      const conflicts=merge(pulled.records,ack);
      if(pulled.watermark)localStorage.setItem(SINCE,pulled.watermark);
      if(forceFull&&!pulled.incomplete)localStorage.setItem(FULL_PULL,String(Date.now()));
      lastOk=new Date().toISOString();errorCount=0;
      const pending=localRecords().filter(x=>!isDemo(x)&&ack[x.id]!==stamp(x)).length;
      if(up.oversized||conflicts||pending||pulled.incomplete)status('Sincronizado parcialmente · revisar '+(pending+up.oversized+conflicts+pulled.incomplete),'warn');
      else status('Sincronizado','ok');
      window.dispatchEvent(new CustomEvent('mantpro-sync-complete',{detail:{count:localRecords().length,conflicts,pending}}));
      return {ok:!pending&&!conflicts&&!up.oversized&&!pulled.incomplete,up,conflicts,pending,incomplete:pulled.incomplete,restored:pulled.records.length};
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
  function localBackup(){
    const data={application:'EECR/MANTPRO',exportedAt:new Date().toISOString(),records:localRecords(),
      conflicts:safeRead(CONFLICT,[])};
    const url=URL.createObjectURL(new Blob([JSON.stringify(data)],{type:'application/json'}));
    const a=document.createElement('a');a.href=url;a.download='HEPI_MANTPRO_Respaldo_pre_vinculacion_'+Date.now()+'.json';
    document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),15000);
  }
  async function adoptWithConfirmation(value){
    if(!keyPattern.test(value))throw Error('Clave de emparejamiento inválida');
    if(secret===value)return sync({full:true});
    if(!confirm('Se unirán los datos locales con el canal del otro dispositivo. Primero se descargará un respaldo JSON de este equipo. ¿Continuar?'))return null;
    localBackup();
    // Conservar el canal antiguo en este mismo navegador para recuperación controlada.
    const previous=safeRead('eecr-device-previous-channels-v1',[]);
    if(keyPattern.test(secret)&&!previous.includes(secret)){
      previous.push(secret);
      localStorage.setItem('eecr-device-previous-channels-v1',JSON.stringify(previous));
    }
    await adoptAuthorizedChannel(value);
    return sync({full:true});
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
      '<button type="button" id="eecr-recover-all" style="padding:12px;background:#ffcf52;border:0;font-weight:bold">Recuperar historial y fotos completas</button>'+
      '<button type="button" id="eecr-copy-link" style="padding:11px">Copiar enlace privado para vincular otro equipo</button>'+
      '<button type="button" id="eecr-join-link" style="padding:11px">Vincular a otro equipo</button>'+
      '<p id="eecr-check-result" role="status"></p>'+
      '<p id="eecr-channel-check" style="white-space:pre-line;background:#0e283a;padding:12px;border-radius:8px;font-size:13px">Comprobando identificador de canal...</p>'+
      '<button type="button" id="eecr-close-sync" style="padding:11px">Cerrar</button></section>';
    document.body.append(panel);
    panel.querySelector('#eecr-close-sync').onclick=close;
    panel.querySelector('#eecr-recover-all').onclick=async e=>{
      e.currentTarget.disabled=true;
      try{
        const r=await sync({full:true});
        panel.querySelector('#eecr-check-result').textContent=r?.ok?'Historial completo verificado. Registros: '+localRecords().length:'Recuperación parcial: '+(r?.error||r?.pending||'comprobar pendientes');
      }finally{e.currentTarget.disabled=false;refreshDiagnostics()}
    };
    panel.querySelector('#eecr-copy-link').onclick=async()=>{
      try{await navigator.clipboard.writeText(pairingUrl());alert('Enlace privado copiado. Ábrelo únicamente en tu teléfono o computador.')}catch{prompt('Copia este enlace privado (no lo compartas con terceros):',pairingUrl())}
    };
    panel.querySelector('#eecr-join-link').onclick=async()=>{
      const raw=prompt('Pega aquí el enlace privado o la clave del otro equipo:','');if(!raw)return;
      let candidate=raw.trim();try{candidate=new URL(raw).hash.replace(/^#eecrDevice=/,'')||candidate}catch{}
      try{await adoptWithConfirmation(decodeURIComponent(candidate));refreshDiagnostics()}catch(err){alert(err.message||'No fue posible vincular el equipo')}
    };
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
      if(secret&&secret!==incoming){
        window.setTimeout(()=>adoptWithConfirmation(incoming).then(()=>openPanel()).catch(e=>alert(e.message)),300);
      }else{
        persistSecret(incoming);
        window.setTimeout(()=>{sync({full:true});openPanel();},500);
      }
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
      if(secret)sync({full:true});
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
    localStorage.removeItem(SINCE);localStorage.removeItem(FULL_PULL);
    lastOk=null;
    status('Grupo autorizado · preparando sincronización…','warn');
    // Los datos existentes nunca se borran; se sincronizarán con el grupo autorizado.
    await sync();
  }
  window.EECR_DEVICE_SYNC={sync,openPanel,hasPair:()=>!!secret,lastSuccess:()=>lastOk,adoptAuthorizedChannel,channelCode};
  window.EECR_DEVICE_SYNC_BOOTING=false;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();