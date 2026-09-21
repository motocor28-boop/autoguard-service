/* MANTPRO — casos operacionales Q1 2026. Carga determinística para PC/móvil; procedencia sintética conservada en metadatos. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3', MARK='mantpro-q1-2026-cases-v2', LOCAL_MARK='mantpro-q1-2026-local-v2';
  const META={kind:'synthetic-training',dataset:'Q1_2026_OPERATIONAL_CASES',generatedFor:'MANTPRO',historicalEvidence:false};
  const commons=name=>'https://commons.wikimedia.org/wiki/Special:Redirect/file/'+encodeURIComponent(name)+'?width=960';
  const PHOTO={
    pump:commons('Operational procedures 120827-F-EA289-004.jpg'),
    mechanic:commons('Rick Sacca, maintenance mechanic, working on a water pump at Lake Village (53087035030).jpg'),
    equipment:commons('NWO-Pumpe2.JPG'),
    safety:commons('QA inspection checks, work, safety 140509-F-QQ371-036.jpg'),
    harness:commons('Worker with safety harness (9248564334).jpg'),
    clean:commons('Clean pump.JPG'),
    test:commons('U.S. Navy Hull Maintenance Technician 2nd Class Stephen J. Lippold, right, and Hull Maintenance Technician 3rd Class Benjamin R. Smith test the discharge hose from a P-100 pump during a damage control team 130822-N-LN619-037.jpg')
  };
  const ts=(m,d,h,min=0)=>`2026-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}T${String(h).padStart(2,'0')}:${String(min).padStart(2,'0')}:00-03:00`;
  const iso=x=>new Date(x).toISOString();
  const provenance=()=>({...META});
  const techs=[
    ['q1-tech-01','Carlos Muñoz','Mecánico','Mantención Planta'],['q1-tech-02','Luis Araya','Mecánico','Mantención Planta'],
    ['q1-tech-03','Rodrigo Soto','Eléctrico','Mantención Planta'],['q1-tech-04','Andrés Morales','Instrumentista','Mantención Planta'],
    ['q1-tech-05','Patricio Rojas','Mecánico','Servicios Mecánicos'],['q1-tech-06','Miguel Salinas','Mecánico','Servicios Mecánicos']
  ].map(([id,name,specialty,company],i)=>({id,name,specialty,company,phone:'',createdAt:iso(ts(1,5+i,8)),updatedAt:iso(ts(1,5+i,8)),provenance:provenance()}));
  const JOBS=[
    [1,1,12,'OT-2026-001','Planta Concentradora','Bombas de proceso','Bomba centrífuga','P-101','Correctiva','Alta','Cambio de sello mecánico y revisión de acoplamiento','q1-tech-01','q1-tech-02',PHOTO.mechanic],
    [2,1,20,'OT-2026-002','Planta Agua Industrial','Estación de impulsión','Bomba vertical','VTP-202','Preventiva','Normal','Alineamiento motor-bomba y verificación de juego axial','q1-tech-01','q1-tech-03',PHOTO.pump],
    [3,1,29,'OT-2026-003','Planta Concentradora','Correas','Reductor','CV-04-RD','Predictiva','Normal','Inspección vibracional, nivel de aceite y condición de acoplamiento','q1-tech-04','q1-tech-05',PHOTO.equipment],
    [4,2,9,'OT-2026-004','Planta Concentradora','Bombas de proceso','Bomba centrífuga','P-204','Correctiva','Alta','Cambio de rodamientos y centrado del conjunto rotativo','q1-tech-02','q1-tech-05',PHOTO.mechanic],
    [5,2,17,'OT-2026-005','Taller Mecánico','Hidráulica','Unidad hidráulica','HP-03','Correctiva','Alta','Corrección de fuga y cambio de manguera de alta presión','q1-tech-05','q1-tech-06',PHOTO.equipment],
    [6,2,26,'OT-2026-006','Planta Concentradora','Ventilación','Ventilador centrífugo','VF-12','Preventiva','Normal','Inspección de rodamientos, correas y balanceo operacional','q1-tech-01','q1-tech-04',PHOTO.safety],
    [7,3,8,'OT-2026-007','Planta Agua Industrial','Bombas de proceso','Bomba centrífuga','P-307','Preventiva','Normal','Inspección de impulsor, limpieza y control de holguras','q1-tech-01','q1-tech-02',PHOTO.clean],
    [8,3,18,'OT-2026-008','Planta Concentradora','Filtrado','Filtro prensa','FP-02','Correctiva','Alta','Intervención de cilindro hidráulico y prueba funcional','q1-tech-05','q1-tech-06',PHOTO.test],
    [9,3,27,'OT-2026-009','Taller Equipos Móviles','Servicios','Grúa horquilla','GH-05','Preventiva','Normal','Revisión de frenos, sistema hidráulico y prueba operacional','q1-tech-03','q1-tech-06',PHOTO.safety]
  ].map(([n,m,d,folio,plant,area,equipment,tag,type,priority,description,t1,t2,photo])=>{
    const start=ts(m,d,8,0), end=ts(m,d,15,30);
    return {id:`q1-job-${String(n).padStart(2,'0')}`,folio,plant,area,equipment,tag,type,priority,description,technicianIds:[t1,t2],plannedDate:`2026-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`,plannedStart:'08:00',plannedEnd:'16:00',actualStart:iso(start),actualEnd:iso(end),safetyDocStart:iso(ts(m,d,7,35)),safetyDocEnd:iso(ts(m,d,7,55)),lockoutStart:iso(ts(m,d,8,0)),zeroEnergyVerifiedAt:iso(ts(m,d,8,12)),lockoutEnd:iso(ts(m,d,15,20)),unlockEnd:iso(ts(m,d,15,25)),pauseMinutes:30,progress:100,sourcePhotos:[photo],createdAt:iso(ts(m,d,7,30)),updatedAt:iso(end),provenance:provenance()};
  });
  const stageText=[
    ['Inspección inicial, documentación de seguridad y bloqueo del equipo.','Condición inicial registrada; controles críticos verificados.',25,'Antes'],
    ['Desmontaje e intervención técnica según alcance de la orden.','Mediciones y condición de componentes revisadas durante la intervención.',65,'Durante el trabajo'],
    ['Armado, pruebas funcionales y entrega del equipo a operación.','Prueba final satisfactoria y parámetros dentro del rango esperado.',100,'Después']
  ];
  const PROGRESS=[];
  JOBS.forEach((j,ji)=>stageText.forEach((s,si)=>{
    const base=new Date(j.actualStart).getTime(), at=new Date(base+[45,240,420][si]*60000).toISOString();
    PROGRESS.push({id:`q1-progress-${String(ji+1).padStart(2,'0')}-${si+1}`,workId:j.id,timestamp:at,type:s[3],percent:s[2],notes:s[0],findings:s[1],photoPaths:[j.sourcePhotos[0]],updatedAt:at,provenance:provenance()});
  }));
  const DEVIATIONS=[
    ['01',JOBS[0],1,12,9,20,'Condición insegura','Medio','Presencia de aceite en piso junto al equipo intervenido.','Se aisló el sector y se realizó limpieza inmediata.','Mantener bandeja de contención durante desmontaje.',PHOTO.safety],
    ['02',JOBS[1],1,20,10,10,'Línea de fuego','Alto','Herramienta ubicada dentro del radio de movimiento durante prueba de giro.','Se detuvo la actividad y se despejó el área.','Demarcar zona de exclusión antes de pruebas dinámicas.',PHOTO.safety],
    ['03',JOBS[3],2,9,11,0,'Orden y aseo','Bajo','Manguera de servicio atravesaba zona de tránsito peatonal.','Se reubicó y aseguró la manguera fuera del paso.','Usar canalización temporal en intervenciones prolongadas.',PHOTO.safety],
    ['04',JOBS[4],2,17,10,30,'LOTO / energías peligrosas','Alto','Punto de presión residual detectado antes de desacoplar línea hidráulica.','Se descargó presión y se verificó energía cero.','Incorporar punto de purga al checklist del sistema.',PHOTO.safety],
    ['05',JOBS[6],3,8,12,10,'EPP','Medio','Protección facial no disponible en el punto de limpieza de componentes.','Se suspendió limpieza hasta disponer del EPP requerido.','Mantener kit de EPP específico en carro de trabajo.',PHOTO.harness],
    ['06',JOBS[8],3,27,14,0,'Observación positiva','Bajo','Área ordenada, herramientas segregadas y control de derrames disponible.','Se reconoció la buena práctica al equipo.','Mantener estándar de orden y cierre del trabajo.',PHOTO.safety]
  ].map(([n,j,m,d,h,min,category,risk,description,immediateAction,correctiveAction,photo])=>({id:`q1-safety-${n}`,workId:j.id,walkId:'',plant:j.plant,area:j.area,category,risk,description,immediateAction,correctiveAction,preventiveAction:'Verificar el control en la siguiente inspección de supervisión.',responsible:'Supervisor de turno',dueDate:`2026-${String(m).padStart(2,'0')}-${String(Math.min(d+2,28)).padStart(2,'0')}`,status:'Cerrada',closedAt:iso(ts(m,d,h+1,min)),detectedAt:iso(ts(m,d,h,min)),updatedAt:iso(ts(m,d,h+1,min)),photoPaths:[photo],closurePhotoPaths:[],provenance:provenance()}));
  const WALKS=[
    ['01',1,8,'Planta Concentradora','Bombas y piping'],['02',1,23,'Planta Agua Industrial','Estación de impulsión'],
    ['03',2,6,'Taller Mecánico','Bahías de mantenimiento'],['04',2,21,'Planta Concentradora','Correas y transferencia'],
    ['05',3,11,'Planta Concentradora','Filtrado y bombas'],['06',3,25,'Taller Equipos Móviles','Patio y taller']
  ].map(([n,m,d,plant,areas])=>({id:`q1-walk-${n}`,folio:`CS-2026-${n}`,date:`2026-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`,startTime:'09:00',endTime:'10:15',plant,areas,objective:'Verificar controles críticos, orden operacional y condiciones de los equipos.',participants:'Esteban Cortez, equipo de mantención',notes:'Recorrido de supervisión con verificación de condiciones y acciones en terreno.',createdAt:iso(ts(m,d,9)),updatedAt:iso(ts(m,d,10,15)),provenance:provenance()}));
  const EVALS=JOBS.map((j,i)=>({id:`q1-kpi-${String(i+1).padStart(2,'0')}`,workId:j.id,technicianId:j.technicianIds[0],date:j.plannedDate,safetyScore:[5,5,4,5,4,5,5,4,5][i],qualityScore:[5,4,5,4,5,4,5,5,4][i],scheduleScore:[4,5,5,4,4,5,5,4,5][i],productivityScore:[4,4,5,4,5,4,5,4,5][i],documentationScore:[5,4,4,5,4,5,5,4,4][i],communicationScore:[5,5,4,4,5,4,5,5,5][i],strengths:'Aplicación de controles, coordinación y ejecución técnica conforme al alcance.',improvements:'Mantener registro oportuno de mediciones y cierre documental.',trainingNeeded:'Refuerzo periódico de controles críticos y estándares del equipo.',createdAt:j.actualEnd,updatedAt:j.actualEnd,provenance:provenance()}));
  const ASSETS=[
    ['q1-asset-01','P-101','Bomba centrífuga','Planta Concentradora','Bombas de proceso'],['q1-asset-02','VTP-202','Bomba vertical','Planta Agua Industrial','Estación de impulsión'],
    ['q1-asset-03','CV-04-RD','Reductor','Planta Concentradora','Correas'],['q1-asset-04','FP-02','Filtro prensa','Planta Concentradora','Filtrado'],['q1-asset-05','GH-05','Grúa horquilla','Taller Equipos Móviles','Servicios']
  ].map(([id,tag,name,plant,area])=>({id,tag,name,plant,area,status:'Operativo',criticality:'B',createdAt:iso(ts(1,5,8)),updatedAt:iso(ts(3,31,8)),provenance:provenance()}));
  const INVENTORY=[
    ['SELLO-P101','Sello mecánico 45 mm',3,1],['ROD-6312','Rodamiento 6312',6,2],['ACOP-ELAST','Elemento elástico de acoplamiento',5,2],['MANG-HID-1','Manguera hidráulica alta presión',4,1],
    ['ACEITE-ISO68','Aceite hidráulico ISO VG 68',40,10],['GRASA-EP2','Grasa EP2',18,5],['FILT-HID-03','Filtro hidráulico HP-03',3,1],['PAST-GH05','Juego pastillas freno GH-05',2,1]
  ].map(([sku,name,stock,minStock],i)=>({id:`q1-inv-${i+1}`,sku,name,stock,minStock,location:`Bodega-${i%3+1}`,updatedAt:iso(ts(3,31,9)),provenance:provenance()}));
  const PROCEDURES=[
    ['q1-proc-01','Cambio de sello mecánico en bomba centrífuga','Mecánica'],['q1-proc-02','Alineamiento motor-bomba','Mecánica'],['q1-proc-03','Intervención segura de sistemas hidráulicos','Hidráulica'],['q1-proc-04','Bloqueo y verificación de energía cero','Seguridad']
  ].map(([id,title,area])=>({id,title,area,revision:'1',status:'Vigente',updatedAt:iso(ts(1,3,9)),provenance:provenance()}));
  const PLANS=ASSETS.map((a,i)=>({id:`q1-plan-${i+1}`,assetId:a.id,name:`Plan preventivo ${a.tag}`,frequency:['Mensual','Trimestral','Mensual','Trimestral','Mensual'][i],lastDate:`2026-0${Math.min(i+1,3)}-05`,nextDate:`2026-0${Math.min(i+2,4)}-05`,status:'Activo',provenance:provenance()}));
  const STOCK=INVENTORY.map((x,i)=>({id:`q1-stock-${i+1}`,inventoryId:x.id,date:iso(ts(1+(i%3),7+i,11)),type:i%2?'Ingreso':'Salida',quantity:i%2?2:1,reference:`OT-2026-${String((i%9)+1).padStart(3,'0')}`,provenance:provenance()}));
  function talkSvg(title,date){const esc=String(title).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1200"><rect width="900" height="1200" fill="#ddd"/><rect x="70" y="55" width="760" height="1090" rx="8" fill="white"/><text x="120" y="125" font-family="Arial" font-size="30" font-weight="bold">REGISTRO DE CHARLA DE SEGURIDAD</text><text x="120" y="180" font-family="Arial" font-size="24">${esc}</text><text x="120" y="225" font-family="Arial" font-size="20">Fecha: ${date}</text><line x1="120" y1="275" x2="780" y2="275" stroke="#888"/><text x="120" y="330" font-family="Arial" font-size="19">Temas revisados · riesgos · controles críticos · participación</text>${[410,500,590,680,770,860].map((y,i)=>`<line x1="120" y1="${y}" x2="780" y2="${y}" stroke="#bbb"/><text x="130" y="${y-18}" font-family="Arial" font-size="18">Participante ${i+1}</text><path d="M520 ${y-25} q45 -35 90 0 t90 0" fill="none" stroke="#334" stroke-width="3"/>`).join('')}<text x="120" y="1010" font-family="Arial" font-size="18">Relator: Supervisor de Mantención</text><path d="M420 1045 q60 -50 140 0 t120 -5" fill="none" stroke="#334" stroke-width="4"/><text x="120" y="1110" font-family="Arial" font-size="16" fill="#777">Registro visual para capacitación funcional del sistema</text></svg>`)}
  const TALKS=[
    ['q1-talk-01','Bloqueo, aislamiento y verificación de energía cero','2026-01-13','Planta Agua Industrial','Bombas'],
    ['q1-talk-02','Control de línea de fuego durante mantenimiento','2026-02-10','Planta Concentradora','Bombas de proceso'],
    ['q1-talk-03','Orden, aseo y prevención de derrames','2026-03-12','Taller Mecánico','Bahías de mantenimiento']
  ].map(([id,title,date,plant,area])=>({id,date:`${date}T08:00`,title,presenter:'Supervisor de Mantención',plant,area,shift:'Día',observations:'Registro documental para validar flujo de captura y sincronización.',sourceApp:'CHARLAS DIARIAS',transportApp:'MANTPRO IA Premium',createdAt:iso(`${date}T08:00:00-03:00`),updatedAt:iso(`${date}T08:10:00-03:00`),status:'sent',sentAt:iso(`${date}T08:10:00-03:00`),photoDataUrl:talkSvg(title,date),provenance:provenance()}));
  const techById=new Map(techs.map(t=>[t.id,t]));
  const pwa=[];
  const push=(id,type,title,at,data,extra={})=>pwa.push({id,type,title,at,updatedAt:at,dirty:false,synced:true,data:{...data,provenance:provenance()},provenance:provenance(),...extra});
  techs.forEach(t=>push(t.id,'technician',t.name,t.createdAt,{name:t.name,specialty:t.specialty,company:t.company}));
  JOBS.forEach(j=>push(j.id,'job',`${j.folio} · ${j.tag}`,j.createdAt,{folio:j.folio,plant:j.plant,area:j.area,equip:j.tag,task:j.description,maintenance:j.type,priority:j.priority,plannedStart:iso(`${j.plannedDate}T${j.plannedStart}:00-03:00`),plannedEnd:iso(`${j.plannedDate}T${j.plannedEnd}:00-03:00`),technicians:j.technicianIds.map(id=>techById.get(id)?.name).filter(Boolean).join(', '),progress:j.progress,pauses:j.pauseMinutes?[{start:j.actualStart,end:new Date(new Date(j.actualStart).getTime()+j.pauseMinutes*60000).toISOString()}]:[],docsStart:j.safetyDocStart,docsEnd:j.safetyDocEnd,lotoStart:j.lockoutStart,zeroVerifiedAt:j.zeroEnergyVerifiedAt,lotoEnd:j.unlockEnd,actualStart:j.actualStart,actualEnd:j.actualEnd},{photo:j.sourcePhotos[0],photoSource:'Wikimedia Commons · fotografía de referencia'}));
  PROGRESS.forEach(p=>push(p.id,'progress',`${p.percent}% · ${p.notes}`,p.timestamp,{jobId:p.workId,recordedAt:p.timestamp,percent:p.percent,text:p.notes,findings:p.findings,photoType:p.type},{photo:p.photoPaths[0],photoSource:'Wikimedia Commons · fotografía de referencia'}));
  DEVIATIONS.forEach(d=>push(d.id,'safety',`${d.category} · ${d.area}`,d.detectedAt,{origin:'Trabajo',jobId:d.workId,walkId:d.walkId,recordedAt:d.detectedAt,plant:d.plant,area:d.area,category:d.category,risk:d.risk,text:d.description,action:d.immediateAction,recommendation:d.correctiveAction,responsible:d.responsible,dueDate:d.dueDate,closedAt:d.closedAt,photoType:'Evidencia de desviación'},{photo:d.photoPaths[0],photoSource:'Wikimedia Commons · fotografía de referencia'}));
  WALKS.forEach(w=>push(w.id,'walk',`Caminata · ${w.areas}`,iso(`${w.date}T${w.startTime}:00-03:00`),{folio:w.folio,startAt:iso(`${w.date}T${w.startTime}:00-03:00`),endAt:iso(`${w.date}T${w.endTime}:00-03:00`),plant:w.plant,area:w.areas,objective:w.objective,participants:w.participants}));
  EVALS.forEach(e=>{const t=techById.get(e.technicianId), score=Math.round(((e.safetyScore*.30)+(e.qualityScore*.25)+(e.scheduleScore*.15)+(e.productivityScore*.10)+(e.documentationScore*.10)+(e.communicationScore*.10))/5*100);push(e.id,'kpi',`${t?.name||'Técnico'} · ${score}%`,iso(`${e.date}T15:45:00-03:00`),{jobId:e.workId,recordedAt:iso(`${e.date}T15:45:00-03:00`),technician:t?.name||'',safety:e.safetyScore,quality:e.qualityScore,compliance:e.scheduleScore,productivity:e.productivityScore,documentation:e.documentationScore,communication:e.communicationScore,firstTimeRight:true,rework:false,externalFactors:false,score,notes:e.strengths,training:e.trainingNeeded});});
  TALKS.forEach(t=>push(t.id,'talk_signed','Charla firmada',t.createdAt,{sourceApp:t.sourceApp,sourceModule:'SUPERVISIÓN EECR',transportApp:t.transportApp,registrationMode:'signed-talk-photo',reviewStatus:'pendiente-lectura',observations:t.observations,photoFileName:`${t.id}.svg`,photoMimeType:'image/svg+xml',photoSize:0,photoDataUrl:t.photoDataUrl,stagePhotos:[{id:`${t.id}-photo`,dataUrl:t.photoDataUrl,designation:'Documento firmado de la charla',segment:'Charla firmada',capturedAt:t.createdAt,description:t.title,note:t.observations}]},{photo:t.photoDataUrl}));
  function loadPwa(){
    try{
      const current=JSON.parse(localStorage.getItem(STORE)||'[]'), rows=Array.isArray(current)?current:[], map=new Map(rows.map(x=>[x.id,x]));let added=0;
      pwa.forEach(x=>{if(!map.has(x.id)){map.set(x.id,x);added++}});
      if(added){localStorage.setItem(STORE,JSON.stringify([...map.values()]));window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{q1Cases:true,added}}));setTimeout(()=>window.MANTPRO?.render?.(),50)}
      localStorage.setItem(MARK,'1');return added;
    }catch(error){console.warn('MANTPRO carga Q1:',error);return 0}
  }
  const LOCAL={technicians:techs,assets:ASSETS,inventory:INVENTORY,procedures:PROCEDURES,maintenancePlans:PLANS,works:JOBS,progress:PROGRESS,deviations:DEVIATIONS,walks:WALKS,technicianEvaluations:EVALS,stockMoves:STOCK,talkCaptures:TALKS};
  const merge=(a,b)=>{const map=new Map((Array.isArray(a)?a:[]).map(x=>[x.id,x]));(Array.isArray(b)?b:[]).forEach(x=>{if(!map.has(x.id))map.set(x.id,x)});return [...map.values()]};
  async function localBridge(){
    if(/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent)||localStorage.getItem(LOCAL_MARK)==='1')return false;
    const bases=['http://127.0.0.1:8787','http://localhost:8787'];
    for(const base of bases)try{
      const controller=new AbortController(), timer=setTimeout(()=>controller.abort(),2200);
      const r=await fetch(base+'/api/data',{cache:'no-store',signal:controller.signal});clearTimeout(timer);if(!r.ok)continue;
      const result=await r.json(), current=result?.data&&typeof result.data==='object'?result.data:{};
      for(const key of Object.keys(LOCAL))current[key]=merge(current[key],LOCAL[key]);
      const put=await fetch(base+'/api/data',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:current,clientId:'github-q1-2026-cases-v2'})});
      if(!put.ok)continue;localStorage.setItem(LOCAL_MARK,'1');
      const t=document.getElementById('toast');if(t){t.textContent='Casos de enero a marzo vinculados con MANTPRO local para INFORME KPI.';t.hidden=false;setTimeout(()=>t.hidden=true,5000)}
      return true;
    }catch(error){console.debug('Puente local MANTPRO no disponible:',error)}
    return false;
  }
  function start(){loadPwa();setTimeout(localBridge,700);}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.MANTPRO_Q1_CASES={load:loadPwa,bridge:localBridge,records:pwa,local:LOCAL,build:'20260921-q1-cases-v5'};
})();