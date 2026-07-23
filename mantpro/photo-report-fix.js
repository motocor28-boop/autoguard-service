/* MANTPRO IA Cloud — corrección robusta de fotografías en informes.
   - Optimiza nuevas imágenes antes de que app.js las guarde.
   - Reconoce fotografías de versiones anteriores.
   - Inserta anexo fotográfico en la vista del informe.
   - Genera PDF de OT y diario esperando que cada imagen esté cargada. */
(()=>{
  'use strict';

  const BUILD='2026-07-23-photo-fix';
  const $=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const fmt=v=>{if(!v)return'No registrado';const d=new Date(v);return Number.isNaN(d.valueOf())?'No registrado':d.toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short',hour12:false})};
  const records=()=>window.MANTPRO?.records?.()||[];
  const byType=t=>records().filter(x=>x.type===t);
  const linked=(t,id)=>byType(t).filter(x=>x.data?.jobId===id);

  function rawPhoto(value){
    if(!value)return'';
    if(typeof value==='string')return value;
    if(Array.isArray(value))return rawPhoto(value[0]);
    if(typeof value==='object')return rawPhoto(value.dataUrl||value.dataURL||value.src||value.url||value.photo||value.image||value.base64||'');
    return'';
  }

  function photoCandidates(record){
    if(!record)return[];
    const d=record.data||{};
    const values=[record.photo,record.image,record.photos,record.images,record.attachments,d.photo,d.image,d.photos,d.images,d.attachments,d.photoData,d.imageData];
    const out=[];
    const add=v=>{
      if(!v)return;
      if(Array.isArray(v)){v.forEach(add);return}
      const p=rawPhoto(v);
      if(p&&!out.includes(p))out.push(p);
    };
    values.forEach(add);
    return out;
  }

  function photoEntriesForJob(job){
    if(!job)return[];
    const entries=[];
    const add=(record,label,kind)=>photoCandidates(record).forEach((src,index)=>entries.push({record,src,label:index?`${label} ${index+1}`:label,kind}));
    add(job,'Fotografía inicial de la orden','Inicial');
    linked('progress',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>add(x,x.data?.photoType||`Avance ${i+1}`,'Avance'));
    linked('safety',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)).forEach((x,i)=>add(x,x.data?.photoType||`Evidencia de seguridad ${i+1}`,'Seguridad'));
    const seen=new Set();
    return entries.filter(x=>{const key=x.src;if(seen.has(key))return false;seen.add(key);return true});
  }

  function dateKey(v){const d=new Date(v||Date.now());return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')}
  function allPhotosForDay(day){
    const entries=[];
    byType('job').filter(j=>dateKey(j.data?.actualStart||j.at)===day).forEach(j=>entries.push(...photoEntriesForJob(j)));
    byType('safety').filter(x=>!x.data?.jobId&&dateKey(x.at)===day).forEach((x,i)=>photoCandidates(x).forEach((src,n)=>entries.push({record:x,src,label:x.data?.photoType||`Desviación independiente ${i+1}${n?` · Foto ${n+1}`:''}`,kind:'Seguridad'})));
    const seen=new Set();return entries.filter(x=>{if(seen.has(x.src))return false;seen.add(x.src);return true});
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
      img.onload=()=>resolve(img);
      img.onerror=()=>reject(new Error('No se pudo cargar la fotografía'));
      img.src=src;
    });
  }

  async function toJpegData(src,max=1280,quality=.74){
    if(!src)throw new Error('Fotografía vacía');
    const img=await loadImage(src);
    const scale=Math.min(1,max/Math.max(img.naturalWidth||img.width,img.naturalHeight||img.height));
    const canvas=document.createElement('canvas');
    canvas.width=Math.max(1,Math.round((img.naturalWidth||img.width)*scale));
    canvas.height=Math.max(1,Math.round((img.naturalHeight||img.height)*scale));
    const ctx=canvas.getContext('2d',{alpha:false});
    ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/jpeg',quality);
  }

  async function optimizeInput(input,file){
    const src=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=reject;r.readAsDataURL(file)});
    const data=await toJpegData(src,900,.60);
    const blob=await (await fetch(data)).blob();
    const optimized=new File([blob],(file.name||'foto').replace(/\.[^.]+$/,'')+'.jpg',{type:'image/jpeg',lastModified:Date.now()});
    const dt=new DataTransfer();dt.items.add(optimized);input.files=dt.files;
  }

  document.addEventListener('change',async e=>{
    const input=e.target;
    if(!(input instanceof HTMLInputElement)||input.id!=='photo'||input.dataset.optimized==='yes')return;
    const file=input.files?.[0];if(!file)return;
    e.preventDefault();e.stopImmediatePropagation();
    try{
      input.dataset.optimized='yes';
      await optimizeInput(input,file);
      input.dispatchEvent(new Event('change',{bubbles:true}));
    }catch(error){
      console.warn('MANTPRO photo optimizer:',error);
      input.dataset.optimized='yes';
      input.dispatchEvent(new Event('change',{bubbles:true}));
    }finally{setTimeout(()=>delete input.dataset.optimized,0)}
  },true);

  function appendPhotoAnnex(){
    const sheet=$('.report-sheet');if(!sheet||!$('[data-pdf-job]',sheet))return;
    const job=currentJob();if(!job)return;
    const photos=photoEntriesForJob(job);
    $('#mantpro-photo-annex')?.remove();
    const block=document.createElement('section');block.id='mantpro-photo-annex';block.className='report-photo-annex';
    block.innerHTML=`<h2>Registro fotográfico (${photos.length})</h2>`+(photos.length?`<div class="report-photo-grid">${photos.map(p=>`<figure class="report-photo report-photo-fixed"><img src="${esc(p.src)}" alt="${esc(p.label)}" loading="eager"><figcaption><b>${esc(p.label)}</b><br><small>${fmt(p.record?.at)}</small></figcaption></figure>`).join('')}</div>`:'<div class="empty">No existen fotografías guardadas en esta orden. Las fotos tomadas pero no guardadas deben adjuntarse nuevamente.</div>');
    const button=$('[data-pdf-job]',sheet);sheet.insertBefore(block,button);
  }

  let annexTimer;
  const observer=new MutationObserver(()=>{clearTimeout(annexTimer);annexTimer=setTimeout(appendPhotoAnnex,80)});
  const startObserver=()=>{observer.observe(document.getElementById('app')||document.body,{childList:true,subtree:true});appendPhotoAnnex()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',startObserver);else startObserver();

  document.addEventListener('click',e=>{
    const open=e.target.closest('[data-open-job],[data-report-job]');
    const id=open?.dataset.openJob||open?.dataset.reportJob;
    if(id)sessionStorage.setItem('mantpro-active-report-job',id);
  },true);
  document.addEventListener('submit',e=>{if(e.target?.id==='report-form'){const day=e.target.querySelector('[name="date"]')?.value;if(day)sessionStorage.setItem('mantpro-report-day',day)}},true);

  function pdfName(value){return String(value||'MANTPRO').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9_-]+/gi,'_').replace(/^_+|_+$/g,'')+'.pdf'}

  function writer(title,subtitle){
    if(!window.jspdf?.jsPDF)throw new Error('El generador PDF no está disponible. Cierre y vuelva a abrir MANTPRO.');
    const doc=new window.jspdf.jsPDF({unit:'mm',format:'a4',compress:true}),margin=15,width=180;let y=18;
    const header=first=>{doc.setFillColor(18,27,35);doc.rect(0,0,210,first?38:18,'F');doc.setTextColor(255,139,24);doc.setFont('helvetica','bold');doc.setFontSize(first?18:11);doc.text('MANTPRO IA',margin,first?17:11);doc.setTextColor(255,255,255);if(first){doc.setFontSize(15);doc.text(title,margin,27,{maxWidth:width});doc.setFontSize(9);doc.text(subtitle||'',margin,34,{maxWidth:width})}y=first?46:25};
    const ensure=h=>{if(y+h>278){doc.addPage();header(false)}};
    const paragraph=(text,opt={})=>{const size=opt.size||10,lh=opt.lineHeight||4.6;doc.setFont('helvetica',opt.bold?'bold':'normal');doc.setFontSize(size);doc.setTextColor(...(opt.color||[33,43,54]));const lines=[];String(text??'No informado').replace(/\r/g,'').split('\n').forEach(p=>lines.push(...doc.splitTextToSize(p||' ',width)));ensure(lines.length*lh+2);doc.text(lines,margin,y);y+=lines.length*lh+(opt.after??2)};
    const section=text=>{ensure(12);y+=3;doc.setFillColor(238,242,245);doc.rect(margin,y-5,width,9,'F');doc.setTextColor(18,61,92);doc.setFont('helvetica','bold');doc.setFontSize(12);doc.text(String(text),margin+3,y+1);y+=9};
    const item=(head,body)=>{ensure(14);doc.setDrawColor(205,214,221);doc.setFillColor(249,250,251);doc.roundedRect(margin,y-4,width,7,1.5,1.5,'FD');doc.setTextColor(18,61,92);doc.setFont('helvetica','bold');doc.setFontSize(10);const lines=doc.splitTextToSize(String(head),width-6);doc.text(lines,margin+3,y);y+=lines.length*4.2+3;paragraph(body,{size:9.5,after:4})};
    const photo=async(entry,index)=>{try{const data=await toJpegData(entry.src,1500,.78),img=await loadImage(data),ratio=(img.naturalWidth||img.width)/(img.naturalHeight||img.height);let w=150,h=w/ratio;if(h>100){h=100;w=h*ratio}ensure(h+22);paragraph(`${index+1}. ${entry.label}`,{bold:true,size:9,after:2});doc.setDrawColor(160,170,180);doc.rect(margin,y,w,h);doc.addImage(data,'JPEG',margin,y,w,h,undefined,'FAST');y+=h+5;paragraph(`Registro: ${fmt(entry.record?.at)}`,{size:8,color:[90,101,112],after:4});return true}catch(error){console.warn('MANTPRO PDF photo:',error);paragraph(`${index+1}. ${entry.label}: no fue posible incrustar esta fotografía.`,{size:8,color:[150,55,55]});return false}};
    const finish=name=>{const pages=doc.getNumberOfPages();for(let p=1;p<=pages;p++){doc.setPage(p);doc.setDrawColor(205,214,221);doc.line(margin,287,195,287);doc.setFont('helvetica','normal');doc.setFontSize(8);doc.setTextColor(90,101,112);doc.text(`Supervisor: ${window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards'}`,margin,292);doc.text(`Página ${p} de ${pages}`,195,292,{align:'right'})}doc.save(pdfName(name))};
    header(true);return{paragraph,section,item,photo,finish};
  }

  function pauseMs(job){return (job.data?.pauses||[]).reduce((n,p)=>n+(p.end?new Date(p.end)-new Date(p.start):0),0)}
  function duration(start,end){if(!start||!end)return'No registrado';const ms=Math.max(0,new Date(end)-new Date(start)),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000);return `${h} h ${String(m).padStart(2,'0')} min`}
  function netDuration(job){const d=job.data||{};if(!d.actualStart||!d.actualEnd)return'No registrado';const ms=Math.max(0,new Date(d.actualEnd)-new Date(d.actualStart)-pauseMs(job)),h=Math.floor(ms/3600000),m=Math.floor(ms%3600000/60000);return `${h} h ${String(m).padStart(2,'0')} min`}
  function jobStatus(job){const d=job.data||{};if(d.actualEnd)return'Terminado';if(d.pauseStartAt)return'Pausado';if(d.actualStart)return'En ejecución';if(d.lotoStart)return'En bloqueo';if(d.docsStart)return'Documentación';return'Programado'}

  async function downloadJobPdfFixed(){
    const job=currentJob();if(!job){alert('No fue posible identificar la orden de trabajo. Vuelva a abrir el informe desde la lista de OT.');return}
    const d=job.data||{},progress=linked('progress',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)),safety=linked('safety',job.id).sort((a,b)=>new Date(a.at)-new Date(b.at)),kpis=linked('kpi',job.id),photos=photoEntriesForJob(job);
    const pdf=writer('Informe técnico de mantención',`${d.folio||'OT'} · ${d.equip||'Equipo no informado'}`);
    pdf.section('Identificación');pdf.paragraph(`Supervisor: ${window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards'}\nPlanta / área: ${d.plant||'No informado'} / ${d.area||'No informado'}\nEquipo / TAG: ${d.equip||'No informado'}\nTrabajo: ${d.task||'No informado'}\nEstado: ${jobStatus(job)}\nFecha de emisión: ${fmt(new Date().toISOString())}`);
    pdf.section('Horario real y tiempos');pdf.item('Documentación de seguridad',`Inicio: ${fmt(d.docsStart)}\nTérmino: ${fmt(d.docsEnd)}\nDuración: ${duration(d.docsStart,d.docsEnd)}`);pdf.item('Bloqueo / aislamiento LOTO',`Inicio: ${fmt(d.lotoStart)}\nEnergía cero verificada: ${fmt(d.zeroVerifiedAt)}\nTérmino: ${fmt(d.lotoEnd)}\nDuración: ${duration(d.lotoStart,d.lotoEnd)}`);pdf.item('Ejecución real del trabajo',`Inicio: ${fmt(d.actualStart)}\nTérmino: ${fmt(d.actualEnd)}\nDuración neta: ${netDuration(job)}\nAvance final: ${Number(d.progress||0)}%`);
    pdf.section('Actividades realizadas');if(!progress.length)pdf.paragraph('No informado.');progress.forEach((x,i)=>pdf.item(`Avance ${i+1} · ${x.data?.percent||0}% · ${fmt(x.at)}`,`${x.data?.text||'No informado'}${x.data?.findings?'\nHallazgo: '+x.data.findings:''}`));
    pdf.section('Desviaciones de seguridad');if(!safety.length)pdf.paragraph('No se registraron desviaciones para esta OT.');safety.forEach((x,i)=>pdf.item(`Desviación ${i+1} · Riesgo ${x.data?.risk||'No informado'} · ${fmt(x.at)}`,`Categoría: ${x.data?.category||'No informada'}\nHallazgo: ${x.data?.text||'No informado'}\nAcción inmediata: ${x.data?.action||'No informada'}\nRecomendación: ${x.data?.recommendation||'No informada'}`));
    pdf.section('Evaluación de técnicos');if(!kpis.length)pdf.paragraph('No informado.');kpis.forEach(x=>pdf.item(`${x.data?.technician||'Técnico'} · ${x.data?.score||0}%`,x.data?.notes||'Sin observaciones.'));
    pdf.section(`Registro fotográfico (${photos.length})`);if(!photos.length)pdf.paragraph('No existen fotografías guardadas en esta orden.');else for(let i=0;i<photos.length;i++)await pdf.photo(photos[i],i);
    pdf.section('Trazabilidad');pdf.paragraph('Las fotografías anteriores fueron recuperadas desde la orden, avances y desviaciones asociadas. Cada imagen se procesa antes de incrustarse para asegurar compatibilidad con el PDF.');
    pdf.finish(`Informe_${d.folio||job.id}`);showToast(photos.length?`Informe descargado con ${photos.length} fotografía(s).`:'Informe descargado sin fotografías guardadas.');
  }

  async function downloadDailyPdfFixed(){
    const day=sessionStorage.getItem('mantpro-report-day')||new Date().toISOString().slice(0,10),jobs=byType('job').filter(j=>dateKey(j.data?.actualStart||j.at)===day),safety=byType('safety').filter(x=>dateKey(x.at)===day),walks=byType('walk').filter(x=>dateKey(x.data?.startAt||x.at)===day),photos=allPhotosForDay(day);
    const pdf=writer('Informe general diario',new Date(day+'T12:00:00').toLocaleDateString('es-CL',{dateStyle:'full'}));
    pdf.section('Resumen ejecutivo');pdf.paragraph(`Supervisor: ${window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards'}\nTrabajos: ${jobs.length}\nTrabajos terminados: ${jobs.filter(x=>x.data?.actualEnd).length}\nDesviaciones: ${safety.length}\nCaminatas: ${walks.length}\nFotografías: ${photos.length}\nFecha de emisión: ${fmt(new Date().toISOString())}`);
    pdf.section('Trabajos de la jornada');if(!jobs.length)pdf.paragraph('Sin trabajos registrados para la fecha.');jobs.forEach(j=>pdf.item(`${j.data?.folio||'OT'} · ${j.data?.equip||'Equipo'}`,`Trabajo: ${j.data?.task||'No informado'}\nInicio real: ${fmt(j.data?.actualStart)}\nTérmino real: ${fmt(j.data?.actualEnd)}\nAvance: ${Number(j.data?.progress||0)}%\nEstado: ${jobStatus(j)}`));
    pdf.section(`Registro fotográfico diario (${photos.length})`);if(!photos.length)pdf.paragraph('No existen fotografías guardadas para la jornada.');else for(let i=0;i<photos.length;i++)await pdf.photo(photos[i],i);
    pdf.finish(`Informe_Diario_${day}`);showToast(`Informe diario descargado con ${photos.length} fotografía(s).`);
  }

  function showToast(text){const t=$('#toast');if(!t){alert(text);return}t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,3500)}

  document.addEventListener('click',e=>{
    const jobButton=e.target.closest('[data-pdf-job]');
    if(jobButton){e.preventDefault();e.stopImmediatePropagation();jobButton.disabled=true;jobButton.textContent='Preparando fotografías…';downloadJobPdfFixed().catch(err=>{console.error(err);alert(err.message||'No fue posible generar el informe con fotografías.')}).finally(()=>{jobButton.disabled=false;jobButton.textContent='Descargar informe PDF'});return}
    const dailyButton=e.target.closest('[data-pdf-daily]');
    if(dailyButton){e.preventDefault();e.stopImmediatePropagation();dailyButton.disabled=true;dailyButton.textContent='Preparando fotografías…';downloadDailyPdfFixed().catch(err=>{console.error(err);alert(err.message||'No fue posible generar el informe diario con fotografías.')}).finally(()=>{dailyButton.disabled=false;dailyButton.textContent='Descargar informe diario PDF'})}
  },true);

  window.MANTPRO_PHOTO_REPORT_FIX={build:BUILD,photoEntriesForJob,downloadJobPdfFixed,downloadDailyPdfFixed};
})();
