/* MANTPRO IA Cloud — fotografías universales en todos los informes.
   Incluye OT, informe diario, KPI/EHS, seguridad, caminatas y desviaciones. */
(()=>{
  'use strict';

  const BUILD='2026-07-23-universal-ehs-photo-reports';
  const $=(s,r=document)=>r.querySelector(s);
  const $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const fmt=v=>{if(!v)return'No registrado';const d=new Date(v);return Number.isNaN(d.valueOf())?'No registrado':d.toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short',hour12:false})};
  const records=()=>window.MANTPRO?.records?.()||[];
  const byType=t=>records().filter(x=>x.type===t);
  const linked=(t,id)=>byType(t).filter(x=>x.data?.jobId===id);
  const supervisor=()=>window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards';

  function dateKey(v){const d=new Date(v||Date.now());return Number.isNaN(d.valueOf())?'':[d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')}
  function recordDate(x){const d=x?.data||{};return d.recordedAt||d.actualStart||d.startAt||d.plannedStart||x?.at||''}
  function selectedDay(){return $('#ehs-report-date')?.value||$('#report-form [name="date"]')?.value||sessionStorage.getItem('mantpro-report-day')||new Date().toISOString().slice(0,10)}
  function sameDay(x,day){return dateKey(recordDate(x))===day}
  function uniqueEntries(entries){const seen=new Set();return entries.filter(x=>{const key=x.src;if(!key||seen.has(key))return false;seen.add(key);return true})}

  function rawPhoto(value){
    if(!value)return'';
    if(typeof value==='string')return value;
    if(Array.isArray(value))return rawPhoto(value[0]);
    if(typeof value==='object')return rawPhoto(value.dataUrl||value.dataURL||value.src||value.url||value.photo||value.image||value.base64||value.content||'');
    return'';
  }

  function photoCandidates(record){
    if(!record)return[];
    const d=record.data||{};
    const values=[record.photo,record.image,record.photos,record.images,record.attachments,d.photo,d.image,d.photos,d.images,d.attachments,d.photoData,d.imageData,d.evidence,d.evidences];
    const out=[];
    const add=v=>{
      if(!v)return;
      if(Array.isArray(v)){v.forEach(add);return}
      if(typeof v==='object'&&!rawPhoto(v)){Object.values(v).forEach(add);return}
      const p=rawPhoto(v);
      if(p&&!out.includes(p))out.push(p);
    };
    values.forEach(add);
    return out;
  }

  function entriesFrom(record,label,kind,context=''){
    return photoCandidates(record).map((src,index)=>({record,src,label:index?`${label} · Foto ${index+1}`:label,kind,context}));
  }

  function photoEntriesForSafety(safety){
    const d=safety?.data||{};
    const label=d.photoType||`${d.category||'Desviación'} · ${d.area||'Área no informada'}`;
    return entriesFrom(safety,label,'Seguridad',d.text||'');
  }

  function photoEntriesForWalk(walk){
    if(!walk)return[];
    const d=walk.data||{},entries=[];
    entries.push(...entriesFrom(walk,`Caminata · ${d.area||'Área no informada'}`,'Caminata',d.objective||''));
    byType('safety').filter(x=>x.data?.walkId===walk.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>{
      photoEntriesForSafety(x).forEach(p=>entries.push({...p,label:`Caminata · Hallazgo ${i+1} · ${p.label}`}));
    });
    return uniqueEntries(entries);
  }

  function photoEntriesForJob(job){
    if(!job)return[];
    const entries=[];
    entries.push(...entriesFrom(job,'Fotografía inicial de la orden','Inicial',job.data?.task||''));
    linked('progress',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>entries.push(...entriesFrom(x,x.data?.photoType||`Avance ${i+1}`,'Avance',x.data?.text||'')));
    linked('safety',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>photoEntriesForSafety(x).forEach(p=>entries.push({...p,label:`OT · Desviación ${i+1} · ${p.label}`})));
    linked('kpi',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>entries.push(...entriesFrom(x,`Evaluación KPI ${i+1} · ${x.data?.technician||'Técnico'}`,'KPI',x.data?.notes||'')));
    return uniqueEntries(entries);
  }

  function photoEntriesForKpi(kpi){
    if(!kpi)return[];
    const entries=[...entriesFrom(kpi,`Evidencia KPI · ${kpi.data?.technician||'Técnico'}`,'KPI',kpi.data?.notes||'')];
    const job=byType('job').find(x=>x.id===kpi.data?.jobId);
    if(job)photoEntriesForJob(job).forEach(p=>entries.push({...p,label:`OT asociada · ${p.label}`}));
    return uniqueEntries(entries);
  }

  function allPhotosForDay(day){
    const entries=[];
    byType('job').filter(x=>sameDay(x,day)).forEach(j=>entries.push(...photoEntriesForJob(j)));
    byType('safety').filter(x=>sameDay(x,day)&&!x.data?.jobId).forEach(x=>entries.push(...photoEntriesForSafety(x)));
    byType('walk').filter(x=>sameDay(x,day)).forEach(x=>entries.push(...photoEntriesForWalk(x)));
    byType('kpi').filter(x=>sameDay(x,day)).forEach(x=>entries.push(...entriesFrom(x,`KPI · ${x.data?.technician||'Técnico'}`,'KPI',x.data?.notes||'')));
    return uniqueEntries(entries);
  }

  function currentJob(){
    const stored=sessionStorage.getItem('mantpro-active-report-job');
    if(stored){const found=records().find(x=>x.id===stored&&x.type==='job');if(found)return found}
    const title=$('.report-sheet h1')?.textContent||'';
    return byType('job').find(j=>title.includes(j.data?.folio||'')&&title.includes(j.data?.equip||''))||null;
  }

  async function loadImage(src){
    return new Promise((resolve,reject)=>{
      const img=new Image();
      if(!String(src).startsWith('data:'))img.crossOrigin='anonymous';
      img.onload=()=>resolve(img);img.onerror=()=>reject(new Error('No se pudo cargar la fotografía'));img.src=src;
    });
  }

  async function toJpegData(src,max=1280,quality=.74){
    if(!src)throw new Error('Fotografía vacía');
    const img=await loadImage(src),iw=img.naturalWidth||img.width,ih=img.naturalHeight||img.height,scale=Math.min(1,max/Math.max(iw,ih));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(iw*scale));canvas.height=Math.max(1,Math.round(ih*scale));
    const ctx=canvas.getContext('2d',{alpha:false});ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/jpeg',quality);
  }

  async function optimizeInput(input,file){
    const src=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
    const data=await toJpegData(src,900,.60),blob=await (await fetch(data)).blob(),optimized=new File([blob],(file.name||'foto').replace(/\.[^.]+$/,'')+'.jpg',{type:'image/jpeg',lastModified:Date.now()});
    const dt=new DataTransfer();dt.items.add(optimized);input.files=dt.files;
  }

  document.addEventListener('change',async e=>{
    const input=e.target;if(!(input instanceof HTMLInputElement)||input.id!=='photo'||input.dataset.optimized==='yes')return;
    const file=input.files?.[0];if(!file)return;e.preventDefault();e.stopImmediatePropagation();
    try{input.dataset.optimized='yes';await optimizeInput(input,file);input.dispatchEvent(new Event('change',{bubbles:true}))}
    catch(error){console.warn('MANTPRO photo optimizer:',error);input.dataset.optimized='yes';input.dispatchEvent(new Event('change',{bubbles:true}))}
    finally{setTimeout(()=>delete input.dataset.optimized,0)}
  },true);

  function appendPhotoAnnex(){
    const sheet=$('.report-sheet');if(!sheet||!$('[data-pdf-job]',sheet))return;
    const job=currentJob();if(!job)return;const photos=photoEntriesForJob(job),signature=photos.map(p=>`${p.record?.id||''}:${p.src.length}:${p.src.slice(-24)}`).join('|')||'empty';
    const existing=$('#mantpro-photo-annex');if(existing?.dataset.signature===signature)return;existing?.remove();
    const block=document.createElement('section');block.id='mantpro-photo-annex';block.className='report-photo-annex';block.dataset.signature=signature;
    block.innerHTML=`<h2>Registro fotográfico (${photos.length})</h2>`+(photos.length?`<div class="report-photo-grid">${photos.map(p=>`<figure class="report-photo report-photo-fixed"><img src="${esc(p.src)}" alt="${esc(p.label)}" loading="eager"><figcaption><b>${esc(p.label)}</b><br><small>${fmt(p.record?.at)}</small></figcaption></figure>`).join('')}</div>`:'<div class="empty">No existen fotografías guardadas en esta orden.</div>');
    const button=$('[data-pdf-job]',sheet);sheet.insertBefore(block,button);
  }

  function reportCenter(){
    const form=$('#report-form'),app=$('#app');if(!form||!app||$('#mantpro-ehs-report-center'))return;
    const day=form.querySelector('[name="date"]')?.value||new Date().toISOString().slice(0,10),section=document.createElement('section');section.id='mantpro-ehs-report-center';section.className='section';
    section.innerHTML=`<h2>Informes KPI / EHS con fotografías</h2><div class="callout"><b>Registro fotográfico obligatorio:</b> los PDF incluyen imágenes de seguridad, caminatas, desvíos, OT y evidencias vinculadas a KPI.</div><form id="ehs-report-controls"><label>Fecha de los informes<input id="ehs-report-date" type="date" value="${esc(day)}"></label><div class="grid"><button type="button" class="primary" data-pdf-ehs>Informe KPI / EHS</button><button type="button" data-pdf-safety-day>Seguridad y desvíos</button><button type="button" data-pdf-walks-day>Caminatas</button><button type="button" data-pdf-kpi-day>KPI técnicos</button></div></form><div id="ehs-individual-reports" class="section"></div>`;
    form.insertAdjacentElement('afterend',section);refreshIndividualReports();
  }

  function refreshIndividualReports(){
    const box=$('#ehs-individual-reports');if(!box)return;const day=selectedDay(),safety=byType('safety').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(b.at)-new Date(a.at)),walks=byType('walk').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(b.at)-new Date(a.at)),kpis=byType('kpi').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(b.at)-new Date(a.at));
    box.innerHTML=`<h3>Informes individuales de la fecha</h3><div class="report-category"><b>Desviaciones / seguridad (${safety.length})</b><div class="list">${safety.length?safety.map(x=>`<button type="button" class="list-item" data-pdf-safety-id="${x.id}"><span>${esc(x.data?.category||'Desviación')} · ${esc(x.data?.area||'Área')}</span><small>${fmt(x.at)} · ${photoCandidates(x).length} foto(s)</small></button>`).join(''):'<div class="empty">Sin desvíos en la fecha.</div>'}</div></div><div class="report-category"><b>Caminatas (${walks.length})</b><div class="list">${walks.length?walks.map(x=>`<button type="button" class="list-item" data-pdf-walk-id="${x.id}"><span>${esc(x.data?.area||'Caminata')}</span><small>${fmt(x.data?.startAt||x.at)} · ${photoEntriesForWalk(x).length} foto(s)</small></button>`).join(''):'<div class="empty">Sin caminatas en la fecha.</div>'}</div></div><div class="report-category"><b>Evaluaciones KPI (${kpis.length})</b><div class="list">${kpis.length?kpis.map(x=>`<button type="button" class="list-item" data-pdf-kpi-id="${x.id}"><span>${esc(x.data?.technician||'Técnico')} · ${Number(x.data?.score||0)}%</span><small>${fmt(x.at)} · ${photoEntriesForKpi(x).length} evidencia(s)</small></button>`).join(''):'<div class="empty">Sin evaluaciones KPI en la fecha.</div>'}</div></div>`;
  }

  let renderTimer;
  const refreshUi=()=>{clearTimeout(renderTimer);renderTimer=setTimeout(()=>{appendPhotoAnnex();reportCenter();refreshIndividualReports()},100)};
  const startObserver=()=>{new MutationObserver(refreshUi).observe($('#app')||document.body,{childList:true,subtree:true});refreshUi()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',startObserver);else startObserver();

  document.addEventListener('click',e=>{
    const open=e.target.closest('[data-open-job],[data-report-job],[data-open-walk]');
    if(open?.dataset.openJob||open?.dataset.reportJob)sessionStorage.setItem('mantpro-active-report-job',open.dataset.openJob||open.dataset.reportJob);
    if(open?.dataset.openWalk)sessionStorage.setItem('mantpro-active-report-walk',open.dataset.openWalk);
  },true);
  document.addEventListener('submit',e=>{if(e.target?.id==='report-form'){const day=e.target.querySelector('[name="date"]')?.value;if(day)sessionStorage.setItem('mantpro-report-day',day)}},true);
  document.addEventListener('change',e=>{if(e.target?.id==='ehs-report-date'){sessionStorage.setItem('mantpro-report-day',e.target.value);refreshIndividualReports()}},true);

  function pdfName(value){return String(value||'MANTPRO').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9_-]+/gi,'_').replace(/^_+|_+$/g,'')+'.pdf'}
  function writer(title,subtitle){
    if(!window.jspdf?.jsPDF)throw new Error('El generador PDF no está disponible. Cierre y vuelva a abrir MANTPRO.');
    const doc=new window.jspdf.jsPDF({unit:'mm',format:'a4',compress:true}),margin=15,width=180;let y=18;
    const header=first=>{doc.setFillColor(18,27,35);doc.rect(0,0,210,first?38:18,'F');doc.setTextColor(255,139,24);doc.setFont('helvetica','bold');doc.setFontSize(first?18:11);doc.text('MANTPRO IA',margin,first?17:11);doc.setTextColor(255,255,255);if(first){doc.setFontSize(15);doc.text(title,margin,27,{maxWidth:width});doc.setFontSize(9);doc.text(subtitle||'',margin,34,{maxWidth:width})}y=first?46:25};
    const ensure=h=>{if(y+h>278){doc.addPage();header(false)}};
    const paragraph=(text,opt={})=>{const size=opt.size||10,lh=opt.lineHeight||4.6;doc.setFont('helvetica',opt.bold?'bold':'normal');doc.setFontSize(size);doc.setTextColor(...(opt.color||[33,43,54]));const lines=[];String(text??'No informado').replace(/\r/g,'').split('\n').forEach(p=>lines.push(...doc.splitTextToSize(p||' ',width)));ensure(lines.length*lh+2);doc.text(lines,margin,y);y+=lines.length*lh+(opt.after??2)};
    const section=text=>{ensure(12);y+=3;doc.setFillColor(238,242,245);doc.rect(margin,y-5,width,9,'F');doc.setTextColor(18,61,92);doc.setFont('helvetica','bold');doc.setFontSize(12);doc.text(String(text),margin+3,y+1);y+=9};
    const item=(head,body)=>{ensure(14);doc.setDrawColor(205,214,221);doc.setFillColor(249,250,251);doc.roundedRect(margin,y-4,width,7,1.5,1.5,'FD');doc.setTextColor(18,61,92);doc.setFont('helvetica','bold');doc.setFontSize(10);const lines=doc.splitTextToSize(String(head),width-6);doc.text(lines,margin+3,y);y+=lines.length*4.2+3;paragraph(body,{size:9.5,after:4})};
    const photo=async(entry,index)=>{try{const data=await toJpegData(entry.src,1500,.78),img=await loadImage(data),ratio=(img.naturalWidth||img.width)/(img.naturalHeight||img.height);let w=150,h=w/ratio;if(h>100){h=100;w=h*ratio}ensure(h+24);paragraph(`${index+1}. ${entry.label}`,{bold:true,size:9,after:2});doc.setDrawColor(160,170,180);doc.rect(margin,y,w,h);doc.addImage(data,'JPEG',margin,y,w,h,undefined,'FAST');y+=h+4;if(entry.context)paragraph(`Antecedente: ${entry.context}`,{size:8,color:[70,81,92],after:1});paragraph(`Registro: ${fmt(entry.record?.at)}`,{size:8,color:[90,101,112],after:4});return true}catch(error){console.warn('MANTPRO PDF photo:',error);paragraph(`${index+1}. ${entry.label}: no fue posible incrustar esta fotografía.`,{size:8,color:[150,55,55]});return false}};
    const finish=name=>{const pages=doc.getNumberOfPages();for(let p=1;p<=pages;p++){doc.setPage(p);doc.setDrawColor(205,214,221);doc.line(margin,287,195,287);doc.setFont('helvetica','normal');doc.setFontSize(8);doc.setTextColor(90,101,112);doc.text(`Supervisor: ${supervisor()}`,margin,292);doc.text(`Página ${p} de ${pages}`,195,292,{align:'right'})}doc.save(pdfName(name))};
    header(true);return{paragraph,section,item,photo,finish};
  }

  function pauseMs(job){return (job.data?.pauses||[]).reduce((n,p)=>n+(p.end?new Date(p.end)-new Date(p.start):0),0)}
  function duration(start,end){if(!start||!end)return'No registrado';const ms=Math.max(0,new Date(end)-new Date(start)),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000);return `${h} h ${String(m).padStart(2,'0')} min`}
  function netDuration(job){const d=job.data||{};if(!d.actualStart||!d.actualEnd)return'No registrado';const ms=Math.max(0,new Date(d.actualEnd)-new Date(d.actualStart)-pauseMs(job)),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000);return `${h} h ${String(m).padStart(2,'0')} min`}
  function jobStatus(job){const d=job.data||{};if(d.actualEnd)return'Terminado';if(d.pauseStartAt)return'Pausado';if(d.actualStart)return'En ejecución';if(d.lotoStart)return'En bloqueo';if(d.docsStart)return'Documentación';return'Programado'}
  async function addPhotos(pdf,photos,emptyText='No existen fotografías guardadas para este informe.'){if(!photos.length){pdf.paragraph(emptyText);return 0}let ok=0;for(let i=0;i<photos.length;i++)if(await pdf.photo(photos[i],i))ok++;return ok}

  async function downloadJobPdfFixed(){
    const job=currentJob();if(!job)throw new Error('No fue posible identificar la orden de trabajo. Vuelva a abrir el informe desde la lista de OT.');
    const d=job.data||{},progress=linked('progress',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)),safety=linked('safety',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)),kpis=linked('kpi',job.id),photos=photoEntriesForJob(job),pdf=writer('Informe técnico de mantención',`${d.folio||'OT'} · ${d.equip||'Equipo no informado'}`);
    pdf.section('Identificación');pdf.paragraph(`Supervisor: ${supervisor()}\nPlanta / área: ${d.plant||'No informado'} / ${d.area||'No informado'}\nEquipo / TAG: ${d.equip||'No informado'}\nTrabajo: ${d.task||'No informado'}\nEstado: ${jobStatus(job)}\nFecha de emisión: ${fmt(new Date().toISOString())}`);
    pdf.section('Horario real y tiempos');pdf.item('Documentación de seguridad',`Inicio: ${fmt(d.docsStart)}\nTérmino: ${fmt(d.docsEnd)}\nDuración: ${duration(d.docsStart,d.docsEnd)}`);pdf.item('Bloqueo / aislamiento LOTO',`Inicio: ${fmt(d.lotoStart)}\nEnergía cero verificada: ${fmt(d.zeroVerifiedAt)}\nTérmino: ${fmt(d.lotoEnd)}\nDuración: ${duration(d.lotoStart,d.lotoEnd)}`);pdf.item('Ejecución real del trabajo',`Inicio: ${fmt(d.actualStart)}\nTérmino: ${fmt(d.actualEnd)}\nDuración neta: ${netDuration(job)}\nAvance final: ${Number(d.progress||0)}%`);
    pdf.section('Actividades realizadas');if(!progress.length)pdf.paragraph('No informado.');progress.forEach((x,i)=>pdf.item(`Avance ${i+1} · ${x.data?.percent||0}% · ${fmt(x.at)}`,`${x.data?.text||'No informado'}${x.data?.findings?'\nHallazgo: '+x.data.findings:''}`));
    pdf.section('Desviaciones de seguridad');if(!safety.length)pdf.paragraph('No se registraron desviaciones para esta OT.');safety.forEach((x,i)=>pdf.item(`Desviación ${i+1} · Riesgo ${x.data?.risk||'No informado'} · ${fmt(x.at)}`,`Categoría: ${x.data?.category||'No informada'}\nHallazgo: ${x.data?.text||'No informado'}\nAcción inmediata: ${x.data?.action||'No informada'}\nRecomendación: ${x.data?.recommendation||'No informada'}`));
    pdf.section('Evaluación de técnicos');if(!kpis.length)pdf.paragraph('No informado.');kpis.forEach(x=>pdf.item(`${x.data?.technician||'Técnico'} · ${x.data?.score||0}%`,x.data?.notes||'Sin observaciones.'));
    pdf.section(`Registro fotográfico (${photos.length})`);const ok=await addPhotos(pdf,photos,'No existen fotografías guardadas en esta orden.');pdf.section('Trazabilidad');pdf.paragraph(`Fotografías encontradas: ${photos.length}. Fotografías incrustadas correctamente: ${ok}.`);pdf.finish(`Informe_${d.folio||job.id}`);showToast(`Informe descargado con ${ok} fotografía(s).`);
  }

  async function downloadDailyPdfFixed(){
    const day=selectedDay(),jobs=byType('job').filter(x=>sameDay(x,day)),safety=byType('safety').filter(x=>sameDay(x,day)),walks=byType('walk').filter(x=>sameDay(x,day)),kpis=byType('kpi').filter(x=>sameDay(x,day)),photos=allPhotosForDay(day),pdf=writer('Informe general diario',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    pdf.section('Resumen ejecutivo');pdf.paragraph(`Supervisor: ${supervisor()}\nTrabajos: ${jobs.length}\nTrabajos terminados: ${jobs.filter(x=>x.data?.actualEnd).length}\nDesviaciones: ${safety.length}\nCaminatas: ${walks.length}\nEvaluaciones KPI: ${kpis.length}\nFotografías: ${photos.length}\nFecha de emisión: ${fmt(new Date().toISOString())}`);
    pdf.section('Trabajos de la jornada');if(!jobs.length)pdf.paragraph('Sin trabajos registrados para la fecha.');jobs.forEach(j=>pdf.item(`${j.data?.folio||'OT'} · ${j.data?.equip||'Equipo'}`,`Trabajo: ${j.data?.task||'No informado'}\nInicio real: ${fmt(j.data?.actualStart)}\nTérmino real: ${fmt(j.data?.actualEnd)}\nAvance: ${Number(j.data?.progress||0)}%\nEstado: ${jobStatus(j)}`));
    pdf.section('Seguridad y desvíos');if(!safety.length)pdf.paragraph('Sin desviaciones registradas.');safety.forEach((x,i)=>pdf.item(`Desviación ${i+1} · ${x.data?.risk||'Riesgo no informado'}`,`${x.data?.category||'Sin categoría'} · ${x.data?.area||'Área no informada'}\n${x.data?.text||'Sin descripción'}\nAcción: ${x.data?.action||'No informada'}`));
    pdf.section('Caminatas');if(!walks.length)pdf.paragraph('Sin caminatas registradas.');walks.forEach((x,i)=>pdf.item(`Caminata ${i+1} · ${x.data?.area||'Área no informada'}`,`Inicio: ${fmt(x.data?.startAt||x.at)}\nTérmino: ${fmt(x.data?.endAt)}\nObjetivo: ${x.data?.objective||'No informado'}\nParticipantes: ${x.data?.participants||'No informados'}`));
    pdf.section('KPI técnicos');if(!kpis.length)pdf.paragraph('Sin evaluaciones KPI.');kpis.forEach(x=>pdf.item(`${x.data?.technician||'Técnico'} · ${Number(x.data?.score||0)}%`,x.data?.notes||'Sin observaciones.'));
    pdf.section(`Registro fotográfico diario (${photos.length})`);const ok=await addPhotos(pdf,photos,'No existen fotografías guardadas para la jornada.');pdf.finish(`Informe_Diario_${day}`);showToast(`Informe diario descargado con ${ok} fotografía(s).`);
  }

  async function downloadSafetyPdf(record){
    if(!record)throw new Error('Desviación no disponible.');const d=record.data||{},photos=photoEntriesForSafety(record),pdf=writer('Informe de desviación de seguridad',`${d.category||'Desviación'} · ${d.area||'Área no informada'}`);
    pdf.section('Identificación');pdf.paragraph(`Supervisor: ${supervisor()}\nFecha y hora: ${fmt(record.at)}\nOrigen: ${d.origin||'No informado'}\nPlanta: ${d.plant||'No informada'}\nÁrea: ${d.area||'No informada'}\nCategoría: ${d.category||'No informada'}\nNivel de riesgo: ${d.risk||'No informado'}`);
    pdf.section('Hallazgo y control');pdf.item('Descripción objetiva',d.text||'No informada');pdf.item('Acción inmediata',d.action||'No informada');pdf.item('Medida correctiva / recomendación',d.recommendation||'No informada');pdf.item('Seguimiento',`Responsable: ${d.responsible||'No informado'}\nFecha compromiso: ${d.dueDate||'No informada'}\nEstado: ${d.closedAt?'Cerrada':'Abierta'}\nCierre verificado: ${fmt(d.closedAt)}`);
    pdf.section(`Evidencia fotográfica (${photos.length})`);const ok=await addPhotos(pdf,photos);pdf.finish(`Desviacion_${d.category||record.id}_${dateKey(record.at)}`);showToast(`Informe de desviación con ${ok} fotografía(s).`);
  }

  async function downloadWalkPdf(walk){
    if(!walk)throw new Error('Caminata no disponible.');const d=walk.data||{},findings=byType('safety').filter(x=>x.data?.walkId===walk.id).sort((a,b)=>new Date(a.at)-new Date(b.at)),photos=photoEntriesForWalk(walk),pdf=writer('Informe de caminata de seguridad',`${d.plant||'Planta'} · ${d.area||'Área no informada'}`);
    pdf.section('Identificación');pdf.paragraph(`Supervisor: ${supervisor()}\nInicio: ${fmt(d.startAt||walk.at)}\nTérmino: ${fmt(d.endAt)}\nPlanta: ${d.plant||'No informada'}\nÁreas recorridas: ${d.area||'No informadas'}\nObjetivo: ${d.objective||'No informado'}\nParticipantes: ${d.participants||'No informados'}`);
    pdf.section(`Hallazgos (${findings.length})`);if(!findings.length)pdf.paragraph('No se registraron hallazgos durante la caminata.');findings.forEach((x,i)=>pdf.item(`Hallazgo ${i+1} · ${x.data?.category||'Sin categoría'} · Riesgo ${x.data?.risk||'No informado'}`,`Ubicación: ${x.data?.area||'No informada'}\nDescripción: ${x.data?.text||'No informada'}\nAcción: ${x.data?.action||'No informada'}\nRecomendación: ${x.data?.recommendation||'No informada'}\nResponsable: ${x.data?.responsible||'No informado'}`));
    pdf.section(`Registro fotográfico de la caminata (${photos.length})`);const ok=await addPhotos(pdf,photos);pdf.finish(`Caminata_${dateKey(d.startAt||walk.at)}_${d.area||walk.id}`);showToast(`Informe de caminata con ${ok} fotografía(s).`);
  }

  async function downloadKpiPdf(kpi){
    if(!kpi)throw new Error('Evaluación KPI no disponible.');const d=kpi.data||{},job=byType('job').find(x=>x.id===d.jobId),photos=photoEntriesForKpi(kpi),pdf=writer('Informe KPI de desempeño técnico',`${d.technician||'Técnico'} · ${Number(d.score||0)}%`);
    pdf.section('Identificación');pdf.paragraph(`Supervisor: ${supervisor()}\nTécnico: ${d.technician||'No informado'}\nFecha de evaluación: ${fmt(kpi.at)}\nOrden asociada: ${job?.data?.folio||'No informada'}\nEquipo: ${job?.data?.equip||'No informado'}\nPuntaje final: ${Number(d.score||0)}%`);
    pdf.section('Criterios de desempeño');pdf.item('Seguridad y controles críticos (30%)',`${d.safety||'No informado'} / 5`);pdf.item('Calidad técnica (25%)',`${d.quality||'No informado'} / 5`);pdf.item('Cumplimiento (15%)',`${d.compliance||'No informado'} / 5`);pdf.item('Productividad responsable (10%)',`${d.productivity||'No informado'} / 5`);pdf.item('Documentación (10%)',`${d.documentation||'No informado'} / 5`);pdf.item('Coordinación (10%)',`${d.communication||'No informado'} / 5`);
    pdf.section('Observaciones');pdf.paragraph(`Correcto a la primera: ${d.firstTimeRight?'Sí':'No'}\nRetrabajo: ${d.rework?'Sí':'No'}\nFactores externos: ${d.externalFactors?'Sí':'No'}\nFortalezas / observaciones: ${d.notes||'No informadas'}\nCapacitación requerida: ${d.training||'No informada'}`);
    pdf.section(`Evidencias fotográficas vinculadas (${photos.length})`);const ok=await addPhotos(pdf,photos,'No existen fotografías directas ni evidencias de la OT asociada.');pdf.finish(`KPI_${d.technician||kpi.id}_${dateKey(kpi.at)}`);showToast(`Informe KPI con ${ok} fotografía(s).`);
  }

  async function downloadSafetyDayPdf(day){
    const safety=byType('safety').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(a.at)-new Date(b.at)),photos=uniqueEntries(safety.flatMap(photoEntriesForSafety)),pdf=writer('Informe diario de seguridad y desvíos',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    pdf.section('Indicadores EHS');const high=safety.filter(x=>/alto|crítico/i.test(x.data?.risk||'')).length,positive=safety.filter(x=>/positiva/i.test(x.data?.category||'')).length,closed=safety.filter(x=>x.data?.closedAt).length;pdf.paragraph(`Supervisor: ${supervisor()}\nDesviaciones / observaciones: ${safety.length}\nRiesgos altos o críticos: ${high}\nObservaciones positivas: ${positive}\nCerradas: ${closed}\nAbiertas: ${safety.length-closed}\nFotografías: ${photos.length}`);
    pdf.section('Detalle de seguridad');if(!safety.length)pdf.paragraph('Sin registros de seguridad en la fecha.');safety.forEach((x,i)=>pdf.item(`${i+1}. ${x.data?.category||'Desviación'} · Riesgo ${x.data?.risk||'No informado'}`,`Hora: ${fmt(x.at)}\nOrigen: ${x.data?.origin||'No informado'}\nÁrea: ${x.data?.area||'No informada'}\nHallazgo: ${x.data?.text||'No informado'}\nAcción: ${x.data?.action||'No informada'}\nRecomendación: ${x.data?.recommendation||'No informada'}`));
    pdf.section(`Evidencia fotográfica EHS (${photos.length})`);const ok=await addPhotos(pdf,photos);pdf.finish(`Seguridad_Desvios_${day}`);showToast(`Informe de seguridad con ${ok} fotografía(s).`);
  }

  async function downloadWalksDayPdf(day){
    const walks=byType('walk').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(a.at)-new Date(b.at)),photos=uniqueEntries(walks.flatMap(photoEntriesForWalk)),pdf=writer('Informe diario de caminatas de seguridad',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    pdf.section('Resumen');pdf.paragraph(`Supervisor: ${supervisor()}\nCaminatas realizadas: ${walks.length}\nFotografías: ${photos.length}`);if(!walks.length)pdf.paragraph('Sin caminatas registradas en la fecha.');for(const [i,w] of walks.entries()){const findings=byType('safety').filter(x=>x.data?.walkId===w.id);pdf.section(`Caminata ${i+1} · ${w.data?.area||'Área no informada'}`);pdf.paragraph(`Inicio: ${fmt(w.data?.startAt||w.at)}\nTérmino: ${fmt(w.data?.endAt)}\nObjetivo: ${w.data?.objective||'No informado'}\nParticipantes: ${w.data?.participants||'No informados'}\nHallazgos: ${findings.length}`);findings.forEach((x,n)=>pdf.item(`Hallazgo ${n+1} · ${x.data?.category||'Sin categoría'}`,`${x.data?.text||'No informado'}\nRiesgo: ${x.data?.risk||'No informado'}\nAcción: ${x.data?.action||'No informada'}`))}
    pdf.section(`Registro fotográfico de caminatas (${photos.length})`);const ok=await addPhotos(pdf,photos);pdf.finish(`Caminatas_Seguridad_${day}`);showToast(`Informe de caminatas con ${ok} fotografía(s).`);
  }

  async function downloadKpiDayPdf(day){
    const kpis=byType('kpi').filter(x=>sameDay(x,day)).sort((a,b)=>new Date(a.at)-new Date(b.at)),photos=uniqueEntries(kpis.flatMap(photoEntriesForKpi)),pdf=writer('Informe diario KPI de técnicos',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    const avg=kpis.length?Math.round(kpis.reduce((n,x)=>n+Number(x.data?.score||0),0)/kpis.length):0;pdf.section('Resumen KPI');pdf.paragraph(`Supervisor: ${supervisor()}\nEvaluaciones: ${kpis.length}\nPromedio: ${kpis.length?avg+'%':'No informado'}\nRetrabajos: ${kpis.filter(x=>x.data?.rework).length}\nCorrecto a la primera: ${kpis.filter(x=>x.data?.firstTimeRight).length}\nEvidencias fotográficas vinculadas: ${photos.length}`);
    pdf.section('Detalle por técnico');if(!kpis.length)pdf.paragraph('Sin evaluaciones KPI en la fecha.');kpis.forEach((x,i)=>pdf.item(`${i+1}. ${x.data?.technician||'Técnico'} · ${Number(x.data?.score||0)}%`,`Seguridad: ${x.data?.safety||'-'}/5 · Calidad: ${x.data?.quality||'-'}/5 · Cumplimiento: ${x.data?.compliance||'-'}/5\nProductividad: ${x.data?.productivity||'-'}/5 · Documentación: ${x.data?.documentation||'-'}/5 · Coordinación: ${x.data?.communication||'-'}/5\nObservaciones: ${x.data?.notes||'No informadas'}\nCapacitación: ${x.data?.training||'No informada'}`));
    pdf.section(`Evidencias fotográficas KPI (${photos.length})`);const ok=await addPhotos(pdf,photos,'No existen fotografías directas ni evidencias asociadas a las OT evaluadas.');pdf.finish(`KPI_Tecnicos_${day}`);showToast(`Informe KPI con ${ok} fotografía(s).`);
  }

  async function downloadEhsPdf(day){
    const safety=byType('safety').filter(x=>sameDay(x,day)),walks=byType('walk').filter(x=>sameDay(x,day)),kpis=byType('kpi').filter(x=>sameDay(x,day)),jobs=byType('job').filter(x=>sameDay(x,day)),photos=allPhotosForDay(day),pdf=writer('Informe KPI / EHS',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    const high=safety.filter(x=>/alto|crítico/i.test(x.data?.risk||'')).length,closed=safety.filter(x=>x.data?.closedAt).length,avg=kpis.length?Math.round(kpis.reduce((n,x)=>n+Number(x.data?.score||0),0)/kpis.length):0;
    pdf.section('Panel KPI / EHS');pdf.paragraph(`Supervisor: ${supervisor()}\nTrabajos: ${jobs.length}\nCaminatas: ${walks.length}\nDesviaciones / observaciones: ${safety.length}\nRiesgos altos o críticos: ${high}\nCierre de desvíos: ${safety.length?Math.round(closed/safety.length*100)+'%':'No informado'}\nEvaluaciones técnicas: ${kpis.length}\nPromedio KPI técnico: ${kpis.length?avg+'%':'No informado'}\nFotografías: ${photos.length}`);
    pdf.section('Seguridad y desvíos');if(!safety.length)pdf.paragraph('Sin registros.');safety.forEach((x,i)=>pdf.item(`${i+1}. ${x.data?.category||'Desviación'} · ${x.data?.risk||'Riesgo no informado'}`,`${x.data?.area||'Área no informada'}\n${x.data?.text||'Sin descripción'}\nAcción: ${x.data?.action||'No informada'}\nResponsable: ${x.data?.responsible||'No informado'}`));
    pdf.section('Caminatas');if(!walks.length)pdf.paragraph('Sin caminatas.');walks.forEach((x,i)=>pdf.item(`${i+1}. ${x.data?.area||'Área no informada'}`,`Inicio: ${fmt(x.data?.startAt||x.at)}\nTérmino: ${fmt(x.data?.endAt)}\nObjetivo: ${x.data?.objective||'No informado'}\nHallazgos: ${byType('safety').filter(s=>s.data?.walkId===x.id).length}`));
    pdf.section('KPI de técnicos');if(!kpis.length)pdf.paragraph('Sin evaluaciones.');kpis.forEach((x,i)=>pdf.item(`${i+1}. ${x.data?.technician||'Técnico'} · ${Number(x.data?.score||0)}%`,x.data?.notes||'Sin observaciones.'));
    pdf.section(`Registro fotográfico integral (${photos.length})`);const ok=await addPhotos(pdf,photos);pdf.section('Control de integridad');pdf.paragraph(`Fotografías encontradas: ${photos.length}. Fotografías incrustadas: ${ok}. Las imágenes se obtienen de OT, avances, seguridad, caminatas, desvíos y evidencias vinculadas a KPI.`);pdf.finish(`KPI_EHS_${day}`);showToast(`Informe KPI / EHS con ${ok} fotografía(s).`);
  }

  function showToast(text){const t=$('#toast');if(!t){alert(text);return}t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,4200)}
  async function runButton(button,text,task){button.disabled=true;const old=button.textContent;button.textContent=text;try{await task()}catch(err){console.error(err);alert(err.message||'No fue posible generar el informe.')}finally{button.disabled=false;button.textContent=old}}

  document.addEventListener('click',e=>{
    const button=e.target.closest('[data-pdf-job],[data-pdf-daily],[data-pdf-ehs],[data-pdf-safety-day],[data-pdf-walks-day],[data-pdf-kpi-day],[data-pdf-safety-id],[data-pdf-walk-id],[data-pdf-kpi-id]');if(!button)return;
    e.preventDefault();e.stopImmediatePropagation();const day=selectedDay();
    if(button.matches('[data-pdf-job]'))return void runButton(button,'Preparando fotografías…',downloadJobPdfFixed);
    if(button.matches('[data-pdf-daily]'))return void runButton(button,'Preparando fotografías…',downloadDailyPdfFixed);
    if(button.matches('[data-pdf-ehs]'))return void runButton(button,'Generando KPI / EHS…',()=>downloadEhsPdf(day));
    if(button.matches('[data-pdf-safety-day]'))return void runButton(button,'Generando seguridad…',()=>downloadSafetyDayPdf(day));
    if(button.matches('[data-pdf-walks-day]'))return void runButton(button,'Generando caminatas…',()=>downloadWalksDayPdf(day));
    if(button.matches('[data-pdf-kpi-day]'))return void runButton(button,'Generando KPI…',()=>downloadKpiDayPdf(day));
    if(button.dataset.pdfSafetyId)return void runButton(button,'Generando desvío…',()=>downloadSafetyPdf(records().find(x=>x.id===button.dataset.pdfSafetyId)));
    if(button.dataset.pdfWalkId)return void runButton(button,'Generando caminata…',()=>downloadWalkPdf(records().find(x=>x.id===button.dataset.pdfWalkId)));
    if(button.dataset.pdfKpiId)return void runButton(button,'Generando KPI…',()=>downloadKpiPdf(records().find(x=>x.id===button.dataset.pdfKpiId)));
  },true);

  window.MANTPRO_PHOTO_REPORT_FIX={build:BUILD,photoCandidates,photoEntriesForJob,photoEntriesForSafety,photoEntriesForWalk,photoEntriesForKpi,allPhotosForDay,downloadJobPdfFixed,downloadDailyPdfFixed,downloadEhsPdf,downloadSafetyDayPdf,downloadWalksDayPdf,downloadKpiDayPdf,downloadSafetyPdf,downloadWalkPdf,downloadKpiPdf};
})();
