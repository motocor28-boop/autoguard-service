/* MANTPRO IA Cloud — captura simple con una descripción independiente por fotografía. */
(()=>{
  'use strict';
  const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const uid=()=>crypto.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const pending=new WeakMap();
  let captureTarget=null,quick=[];
  const core=()=>window.MANTPRO_STAGE_PHOTOS||{};
  const categories=type=>core().categories?.[type]||[];
  const segmentName={job:'Trabajo',progress:'Trabajo',safety:'Desviación',walk:'Caminata',kpi:'KPI'};
  const route={job:'job_new',walk:'walk_new',safety:'safety_new',kpi:'jobs'};
  const notify=text=>{const t=$('#toast');if(t){t.textContent=text;t.hidden=false;setTimeout(()=>t.hidden=true,3600)}else alert(text)};
  const records=()=>{try{return core().records?.()||[]}catch{return[]}};
  const listFor=form=>{if(!pending.has(form))pending.set(form,[]);return pending.get(form)};

  async function imageData(file){
    const src=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file)});
    const img=await new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src=src});
    const max=1100,scale=Math.min(1,max/Math.max(img.naturalWidth||img.width,img.naturalHeight||img.height));
    const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round((img.naturalWidth||img.width)*scale));canvas.height=Math.max(1,Math.round((img.naturalHeight||img.height)*scale));
    const ctx=canvas.getContext('2d',{alpha:false});ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    return canvas.toDataURL('image/jpeg',.68);
  }
  const photoObject=(dataUrl,type,designation,description='')=>{const text=String(description||'').trim();return{id:uid(),dataUrl,type,designation,segment:segmentName[type]||type,capturedAt:new Date().toISOString(),description:text,note:text}};
  function recordTitle(record){const d=record?.data||{};if(record?.type==='job')return`${d.folio||'OT'} · ${d.equip||'Equipo'}`;if(record?.type==='walk')return`${d.area||'Caminata'} · ${new Date(d.startAt||record.at).toLocaleDateString('es-CL')}`;if(record?.type==='safety')return`${d.category||'Desviación'} · ${d.area||'Área'} · ${new Date(record.at).toLocaleDateString('es-CL')}`;if(record?.type==='kpi')return`${d.technician||'Técnico'} · ${d.score||0}%`;return record?.title||'Registro'}
  function photoCard(photo,index,type){
    const options=categories(type).map(stage=>`<option${stage===photo.designation?' selected':''}>${esc(stage)}</option>`).join('');
    return `<article class="stage-photo-card stage-photo-described" data-photo-index="${index}"><img src="${photo.dataUrl}" alt="${esc(photo.designation)}"><div><label class="stage-photo-card-label">Etapa<select data-photo-designation>${options}</select></label><label class="stage-photo-card-label">Descripción de esta foto<textarea data-photo-description rows="3" placeholder="Describa lo que se observa.">${esc(photo.description||photo.note||'')}</textarea></label><button type="button" class="danger-link" data-photo-remove>Eliminar foto</button></div></article>`;
  }
  function bindCards(box,photos,type,render){box.querySelectorAll('.stage-photo-described').forEach(card=>{const index=Number(card.dataset.photoIndex),photo=photos[index];card.querySelector('[data-photo-designation]').onchange=e=>photo.designation=e.target.value;card.querySelector('[data-photo-description]').oninput=e=>{photo.description=e.target.value;photo.note=e.target.value};card.querySelector('[data-photo-remove]').onclick=()=>{photos.splice(index,1);render()}})}
  function renderForm(form,type,focusLast=false){const box=form.querySelector('[data-described-preview]'),photos=listFor(form);if(!box)return;box.innerHTML=photos.length?photos.map((photo,index)=>photoCard(photo,index,type)).join(''):'<p class="stage-photo-empty">Sin fotografías. Puede guardar el registro igualmente.</p>';bindCards(box,photos,type,()=>renderForm(form,type));if(focusLast)box.querySelector('.stage-photo-described:last-child [data-photo-description]')?.focus()}
  function panelFor(form,type){
    if(form.querySelector('[data-photo-description-panel]')||!categories(type).length)return;
    const panel=document.createElement('section');panel.dataset.photoDescriptionPanel='1';panel.className='stage-photo-panel simple-photo-panel';
    panel.innerHTML=`<div class="stage-photo-title"><div><b>📷 Evidencia fotográfica</b><small>Opcional. Seleccione la etapa, tome la foto y describa lo observado.</small></div><span>Opcional</span></div><div class="simple-photo-capture"><label>Etapa<select data-described-stage>${categories(type).map(stage=>`<option>${esc(stage)}</option>`).join('')}</select></label><button type="button" class="primary" data-described-take>📷 Tomar foto</button></div><div data-described-preview></div>`;
    const submit=form.querySelector('button[type="submit"],button.primary:last-child');submit?form.insertBefore(panel,submit):form.appendChild(panel);
    panel.querySelector('[data-described-take]').onclick=()=>{captureTarget={mode:'form',form,type,designation:panel.querySelector('[data-described-stage]').value,description:''};$('#mantpro-described-camera').click()};
    renderForm(form,type);
  }
  function attach(record,photos){return !!(record&&photos.length&&core().attachToRecord?.(record,photos))}
  function watchSubmit(form,type){
    if(form.dataset.photoDescriptionSubmit)return;form.dataset.photoDescriptionSubmit='1';
    form.addEventListener('submit',()=>{const photos=[...listFor(form)];if(!photos.length)return;const before=new Set(records().map(record=>record.id));let attempts=0;const findCreated=()=>{const created=records().filter(record=>record.type===type&&!before.has(record.id)).sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at))[0];if(created&&attach(created,photos)){pending.set(form,[]);notify(`Registro guardado con ${photos.length} fotografía(s).`);return}if(++attempts<10)setTimeout(findCreated,250)};setTimeout(findCreated,180)},true);
  }
  function ensureCamera(){
    if($('#mantpro-described-camera'))return;
    const input=document.createElement('input');input.id='mantpro-described-camera';input.type='file';input.accept='image/*';input.capture='environment';input.hidden=true;document.body.appendChild(input);
    input.onchange=async()=>{const file=input.files?.[0];input.value='';if(!file||!captureTarget)return;try{const data=await imageData(file),photo=photoObject(data,captureTarget.type,captureTarget.designation,captureTarget.description);if(captureTarget.mode==='form'){listFor(captureTarget.form).push(photo);renderForm(captureTarget.form,captureTarget.type,true)}else{quick.push(photo);renderQuick(true);const next=$('#next-photo-description');if(next)next.value=''}notify('Foto agregada. Escriba su descripción.')}catch(error){console.error(error);notify('No fue posible procesar la fotografía. Puede continuar sin imagen.')}};
  }
  function enhanceForms(){$$('#record-form[data-form]').forEach(form=>{const type=form.dataset.form;if(!categories(type).length)return;panelFor(form,type);watchSubmit(form,type)})}
  function openCreate(type,overlay){overlay?.remove();const target=route[type];try{if(window.MANTPRO?.go){window.MANTPRO.go(target);return}}catch{}const direct=$(`[data-go="${target}"]`);if(direct){direct.click();return}document.querySelector('[data-route="home"]')?.click();setTimeout(()=>document.querySelector(`[data-go="${target}"]`)?.click(),120)}
  function modal(){
    $('#mantpro-photo-description-overlay')?.remove();quick=[];
    const overlay=document.createElement('div');overlay.id='mantpro-photo-description-overlay';overlay.className='stage-photo-overlay';
    overlay.innerHTML=`<section class="stage-photo-modal"><header><div><span>EVIDENCIA OPCIONAL</span><h2>Agregar fotografías</h2></div><button type="button" data-close-described>×</button></header><label>Tipo de registro<select id="described-segment"><option value="job">Trabajo</option><option value="walk">Caminata</option><option value="safety">Desviación / hallazgo</option><option value="kpi">KPI</option></select></label><label>Registro<select id="described-record"></select></label><div id="described-record-state" class="stage-record-state"></div><div class="stage-record-tools"><button type="button" data-refresh-described>↻ Actualizar</button><button type="button" data-create-described>＋ Crear registro</button></div><label>Etapa<select id="described-designation"></select></label><label>Descripción para esta foto<textarea id="next-photo-description" rows="3" placeholder="Describa objetivamente lo que se observa."></textarea></label><button type="button" class="primary stage-camera-big" data-take-described>📷 Tomar fotografía</button><div id="described-quick-preview"></div><div class="stage-photo-warning">Las fotografías son opcionales. Puede cerrar sin tomar imágenes.</div><footer><button type="button" data-close-described>Cancelar</button><button type="button" class="primary" data-save-described>Guardar fotos</button></footer></section>`;
    document.body.appendChild(overlay);
    const segment=$('#described-segment'),record=$('#described-record'),designation=$('#described-designation'),state=$('#described-record-state');
    const refresh=()=>{const type=segment.value,previous=record.value,rows=records().filter(item=>item.type===type).sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at));record.innerHTML=rows.map(item=>`<option value="${item.id}">${esc(recordTitle(item))}</option>`).join('')||'<option value="">No hay registros disponibles</option>';if(rows.some(item=>item.id===previous))record.value=previous;designation.innerHTML=categories(type).map(stage=>`<option>${esc(stage)}</option>`).join('');state.textContent=rows.length?`${rows.length} registro(s) disponible(s).`:'Primero cree el registro al que asociará la fotografía.';state.classList.toggle('warn',!rows.length);overlay.querySelector('[data-take-described]').disabled=!rows.length;overlay.querySelector('[data-save-described]').disabled=!rows.length;renderQuick()};
    segment.onchange=()=>{quick=[];refresh()};refresh();overlay.querySelectorAll('[data-close-described]').forEach(button=>button.onclick=()=>overlay.remove());overlay.onclick=e=>{if(e.target===overlay)overlay.remove()};
    overlay.querySelector('[data-refresh-described]').onclick=async button=>{button.disabled=true;button.textContent='Actualizando…';try{await window.MANTPRO?.sync?.()}catch{}setTimeout(()=>{refresh();button.disabled=false;button.textContent='↻ Actualizar'},700)};
    overlay.querySelector('[data-create-described]').onclick=()=>openCreate(segment.value,overlay);
    overlay.querySelector('[data-take-described]').onclick=()=>{if(!record.value)return notify('Primero debe existir un registro guardado.');captureTarget={mode:'quick',type:segment.value,designation:designation.value,description:$('#next-photo-description').value};$('#mantpro-described-camera').click()};
    overlay.querySelector('[data-save-described]').onclick=()=>{const target=records().find(item=>item.id===record.value);if(!quick.length)return notify('No hay fotografías para guardar.');if(attach(target,quick)){notify(`${quick.length} fotografía(s) guardada(s).`);overlay.remove()}else notify('No se encontró el registro. Actualice e intente nuevamente.')};
    setTimeout(async()=>{try{await window.MANTPRO?.sync?.()}catch{}refresh()},500);
  }
  function renderQuick(focusLast=false){const box=$('#described-quick-preview');if(!box)return;const type=$('#described-segment')?.value||'job';box.innerHTML=quick.length?quick.map((photo,index)=>photoCard(photo,index,type)).join(''):'<p class="stage-photo-empty">Todavía no se han tomado fotografías.</p>';bindCards(box,quick,type,()=>renderQuick());if(focusLast)box.querySelector('.stage-photo-described:last-child [data-photo-description]')?.focus()}
  let timer;function enhance(){clearTimeout(timer);timer=setTimeout(()=>{ensureCamera();enhanceForms()},70)}
  const start=()=>{new MutationObserver(enhance).observe($('#app')||document.body,{childList:true,subtree:true});window.addEventListener('mantpro-records-changed',enhance);enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.MANTPRO_PHOTO_DESCRIPTIONS={open:modal,build:'2026-08-02-simple-photo-description'};
})();
