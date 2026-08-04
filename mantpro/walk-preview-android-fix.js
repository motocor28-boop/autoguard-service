/* EECR móvil — corrección Android para vista previa PDF sin descarga. */
(()=>{
  'use strict';
  const BUILD='2026-08-03-walk-preview-android-v2';
  const $=(selector,root=document)=>root.querySelector(selector);
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
    try{
      const value=window.MANTPRO?.records?.();
      return Array.isArray(value)?value:[];
    }catch{return []}
  };
  let previewUrl='';

  function toast(message){
    const target=$('#toast');
    if(!target)return;
    target.textContent=message;
    target.hidden=false;
    clearTimeout(toast.timer);
    toast.timer=setTimeout(()=>target.hidden=true,3600);
  }

  function currentWalk(){
    const all=records();
    const stored=sessionStorage.getItem('eecr-current-walk-id')||'';
    let walk=all.find(item=>item?.type==='walk'&&item.id===stored);
    if(walk)return walk;
    const heading=$('#app h1')?.textContent?.trim()||'';
    walk=all.filter(item=>item?.type==='walk'&&String(item.data?.area||'').trim()===heading)
      .sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at))[0]||null;
    return walk;
  }

  function addStyles(){
    if($('#eecr-android-preview-style'))return;
    const style=document.createElement('style');
    style.id='eecr-android-preview-style';
    style.textContent=`
      .eecr-android-preview{position:fixed;inset:0;z-index:100000;background:#0b1116;display:grid;grid-template-rows:auto 1fr;padding:env(safe-area-inset-top) 0 env(safe-area-inset-bottom)}
      .eecr-android-preview header{display:flex;align-items:center;gap:12px;padding:12px 14px;background:#18232b;border-bottom:1px solid #41515d;color:#fff}
      .eecr-android-preview header div{flex:1;min-width:0}
      .eecr-android-preview header b{display:block;font-size:15px}
      .eecr-android-preview header small{display:block;color:#bdc9d0;margin-top:3px}
      .eecr-android-preview button{min-width:88px;background:#ff8b18;color:#111;border:0;border-radius:10px;padding:11px 13px;font-weight:900}
      .eecr-android-preview iframe{width:100%;height:100%;border:0;background:#fff}
    `;
    document.head.appendChild(style);
  }

  function buildPdf(walk){
    const JsPDF=window.jspdf?.jsPDF;
    if(typeof JsPDF!=='function')throw new Error('El generador PDF todavía no está disponible.');

    // Sin compresión: la versión móvil incluida no incorpora el filtro FlateEncode.
    const doc=new JsPDF({unit:'mm',format:'a4'});
    const margin=16;
    const usable=178;
    let y=16;
    const findings=records().filter(item=>item?.type==='safety'&&item.data?.walkId===walk.id)
      .sort((a,b)=>new Date(a.at)-new Date(b.at));

    const ensure=needed=>{
      if(y+needed<=281)return;
      doc.addPage();
      y=16;
    };
    const wrapped=(text,maxWidth=usable)=>doc.splitTextToSize(String(text||'No informado'),maxWidth);
    const paragraph=(text,size=9,bold=false)=>{
      const lines=wrapped(text);
      ensure(lines.length*4.7+5);
      doc.setFont('helvetica',bold?'bold':'normal');
      doc.setFontSize(size);
      doc.setTextColor(35,49,58);
      doc.text(lines,margin,y);
      y+=lines.length*4.7+4;
    };
    const section=title=>{
      ensure(14);
      doc.setFillColor(18,61,92);
      doc.rect(margin,y,usable,9,'F');
      doc.setFont('helvetica','bold');
      doc.setFontSize(10);
      doc.setTextColor(255,255,255);
      doc.text(String(title),margin+4,y+6);
      y+=14;
    };
    const field=(label,value)=>{
      ensure(16);
      doc.setFont('helvetica','bold');
      doc.setFontSize(9);
      doc.setTextColor(35,49,58);
      doc.text(String(label),margin,y);
      y+=5;
      paragraph(value,9,false);
    };

    doc.setFillColor(18,23,28);
    doc.rect(0,0,210,34,'F');
    doc.setFont('helvetica','bold');
    doc.setFontSize(16);
    doc.setTextColor(255,139,24);
    doc.text('SISTEMA DE SUPERVISIÓN REMOTO EECR',margin,15);
    doc.setFontSize(13);
    doc.setTextColor(255,255,255);
    doc.text('Informe de caminata de seguridad',margin,24);
    doc.setFont('helvetica','normal');
    doc.setFontSize(8);
    doc.text(`Vista previa: ${fmt(new Date().toISOString())}`,margin,30);
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
      paragraph('No se registraron hallazgos asociados a esta caminata.');
    }else{
      findings.forEach((item,index)=>{
        ensure(34);
        doc.setFillColor(238,243,246);
        doc.rect(margin,y,usable,8,'F');
        doc.setFont('helvetica','bold');
        doc.setFontSize(9);
        doc.setTextColor(18,61,92);
        doc.text(`${index+1}. ${item.data?.category||'Observación'} · Riesgo ${item.data?.risk||'No informado'}`,margin+3,y+5.5);
        y+=12;
        field('Fecha y hora',fmt(item.data?.recordedAt||item.at));
        field('Descripción',item.data?.text);
        field('Acción inmediata',item.data?.action||'No informada');
        field('Medida correctiva / recomendación',item.data?.recommendation||'No informada');
        field('Responsable',item.data?.responsible||'No informado');
      });
    }

    section('CIERRE');
    field('Supervisor responsable',window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards');
    field('Estado',walk.data?.endAt?'Finalizada':'En curso');
    paragraph('Vista previa temporal. Este PDF no se guarda automáticamente en el teléfono.',8,true);

    const pages=typeof doc.getNumberOfPages==='function'?doc.getNumberOfPages():doc.internal.getNumberOfPages();
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
    $('#eecr-android-pdf-preview')?.remove();
    if(previewUrl){URL.revokeObjectURL(previewUrl);previewUrl=''}
  }

  function showPreview(doc){
    closePreview();
    const buffer=doc.output('arraybuffer');
    const blob=new Blob([buffer],{type:'application/pdf'});
    previewUrl=URL.createObjectURL(blob);
    addStyles();
    const overlay=document.createElement('section');
    overlay.id='eecr-android-pdf-preview';
    overlay.className='eecr-android-preview';
    overlay.setAttribute('role','dialog');
    overlay.setAttribute('aria-modal','true');
    overlay.innerHTML=`<header><div><b>Vista previa PDF · Caminata</b><small>Solo visualización. No se guardó en el teléfono.</small></div><button type="button" data-eecr-android-close>Cerrar</button></header><iframe title="Vista previa PDF de la caminata" src="${esc(previewUrl)}#toolbar=1&navpanes=0&view=FitH"></iframe>`;
    document.body.appendChild(overlay);
  }

  function preview(){
    const walk=currentWalk();
    if(!walk){alert('No fue posible identificar la caminata abierta.');return}
    try{
      showPreview(buildPdf(walk));
      toast('Vista previa abierta. El PDF no se guardó en el teléfono.');
    }catch(error){
      console.error('EECR PDF Android:',error);
      alert('No fue posible mostrar la vista previa PDF. Cierre y vuelva a abrir MANTPRO después de actualizar.');
    }
  }

  // Se ejecuta en window-capture para detener el módulo anterior antes de llegar a document.
  window.addEventListener('click',event=>{
    if(event.target?.closest?.('[data-eecr-preview-walk]')){
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      preview();
      return;
    }
    if(event.target?.closest?.('[data-eecr-android-close]')){
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      closePreview();
    }
  },true);

  window.addEventListener('pagehide',closePreview);
  window.EECR_WALK_ANDROID_FIX={preview,closePreview,build:BUILD};
})();