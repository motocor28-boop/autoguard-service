/* EECR — seis registros demostrativos con fotografías y carga persistente en móvil. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3',LEGACY='mantpro-records',PENDING='eecr-demo-six-pending-v2',C=window.MANTPRO_CONFIG||{};
  const IDS=['eecr-demo-job-001','eecr-demo-progress-001','eecr-demo-safety-001','eecr-demo-walk-001','eecr-demo-walk-safety-001','eecr-demo-kpi-001'];
  const $=(s,r=document)=>r.querySelector(s);
  const parse=key=>{try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value:[]}catch{return[]}};
  const notify=text=>{const t=$('#toast');if(t){t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,5200)}else alert(text)};
  const localDate=()=>{const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
  const at=(hour,minute=0)=>{const n=new Date(),d=new Date(n.getFullYear(),n.getMonth(),n.getDate(),hour,minute,0,0);return d.toISOString()};
  const photo=(id,url,designation,segment,capturedAt,description,credit)=>({id,dataUrl:url,src:url,designation,segment,capturedAt,description,note:description,source:'Pexels',credit,demo:true});
  const PHOTOS={
    before:'https://images.pexels.com/photos/10290629/pexels-photo-10290629.jpeg?auto=compress&cs=tinysrgb&w=900',
    during:'https://images.pexels.com/photos/37340066/pexels-photo-37340066/free-photo-of-technician-repairing-machinery-in-workshop.jpeg?auto=compress&cs=tinysrgb&w=900',
    deviation:'https://images.pexels.com/photos/8985965/pexels-photo-8985965.jpeg?auto=compress&cs=tinysrgb&w=900',
    walk:'https://images.pexels.com/photos/16045333/pexels-photo-16045333.jpeg?auto=compress&cs=tinysrgb&w=900',
    immediate:'https://images.pexels.com/photos/32208781/pexels-photo-32208781/free-photo-of-technician-repairing-industrial-machine-equipment.jpeg?auto=compress&cs=tinysrgb&w=900',
    kpi:'https://images.pexels.com/photos/36727265/pexels-photo-36727265.jpeg?auto=compress&cs=tinysrgb&w=900'
  };
  function examples(){
    const now=new Date().toISOString(),job='eecr-demo-job-001',walk='eecr-demo-walk-001';
    return[
      {id:job,type:'job',title:'EECR-DEMO-OT-001 · Bomba P-101',at:at(8,0),updatedAt:now,dirty:true,synced:false,data:{demo:true,folio:'EECR-DEMO-OT-001',plant:'Planta de Procesos — Demostración',area:'Sala de bombas',equip:'Bomba centrífuga P-101',task:'Inspección y corrección de fuga en conjunto de bombeo',maintenance:'Correctiva',priority:'Alta',plannedStart:at(8,0),plannedEnd:at(12,0),actualStart:at(8,15),actualEnd:at(11,50),docsStart:at(7,55),docsEnd:at(8,5),lotoStart:at(8,5),zeroVerifiedAt:at(8,12),lotoEnd:at(11,42),progress:100,pauses:[],technicians:'Técnico demostración',stagePhotos:[photo('eecr-demo-photo-01',PHOTOS.before,'Antes del trabajo','Trabajo',at(8,10),'Vista general del equipo y de la sala de bombas antes de iniciar la intervención.','The Shutter Vision / Pexels')]}},
      {id:'eecr-demo-progress-001',type:'progress',title:'65% · Inspección mecánica y corrección',at:at(9,35),updatedAt:now,dirty:true,synced:false,data:{demo:true,jobId:job,recordedAt:at(9,35),percent:65,text:'Se retiraron las protecciones, se inspeccionó el acoplamiento y se corrigió la condición observada en el conjunto.',findings:'Se detectó desgaste superficial y pérdida menor de estanqueidad, sin daño estructural visible.',photoType:'Durante el trabajo',stagePhotos:[photo('eecr-demo-photo-02',PHOTOS.during,'Durante el trabajo','Trabajo',at(9,35),'Técnico realizando la inspección y el ajuste del conjunto durante la intervención.','Bulat843 / Pexels')]}},
      {id:'eecr-demo-safety-001',type:'safety',title:'Condición insegura · Sala de bombas',at:at(8,25),updatedAt:now,dirty:true,synced:false,data:{demo:true,jobId:job,origin:'Trabajo',recordedAt:at(8,25),plant:'Planta de Procesos — Demostración',area:'Sala de bombas',category:'Condición insegura',risk:'Medio',text:'Se observó presencia de aceite en el sector próximo al equipo, generando riesgo de resbalamiento y contaminación del área.',action:'Se delimitó el sector, se instaló material absorbente y se limpió la superficie antes de continuar.',recommendation:'Verificar la estanqueidad del sistema y mantener control visual posterior a la puesta en servicio.',responsible:'Supervisor EECR',dueDate:localDate(),closedAt:at(11,30),stagePhotos:[photo('eecr-demo-photo-03',PHOTOS.deviation,'Desviación o hallazgo detectado','Desviación',at(8,25),'Condición inicial del equipo y sus conexiones al momento de detectar la desviación.','Artem Podrez / Pexels')]}},
      {id:walk,type:'walk',title:'Caminata · Área de equipos rotatorios',at:at(10,0),updatedAt:now,dirty:true,synced:false,data:{demo:true,startAt:at(10,0),endAt:at(10,35),plant:'Planta de Procesos — Demostración',area:'Equipos rotatorios y tableros',objective:'Verificar condiciones operacionales, orden, limpieza y controles de seguridad.',participants:'Esteban Cortez Richards, Técnico demostración',stagePhotos:[photo('eecr-demo-photo-04',PHOTOS.walk,'Vista general de la caminata','Caminata',at(10,5),'Vista general del sector recorrido durante la caminata de seguridad.','Hoang NC / Pexels')]}},
      {id:'eecr-demo-walk-safety-001',type:'safety',title:'Orden y aseo · Sector de mantenimiento',at:at(10,18),updatedAt:now,dirty:true,synced:false,data:{demo:true,walkId:walk,origin:'Caminata',recordedAt:at(10,18),plant:'Planta de Procesos — Demostración',area:'Sector de mantenimiento',category:'Orden y aseo',risk:'Bajo',text:'Se identificaron herramientas y elementos de trabajo fuera de su ubicación definida.',action:'Los elementos fueron ordenados y el área quedó despejada durante la caminata.',recommendation:'Mantener el estándar de orden al término de cada actividad.',responsible:'Técnico demostración',dueDate:localDate(),closedAt:at(10,30),stagePhotos:[photo('eecr-demo-photo-05',PHOTOS.immediate,'Medida inmediata aplicada','Caminata',at(10,25),'Ejecución de la medida inmediata y revisión del sector antes de cerrar el hallazgo.','Bulat843 / Pexels')]}},
      {id:'eecr-demo-kpi-001',type:'kpi',title:'Técnico demostración · 94%',at:at(11,55),updatedAt:now,dirty:true,synced:false,data:{demo:true,jobId:job,recordedAt:at(11,55),technician:'Técnico demostración',safety:5,quality:5,compliance:5,productivity:4,documentation:4,communication:5,score:94,firstTimeRight:true,rework:false,externalFactors:false,notes:'El técnico cumplió los controles de seguridad, realizó la inspección de acuerdo con el alcance y dejó evidencia del trabajo ejecutado.',training:'Reforzar registro de mediciones y condición final en informes técnicos.',stagePhotos:[photo('eecr-demo-photo-06',PHOTOS.kpi,'Evidencia de desempeño','KPI',at(11,45),'Área de trabajo organizada al término de la actividad, utilizada como evidencia de calidad y cierre.','Lucas Porras / Pexels')]}}
    ];
  }
  function count(){return parse(STORE).filter(x=>IDS.includes(x.id)).length}
  function openReports(){
    $('[data-route="reports"]')?.click();
    setTimeout(()=>{const date=$('#ehs-report-date')||$('#report-form [name="date"]');if(date){date.value=localDate();date.dispatchEvent(new Event('change',{bubbles:true}))}},350);
  }
  let seeding=false;
  async function seed({navigate=true,syncCloud=true}={}){
    if(seeding)return false;seeding=true;
    try{
      const map=new Map(parse(STORE).map(x=>[x.id,x]));examples().forEach(x=>map.set(x.id,x));localStorage.setItem(STORE,JSON.stringify([...map.values()]));localStorage.removeItem(PENDING);
      window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{demoLoaded:true,count:IDS.length}}));
      window.MANTPRO?.render?.();
      notify('6 ejemplos EECR cargados. Abra Informes para revisar los PDF.');
      if(navigate)setTimeout(openReports,250);
      if(syncCloud&&window.MANTPRO_AUTH?.token?.()&&navigator.onLine)setTimeout(()=>window.MANTPRO?.sync?.().catch?.(()=>{}),700);
      return true;
    }finally{seeding=false}
  }
  async function remove(){
    if(!confirm('Se eliminarán solamente los 6 registros demostrativos EECR. Los registros reales no serán modificados. ¿Continuar?'))return false;
    const token=window.MANTPRO_AUTH?.token?.()||'';
    if(token&&navigator.onLine&&C.supabaseUrl){for(const id of IDS){const r=await fetch(`${C.supabaseUrl}/rest/v1/mantpro_records?id=eq.${encodeURIComponent(id)}`,{method:'DELETE',headers:{Prefer:'return=minimal'}});if(!r.ok)throw new Error(`No fue posible eliminar ${id} de la nube.`)}}
    localStorage.setItem(STORE,JSON.stringify(parse(STORE).filter(x=>!IDS.includes(x.id))));localStorage.setItem(LEGACY,JSON.stringify(parse(LEGACY).filter(x=>!IDS.includes(x.id))));localStorage.removeItem(PENDING);
    window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{demoRemoved:true}}));window.MANTPRO?.render?.();notify('Los ejemplos EECR fueron eliminados.');return true;
  }
  function panel(){
    const app=$('#app');if(!app||!/^Informes$/i.test(app.querySelector('h1')?.textContent?.trim()||''))return;
    let box=$('#eecr-demo-panel',app);if(!box){box=document.createElement('section');box.id='eecr-demo-panel';box.className='callout section';box.innerHTML='<div><b>Prueba del informe final</b><br><small>Cargue seis ejemplos con fotografías y descripciones. Se identifican como EECR-DEMO y pueden eliminarse después.</small></div><div class="button-row"><button type="button" class="primary" data-eecr-demo-load>Cargar 6 ejemplos</button><button type="button" class="outline" data-eecr-demo-remove>Eliminar ejemplos</button></div><p data-eecr-demo-state class="muted"></p>';app.querySelector('h1')?.insertAdjacentElement('afterend',box);box.querySelector('[data-eecr-demo-load]').onclick=()=>seed();box.querySelector('[data-eecr-demo-remove]').onclick=async()=>{try{await remove()}catch(error){alert(error.message||'No fue posible eliminar la demostración.')}}}
    const state=box.querySelector('[data-eecr-demo-state]');if(state)state.textContent=`Ejemplos visibles en este dispositivo: ${count()} de 6.`;
  }
  function requestFromUrl(){
    const params=new URLSearchParams(location.search);
    if(params.get('demo')==='6'||params.get('ejemplos')==='6'){localStorage.setItem(PENDING,'1');params.delete('demo');params.delete('ejemplos');const q=params.toString();history.replaceState({},'',location.pathname+(q?'?'+q:'')+location.hash);return true}
    return false;
  }
  function loadPending(){if(localStorage.getItem(PENDING)==='1'&&count()<6)setTimeout(()=>seed({navigate:true,syncCloud:true}),350)}
  let timer;const enhance=()=>{clearTimeout(timer);timer=setTimeout(panel,90)};
  const start=()=>{
    requestFromUrl();
    new MutationObserver(enhance).observe($('#app')||document.body,{childList:true,subtree:true});
    window.addEventListener('mantpro-records-changed',enhance);
    window.addEventListener('mantpro-auth-ready',loadPending);
    window.addEventListener('mantpro-auth-changed',loadPending);
    enhance();
    setTimeout(loadPending,900);
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.EECR_DEMO={seed,remove,count,openReports,ids:IDS,build:'2026-08-02-demo-six-mobile-fix'};
})();
