/* EECR móvil — guardado visible y vista previa PDF de caminatas sin descarga automática. */
(()=>{
  'use strict';
  const BUILD='2026-08-03-walk-save-preview-v1';
  const $=(selector,root=document)=>root.querySelector(selector);
  const $$=(selector,root=document)=>[...root.querySelectorAll(selector)];
  const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
  const fmt=value=>{
    if(!value)return 'No registrado';
    const date=new Date(value);
    return Number.isNaN(date.valueOf())?'No registrado':date.toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short',hour12:false});
  };
  const duration=(start,end)=>{
    if(!start||!end)return 'No registrado';
    const milliseconds=Math.max(0,new Date(end)-new Date(start));
    const hours=Math.floor(milliseconds/3600000);
    const minutes=Math.floor(milliseconds%3600000/60000);
    return `${hours} h ${String(minutes).padStart(2,'0')} min`;
  };
  const records=()=>{
    try{return Array.isArray(window.MANTPRO?.records?.())?window.MANTPRO.records():[]}
    catch{return[]}
  };
  let currentWalkId=sessionStorage.getItem('eecr-current-walk-id')||'';
  let previewUrl='';

  function rememberWalk(id){
    if(!id)return;
    currentWalkId=id;
    try{sessionStorage.setItem('eecr-current-walk-id',id)}catch{}
  }

  function currentWalk(){
    const all=records();
    let walk=all.find(item=>item?.type==='walk'&&item.id===currentWalkId);
    if(walk)return walk;
    const app=$('#app');
    const heading=app?.querySelector('h1')?.textContent?.trim()||'';
    const candidates=all.filter(item=>item?.type==='walk'&&String(item.data?.area||'').trim()===heading)
      .sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at));
    walk=candidates[0]||null;
    if(walk)rememberWalk(walk.id);
    return walk;
  }

  function toast(message){
    const target=$('#toast');
    if(!target)return;
    target.textContent=message;
    target.hidden=false;
    clearTimeout(toast.timer);
    toast.timer=setTimeout(()=>target.hidden=true,3600);
  }

  function style(){
    if($('#eecr-walk-save-preview-style'))return;
    const tag=document.createElement('style');
    tag.id='eecr-walk-save-preview-style';
    tag.textContent=`
      .eecr-walk-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0 18px}
      .eecr-walk-actions button{min-height:48px;font-weight:800}
      .eecr-pdf-preview{position:fixed;inset:0;z-index:99999;background:#0b1116;display:grid;grid-template-rows:auto 1fr;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}
      .eecr-pdf-preview[hidden]{display:none}
      .eecr-pdf-preview header{display:flex;align-items:center;gap:12px;padding:12px 14px;background:#18232b;border-bottom:1px solid #41515d;color:#fff}
      .eecr-pdf-preview header div{flex:1;min-width:0}
      .eecr-pdf-preview header b{display:block;font-size:15px}
      .eecr-pdf-preview header small{display:block;color:#bdc9d0;margin-top:2px}
      .eecr-pdf-preview header button{min-width:88px;background:#ff8b18;color:#111;border:0;border-radius:10px;padding:11px 13px;font-weight:900}
      .eecr-pdf-preview iframe{width:100%;height:100%;border:0;background:#fff}
      @media(max-width:420px){.eecr-walk-actions{grid-template-columns:1fr}.eecr-pdf-preview header small{font-size:11px}}
    `;
    document.head.appendChild(tag);
  }

  function enhanceNewWalk(){
    const form=$('#record-form[data-form="walk"]');
    if(!form)return;
    const submit=form.querySelector('button[type="submit"],button:not([type])');
    if(submit&&!submit.dataset.eecrWalkSave){
      submit.dataset.eecrWalkSave='1';
      submit.textContent='Guardar caminata';
      submit.classList.add('primary');
    }
  }

  function enhanceWalkDetail(){
    const form=$('#manual-walk-form');
    const app=$('#app');
    if(!form||!app)return;
    if(app.querySelector('.eecr-walk-actions'))return;
    const walk=currentWalk();
    if(!walk)return;
    const actions=document.createElement('div');
    actions.className='eecr-walk-actions no-print';
    actions.innerHTML='<button type="button" class="primary" data-eecr-save-walk>Guardar caminata</button><button type="button" class="outline" data-eecr-preview-walk>Vista previa PDF</button>';
    const hero=app.querySelector('.hero');
    (hero||app.querySelector('h1'))?.insertAdjacentElement('afterend',actions);
  }

  function enhance(){
    style();
    enhanceNewWalk();
    enhanceWalkDetail();
  }

  function saveWalk(){
    const detailForm=$('#manual-walk-form');
    if(detailForm){
      if(typeof detailForm.requestSubmit==='function')detailForm.requestSubmit();
      else detailForm.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
      return;
    }
    const newForm=$('#record-form[data-form="walk"]');
    if(newForm){
      if(typeof newForm.requestSubmit==='function')newForm.requestSubmit();
      else newForm.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}));
    }
  }

  function addWrappedText(doc,text,x,y,maxWidth,lineHeight=5){
    const lines=doc.splitTextToSize(String(text||'No informado'),maxWidth);
    doc.text(lines,x,y);
    return y+(lines.length*lineHeight);
  }

  function buildWalkPdf(walk){
    const JsPDF=window.jspdf?.jsPDF;
    if(!JsPDF)throw new Error('El generador PDF todavía no está disponible.');
    const doc=new JsPDF({unit:'mm',format:'a4',compress:true});
    const margin=16,pageWidth=210,usable=178;
    let y=16;
    const findings=records().filter(item=>item?.type==='safety'&&item.data?.walkId===walk.id)
      .sort((a,b)=>new Date(a.at)-new Date(b.at));
    const pageBreak=needed=>{
      if(y+needed<=281)return;
      doc.addPage();
      y=16;
      doc.setFont('helvetica','normal');
      doc.setTextColor(34,45,53);
    };
    const section=title=>{
      pageBreak(13);
      doc.setFillColor(18,61,92);
      doc.roundedRect(margin,y,usable,9,1.5,1.5,'F');
      doc.setFont('helvetica','bold');
      doc.setFontSize(10);
      doc.setTextColor(255,255,255);
      doc.text(title,margin+4,y+6);
      y+=13;
      doc.setTextColor(34,45,53);
      doc.setFont('helvetica','normal');
    };
    const field=(label,value)=>{
      pageBreak(14);
      doc.setFont('helvetica','bold');
      doc.setFontSize(9);
      doc.setTextColor(35,49,58);
      doc.text(label,margin,y);
      doc.setFont('helvetica','normal');
      doc.setFontSize(9);
      y=addWrappedText(doc,value,margin,y+5,usable,4.5)+2;
    };

    doc.setFillColor(18,23,28);
    doc.rect(0,0,pageWidth,34,'F');
    doc.setFont('helvetica','bold');
    doc.setFontSize(17);
    doc.setTextColor(255,139,24);
    doc.text('SISTEMA DE SUPERVISIÓN REMOTO EECR',margin,15);
    doc.setFontSize(13);
    doc.setTextColor(255,255,255);
    doc.text('Informe de caminata de seguridad',margin,24);
    doc.setFontSize(8);
    doc.setFont('helvetica','normal');
    doc.text(`Vista previa generada: ${fmt(new Date().toISOString())}`,margin,30);
    y=43;

    section('IDENTIFICACIÓN');
    field('Planta',walk.data?.plant);
    field('Área o sectores recorridos',walk.data?.area);
    field('Objetivo',walk.data?.objective);
    field('Participantes',walk.data?.participants);
    field('Inicio',fmt(walk.data?.startAt||walk.at));
    field('Término',fmt(walk.data?.endAt));
    field('Duración',duration(walk.data?.startAt||walk.at,walk.data?.endAt));

    section(`HALLAZGOS Y OBSERVACIONES (${findings.length})`);
    if(!findings.length){
      field('Resultado','No se registraron hallazgos asociados a esta caminata.');
    }else{
      findings.forEach((item,index)=>{
        pageBreak(35);
        doc.setFillColor(238,243,246);
        doc.roundedRect(margin,y,usable,7,1,1,'F');
        doc.setFont('helvetica','bold');
        doc.setFontSize(9);
        doc.setTextColor(18,61,92);
        doc.text(`${index+1}. ${item.data?.category||'Observación'} · Riesgo ${item.data?.risk||'No informado'}`,margin+3,y+5);
        y+=11;
        field('Fecha y hora',fmt(item.data?.recordedAt||item.at));
        field('Descripción',item.data?.text);
        field('Acción inmediata',item.data?.action||'No informada');
        field('Medida correctiva / recomendación',item.data?.recommendation||'No informada');
        field('Responsable',item.data?.responsible||'No informado');
      });
    }

    section('CIERRE');
    field('Supervisor responsable',window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards');
    field('Estado de la caminata',walk.data?.endAt?'Finalizada':'En curso');
    field('Trazabilidad','Documento generado exclusivamente para visualización. La vista previa no se guarda automáticamente en el teléfono.');

    const pages=doc.getNumberOfPages();
    for(let page=1;page<=pages;page++){
      doc.setPage(page);
      doc.setDrawColor(205,214,221);
      doc.line(margin,287,194,287);
      doc.setFont('helvetica','normal');
      doc.setFontSize(8);
      doc.setTextColor(90,101,112);
      doc.text('EECR · Gestión de caminatas',margin,292);
      doc.text(`Página ${page} de ${pages}`,194,292,{align:'right'});
    }
    return doc;
  }

  function closePreview(){
    const overlay=$('#eecr-walk-pdf-preview');
    if(overlay)overlay.remove();
    if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=''}
  }

  function showPreview(doc){
    closePreview();
    const blob=doc.output('blob');
    previewUrl=URL.createObjectURL(blob);
    const overlay=document.createElement('section');
    overlay.id='eecr-walk-pdf-preview';
    overlay.className='eecr-pdf-preview';
    overlay.setAttribute('role','dialog');
    overlay.setAttribute('aria-modal','true');
    overlay.innerHTML=`<header><div><b>Vista previa PDF · Caminata</b><small>Solo visualización: no se guardó en el teléfono.</small></div><button type="button" data-eecr-close-preview>Cerrar</button></header><iframe title="Vista previa del informe de caminata" src="${esc(previewUrl)}#toolbar=1&navpanes=0"></iframe>`;
    document.body.appendChild(overlay);
  }

  function previewWalk(){
    const walk=currentWalk();
    if(!walk){alert('No fue posible identificar la caminata abierta.');return}
    try{
      showPreview(buildWalkPdf(walk));
      toast('Vista previa abierta. El PDF no se guardó en el teléfono.');
    }catch(error){
      console.error(error);
      alert(error.message||'No fue posible crear la vista previa PDF.');
    }
  }

  document.addEventListener('click',event=>{
    const open=event.target.closest('[data-open-walk]');
    if(open)rememberWalk(open.dataset.openWalk);
    if(event.target.closest('[data-eecr-save-walk]'))saveWalk();
    if(event.target.closest('[data-eecr-preview-walk]'))previewWalk();
    if(event.target.closest('[data-eecr-close-preview]'))closePreview();
  },true);

  document.addEventListener('submit',event=>{
    const form=event.target;
    if(form?.matches?.('#record-form[data-form="walk"]')){
      setTimeout(()=>{
        const latest=records().filter(item=>item?.type==='walk')
          .sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at))[0];
        if(latest)rememberWalk(latest.id);
        enhance();
      },180);
    }
  },true);

  window.addEventListener('pagehide',closePreview);
  const observer=new MutationObserver(()=>{clearTimeout(observer.timer);observer.timer=setTimeout(enhance,70)});
  const start=()=>{observer.observe(document.body,{childList:true,subtree:true});enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.EECR_WALK_MOBILE={saveWalk,previewWalk,closePreview,build:BUILD};
})();
