/* SUPERVISIÓN EECR — integración de charla firmada con INFORME KPI. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3';
  const TYPE='talk_signed';
  const BUILD='20260806-charla-firmada-v1';
  const $=(s,r=document)=>r.querySelector(s);
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const uid=()=>crypto.randomUUID?.()||`${Date.now()}-${Math.random().toString(16).slice(2)}`;
  let photos=[];

  function notify(text){
    const t=$('#toast');
    if(t){t.textContent=text;t.hidden=false;clearTimeout(notify.t);notify.t=setTimeout(()=>t.hidden=true,4200)}
    else alert(text);
  }
  function readStore(){
    try{const rows=JSON.parse(localStorage.getItem(STORE)||'[]');return Array.isArray(rows)?rows:[]}
    catch{return[]}
  }
  function writeTalk(record){
    const rows=readStore(),i=rows.findIndex(x=>x?.id===record.id);
    if(i<0)rows.push(record);else rows[i]=record;
    localStorage.setItem(STORE,JSON.stringify(rows));
    window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{id:record.id,type:TYPE}}));
  }
  async function dataUrlFromFile(file){
    const source=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsDataURL(file)});
    const image=await new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=reject;img.src=source});
    const render=(max,quality)=>{
      const w=image.naturalWidth||image.width,h=image.naturalHeight||image.height,scale=Math.min(1,max/Math.max(w,h));
      const canvas=document.createElement('canvas');canvas.width=Math.max(1,Math.round(w*scale));canvas.height=Math.max(1,Math.round(h*scale));
      const ctx=canvas.getContext('2d',{alpha:false});ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(image,0,0,canvas.width,canvas.height);
      return canvas.toDataURL('image/jpeg',quality);
    };
    let out=render(2000,.88);
    if(out.length>3500000)out=render(1600,.80);
    return out;
  }
  async function captureFile(file){
    if(!file)return;
    if(!/^image\//i.test(file.type||''))return notify('Seleccione una fotografía válida.');
    try{
      const dataUrl=await dataUrlFromFile(file);
      photos.push({
        id:uid(),dataUrl,designation:'Documento firmado de la charla',segment:'Charla firmada',capturedAt:new Date().toISOString(),
        description:'',note:'',originalName:file.name||'charla_firmada.jpg',originalMime:file.type||'image/jpeg',originalSize:Number(file.size||0)
      });
      renderPhotos();
      notify('Fotografía de charla agregada. Revise que el documento esté completo y legible.');
    }catch(error){console.error(error);notify('No fue posible procesar la fotografía de la charla.')}
  }
  function ensureInputs(){
    if(!$('#eecr-talk-camera')){
      const camera=document.createElement('input');camera.id='eecr-talk-camera';camera.type='file';camera.accept='image/*';camera.capture='environment';camera.hidden=true;
      camera.onchange=()=>{const file=camera.files?.[0];camera.value='';captureFile(file)};document.body.appendChild(camera);
    }
    if(!$('#eecr-talk-gallery')){
      const gallery=document.createElement('input');gallery.id='eecr-talk-gallery';gallery.type='file';gallery.accept='image/*';gallery.hidden=true;
      gallery.onchange=()=>{const file=gallery.files?.[0];gallery.value='';captureFile(file)};document.body.appendChild(gallery);
    }
  }
  function renderPhotos(){
    const box=$('#described-quick-preview');if(!box)return;
    box.innerHTML=photos.length?photos.map((p,i)=>`<article class="stage-photo-card stage-photo-described"><img src="${p.dataUrl}" alt="Documento firmado de la charla"><div><b>Documento firmado</b><small>${esc(p.originalName)} · evidencia ${i+1}</small><button type="button" data-eecr-talk-remove="${i}" class="danger-link">Eliminar foto</button></div></article>`).join(''):'<p class="stage-photo-empty">Todavía no se ha agregado la fotografía de la charla firmada.</p>';
    box.querySelectorAll('[data-eecr-talk-remove]').forEach(button=>button.onclick=()=>{photos.splice(Number(button.dataset.eecrTalkRemove),1);renderPhotos()});
  }
  function setLabel(label,text){
    if(!label)return;
    if(!label.dataset.eecrOriginalLabel){const node=[...label.childNodes].find(n=>n.nodeType===Node.TEXT_NODE&&n.nodeValue.trim());label.dataset.eecrOriginalLabel=node?.nodeValue||''}
    const node=[...label.childNodes].find(n=>n.nodeType===Node.TEXT_NODE);
    if(node)node.nodeValue=text;
  }
  function restoreLabel(label){
    if(!label?.dataset.eecrOriginalLabel)return;
    const node=[...label.childNodes].find(n=>n.nodeType===Node.TEXT_NODE);if(node)node.nodeValue=label.dataset.eecrOriginalLabel;
  }
  function isTalk(){return $('#described-segment')?.value===TYPE}
  function enhanceModal(){
    const overlay=$('#mantpro-photo-description-overlay');if(!overlay||overlay.dataset.eecrTalkIntegration==='1')return;
    overlay.dataset.eecrTalkIntegration='1';ensureInputs();photos=[];
    const segment=$('#described-segment'),record=$('#described-record'),designation=$('#described-designation'),state=$('#described-record-state');
    const take=overlay.querySelector('[data-take-described]'),save=overlay.querySelector('[data-save-described]'),tools=overlay.querySelector('.stage-record-tools');
    const recordLabel=record?.closest('label'),designationLabel=designation?.closest('label'),description=$('#next-photo-description'),descriptionLabel=description?.closest('label'),warning=overlay.querySelector('.stage-photo-warning');
    if(!segment||!take||!save)return;
    if(!segment.querySelector(`option[value="${TYPE}"]`))segment.insertAdjacentHTML('beforeend','<option value="talk_signed">Charla firmada</option>');
    let gallery=overlay.querySelector('[data-eecr-talk-gallery]');
    if(!gallery){gallery=document.createElement('button');gallery.type='button';gallery.className='outline stage-camera-big';gallery.dataset.eecrTalkGallery='1';gallery.textContent='🖼️ Elegir fotografía de galería';take.insertAdjacentElement('afterend',gallery)}

    const applyMode=()=>{
      const talk=isTalk();
      recordLabel?.toggleAttribute('hidden',talk);tools?.toggleAttribute('hidden',talk);designationLabel?.toggleAttribute('hidden',talk);gallery.hidden=!talk;
      if(talk){
        state.hidden=false;state.classList.remove('warn');state.textContent='No requiere OT ni registro previo. La evidencia se enviará a INFORME KPI → Biblioteca de charlas para revisión y confirmación.';
        take.disabled=false;save.disabled=false;take.textContent='📷 Tomar fotografía de charla';save.textContent='Enviar a INFORME KPI';
        setLabel(descriptionLabel,'Observaciones (opcional) ');
        if(warning)warning.textContent='Fotografíe el documento firmado completo, sin recortes. La imagen se conservará como evidencia documental del registro.';
        renderPhotos();
      }else{
        state.hidden=false;gallery.hidden=true;take.textContent='📷 Tomar fotografía';save.textContent='Guardar fotos';restoreLabel(descriptionLabel);
        if(warning)warning.textContent='Las fotografías son opcionales. Puede cerrar sin tomar imágenes.';
        photos=[];
      }
    };
    segment.addEventListener('change',()=>setTimeout(applyMode,0));
    take.addEventListener('click',event=>{if(!isTalk())return;event.preventDefault();event.stopImmediatePropagation();$('#eecr-talk-camera')?.click()},true);
    gallery.addEventListener('click',event=>{if(!isTalk())return;event.preventDefault();event.stopImmediatePropagation();$('#eecr-talk-gallery')?.click()},true);
    save.addEventListener('click',async event=>{
      if(!isTalk())return;
      event.preventDefault();event.stopImmediatePropagation();
      if(!photos.length)return notify('Agregue primero una fotografía completa de la charla firmada.');
      save.disabled=true;save.textContent='Enviando…';
      const now=new Date().toISOString(),obs=String(description?.value||'').trim(),first=photos[0];
      const recordTalk={
        id:uid(),type:TYPE,title:'Charla firmada',at:now,updatedAt:now,dirty:true,synced:false,
        data:{
          sourceApp:'CHARLAS DIARIAS',sourceModule:'SUPERVISIÓN EECR',transportApp:'Supervisión EECR móvil',registrationMode:'signed-talk-photo',reviewStatus:'pendiente-lectura',
          observations:obs,photoFileName:first.originalName,photoMimeType:first.originalMime,photoSize:first.originalSize,photoDataUrl:first.dataUrl,
          stagePhotos:photos.map(p=>({...p,description:obs||p.description,note:obs||p.note}))
        }
      };
      try{
        writeTalk(recordTalk);
        try{await window.MANTPRO?.sync?.()}catch(error){console.warn(error)}
        notify(navigator.onLine?'Charla enviada. Quedará disponible en INFORME KPI → Biblioteca de charlas.':'Charla guardada en el teléfono. Se enviará automáticamente cuando vuelva la conexión.');
        setTimeout(()=>overlay.remove(),650);
      }catch(error){console.error(error);save.disabled=false;save.textContent='Enviar a INFORME KPI';notify('No fue posible guardar la charla. La fotografía no fue eliminada; vuelva a intentar.')}
    },true);
    applyMode();
  }
  function install(){
    const api=window.MANTPRO_PHOTO_DESCRIPTIONS;if(!api?.open||api.__eecrTalkWrapped)return false;
    const original=api.open.bind(api);
    api.open=()=>{original();enhanceModal();setTimeout(enhanceModal,0)};api.__eecrTalkWrapped=true;api.talkBuild=BUILD;
    return true;
  }
  const start=()=>{
    ensureInputs();
    let attempts=0;const timer=setInterval(()=>{if(install()||++attempts>80)clearInterval(timer)},100);
    new MutationObserver(()=>{install();enhanceModal()}).observe(document.body,{childList:true,subtree:true});
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
