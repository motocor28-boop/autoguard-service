/* MANTPRO IA Cloud — captura móvil opcional por etapa y designación. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3';
  const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const uid=()=>crypto.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const read=()=>{try{return JSON.parse(localStorage.getItem(STORE)||'[]')}catch{return[]}};
  const write=a=>localStorage.setItem(STORE,JSON.stringify(a));
  const pending=new WeakMap();
  let captureTarget=null,quick=[];

  const CATEGORIES={
    job:['Antes del trabajo','Durante el trabajo','Después del trabajo','Hallazgo técnico','Medida inmediata','Condición corregida'],
    progress:['Durante el trabajo','Después del trabajo','Hallazgo técnico','Medida inmediata','Condición corregida'],
    safety:['Desviación o hallazgo detectado','Medida inmediata aplicada','Condición corregida','Verificación de cierre'],
    walk:['Vista general de la caminata','Hallazgo de caminata','Medida inmediata aplicada','Condición corregida'],
    kpi:['Evidencia de desempeño','Evidencia de seguridad','Evidencia de calidad']
  };

  const SEGMENT={job:'Trabajo',progress:'Trabajo',safety:'Desviación',walk:'Caminata',kpi:'KPI'};
  const notify=text=>{const t=$('#toast');if(t){t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,3500)}else alert(text)};

  async function imageData(file){
    const src=await new Promise((res,rej)=>{const r=new FileReader();r.onload=()=>res(r.result);r.onerror=rej;r.readAsDataURL(file)});
    const img=await new Promise((res,rej)=>{const i=new Image();i.onload=()=>res(i);i.onerror=rej;i.src=src});
    const max=1100,scale=Math.min(1,max/Math.max(img.naturalWidth||img.width,img.naturalHeight||img.height));
    const c=document.createElement('canvas');c.width=Math.max(1,Math.round((img.naturalWidth||img.width)*scale));c.height=Math.max(1,Math.round((img.naturalHeight||img.height)*scale));
    const x=c.getContext('2d',{alpha:false});x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height);x.drawImage(img,0,0,c.width,c.height);
    return c.toDataURL('image/jpeg',.68);
  }

  function photoObject(dataUrl,designation,segment,note=''){
    return{id:uid(),dataUrl,designation,segment,capturedAt:new Date().toISOString(),note:String(note||'').trim()};
  }

  function listFor(form){if(!pending.has(form))pending.set(form,[]);return pending.get(form)}

  function renderFormPhotos(form){
    const box=form.querySelector('[data-stage-preview]');if(!box)return;const photos=listFor(form);
    box.innerHTML=photos.length?photos.map((p,i)=>`<article class="stage-photo-card"><img src="${p.dataUrl}" alt="${esc(p.designation)}"><div><b>${esc(p.designation)}</b><small>Fotografía opcional ${i+1}</small><button type="button" data-remove-stage="${i}">Eliminar</button></div></article>`).join(''):'<p class="stage-photo-empty">No se han agregado fotografías. Puede guardar el registro y generar el informe igualmente.</p>';
    box.querySelectorAll('[data-remove-stage]').forEach(b=>b.onclick=()=>{photos.splice(Number(b.dataset.removeStage),1);renderFormPhotos(form)});
  }

  function panelFor(form,type){
    if(form.querySelector('[data-stage-panel]')||!CATEGORIES[type])return;
    const panel=document.createElement('section');panel.dataset.stagePanel='1';panel.className='stage-photo-panel';
    panel.innerHTML=`<div class="stage-photo-title"><div><b>📷 Fotografías opcionales</b><small>Agregue solo las que correspondan. No son requisito para guardar ni para generar el informe.</small></div><span>0 obligatorias</span></div><div class="stage-photo-actions">${CATEGORIES[type].map(x=>`<button type="button" data-stage-choice="${esc(x)}">${esc(x)}</button>`).join('')}</div><div data-stage-preview></div>`;
    const submit=form.querySelector('button[type="submit"],button.primary:last-child');
    submit?form.insertBefore(panel,submit):form.appendChild(panel);
    panel.querySelectorAll('[data-stage-choice]').forEach(b=>b.onclick=()=>{captureTarget={mode:'form',form,type,designation:b.dataset.stageChoice};$('#mantpro-stage-camera').click()});
    renderFormPhotos(form);
  }

  function attachToRecord(record,photos){
    if(!record||!photos.length)return false;
    record.data=record.data||{};record.data.stagePhotos=[...(Array.isArray(record.data.stagePhotos)?record.data.stagePhotos:[]),...photos];record.updatedAt=new Date().toISOString();record.dirty=true;record.synced=false;
    const all=read(),i=all.findIndex(x=>x.id===record.id);if(i<0)return false;all[i]=record;write(all);window.MANTPRO?.sync?.();return true;
  }

  function watchSubmit(form,type){
    if(form.dataset.stageSubmitBound)return;form.dataset.stageSubmitBound='1';
    form.addEventListener('submit',()=>{
      const photos=[...listFor(form)];if(!photos.length)return;
      const before=new Set(read().map(x=>x.id));
      setTimeout(()=>{
        const created=read().filter(x=>x.type===type&&!before.has(x.id)).sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at))[0];
        if(created&&attachToRecord(created,photos)){pending.set(form,[]);notify(`Registro guardado con ${photos.length} fotografía(s) opcional(es).`)}
      },220);
    },true);
  }

  function enhanceForms(){
    $$('#record-form[data-form]').forEach(form=>{const type=form.dataset.form;if(!CATEGORIES[type])return;panelFor(form,type);watchSubmit(form,type)});
  }

  function ensureCamera(){
    if($('#mantpro-stage-camera'))return;const input=document.createElement('input');input.id='mantpro-stage-camera';input.type='file';input.accept='image/*';input.capture='environment';input.hidden=true;document.body.appendChild(input);
    input.onchange=async()=>{const file=input.files?.[0];input.value='';if(!file||!captureTarget)return;try{const data=await imageData(file),p=photoObject(data,captureTarget.designation,SEGMENT[captureTarget.type]||captureTarget.segment,captureTarget.note||'');if(captureTarget.mode==='form'){listFor(captureTarget.form).push(p);renderFormPhotos(captureTarget.form)}else{quick.push(p);renderQuickPhotos()}notify(`Fotografía agregada: ${p.designation}`)}catch(e){console.error(e);notify('No fue posible procesar la fotografía. Puede continuar sin imagen.')}};
  }

  function recordTitle(x){const d=x.data||{};if(x.type==='job')return`${d.folio||'OT'} · ${d.equip||'Equipo'}`;if(x.type==='walk')return`${d.area||'Caminata'} · ${new Date(d.startAt||x.at).toLocaleDateString('es-CL')}`;if(x.type==='safety')return`${d.category||'Desviación'} · ${d.area||'Área'} · ${new Date(x.at).toLocaleDateString('es-CL')}`;if(x.type==='kpi')return`${d.technician||'Técnico'} · ${d.score||0}%`;return x.title||'Registro'}

  function modal(){
    $('#mantpro-photo-overlay')?.remove();quick=[];const o=document.createElement('div');o.id='mantpro-photo-overlay';o.className='stage-photo-overlay';
    o.innerHTML=`<section class="stage-photo-modal"><header><div><span>REGISTRO FOTOGRÁFICO OPCIONAL</span><h2>Agregar evidencia desde el teléfono</h2></div><button type="button" data-close-photo>×</button></header><label>Segmento<select id="stage-segment"><option value="job">Trabajo</option><option value="walk">Caminata</option><option value="safety">Desviación / hallazgo</option><option value="kpi">KPI</option></select></label><label>Registro<select id="stage-record"></select></label><label>Designación<select id="stage-designation"></select></label><label>Comentario opcional<input id="stage-note" placeholder="Ej.: fuga controlada, guarda reinstalada"></label><button type="button" class="primary stage-camera-big" data-take-stage>📷 Tomar fotografía</button><div id="stage-quick-preview"></div><div class="stage-photo-warning">Las fotografías son opcionales. Cerrar este cuadro o no tomar imágenes no impide confeccionar el informe.</div><footer><button type="button" data-close-photo>Cancelar</button><button type="button" class="primary" data-save-stage>Guardar fotografías</button></footer></section>`;
    document.body.appendChild(o);const seg=$('#stage-segment'),rec=$('#stage-record'),des=$('#stage-designation');
    const refresh=()=>{const type=seg.value,rows=read().filter(x=>x.type===type).sort((a,b)=>new Date(b.at)-new Date(a.at));rec.innerHTML=rows.map(x=>`<option value="${x.id}">${esc(recordTitle(x))}</option>`).join('')||'<option value="">No hay registros disponibles</option>';des.innerHTML=(CATEGORIES[type]||[]).map(x=>`<option>${esc(x)}</option>`).join('')};
    seg.onchange=refresh;refresh();o.querySelectorAll('[data-close-photo]').forEach(b=>b.onclick=()=>o.remove());o.onclick=e=>{if(e.target===o)o.remove()};
    o.querySelector('[data-take-stage]').onclick=()=>{if(!rec.value)return notify('Primero debe existir un registro.');captureTarget={mode:'quick',type:seg.value,segment:SEGMENT[seg.value],designation:des.value,note:$('#stage-note').value};$('#mantpro-stage-camera').click()};
    o.querySelector('[data-save-stage]').onclick=()=>{const all=read(),r=all.find(x=>x.id===rec.value);if(!quick.length){notify('No hay fotografías para guardar. Puede continuar sin imágenes.');return}if(attachToRecord(r,quick)){notify(`${quick.length} fotografía(s) guardada(s) en ${recordTitle(r)}.`);o.remove()}};
    renderQuickPhotos();
  }

  function renderQuickPhotos(){const b=$('#stage-quick-preview');if(!b)return;b.innerHTML=quick.length?quick.map((p,i)=>`<article class="stage-photo-card"><img src="${p.dataUrl}" alt="${esc(p.designation)}"><div><b>${esc(p.designation)}</b><small>${esc(p.note||'Sin comentario')}</small><button type="button" data-remove-quick="${i}">Eliminar</button></div></article>`).join(''):'<p class="stage-photo-empty">Todavía no se han tomado fotografías.</p>';b.querySelectorAll('[data-remove-quick]').forEach(x=>x.onclick=()=>{quick.splice(Number(x.dataset.removeQuick),1);renderQuickPhotos()})}

  function floating(){if($('#mantpro-photo-float'))return;const b=document.createElement('button');b.id='mantpro-photo-float';b.className='stage-photo-float';b.type='button';b.innerHTML='📷<span>Evidencia</span>';b.onclick=modal;document.body.appendChild(b)}

  let timer;function enhance(){clearTimeout(timer);timer=setTimeout(()=>{ensureCamera();enhanceForms();floating()},60)}
  const start=()=>{new MutationObserver(enhance).observe($('#app')||document.body,{childList:true,subtree:true});enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.MANTPRO_STAGE_PHOTOS={open:modal,categories:CATEGORIES,attachToRecord};
})();