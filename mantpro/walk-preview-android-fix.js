/* EECR móvil — vista previa de caminatas compatible con Android, sin guardar archivos. */
(()=>{
  'use strict';
  const BUILD='20260804-walk-preview-html-v3';
  const $=(selector,root=document)=>root.querySelector(selector);
  const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#039;'}[ch]));
  const fmt=value=>{
    if(!value)return 'No registrado';
    const date=new Date(value);
    return Number.isNaN(date.valueOf())?'No registrado':date.toLocaleString('es-CL',{dateStyle:'short',timeStyle:'short',hour12:false});
  };
  const duration=(start,end)=>{
    if(!start||!end)return 'No registrado';
    const ms=Math.max(0,new Date(end)-new Date(start));
    const hours=Math.floor(ms/3600000);
    const minutes=Math.floor(ms%3600000/60000);
    return `${hours} h ${String(minutes).padStart(2,'0')} min`;
  };
  const records=()=>{
    try{
      const value=window.MANTPRO?.records?.();
      return Array.isArray(value)?value:[];
    }catch{return []}
  };
  let currentWalkId='';
  try{currentWalkId=sessionStorage.getItem('eecr-current-walk-id')||''}catch{}

  function rememberWalk(id){
    if(!id)return;
    currentWalkId=id;
    try{sessionStorage.setItem('eecr-current-walk-id',id)}catch{}
  }

  function currentWalk(){
    const all=records();
    let walk=all.find(item=>item?.type==='walk'&&item.id===currentWalkId);
    if(walk)return walk;
    const heading=$('#app h1')?.textContent?.trim()||'';
    walk=all.filter(item=>item?.type==='walk'&&String(item.data?.area||'').trim()===heading)
      .sort((a,b)=>new Date(b.updatedAt||b.at)-new Date(a.updatedAt||a.at))[0]||null;
    if(walk)rememberWalk(walk.id);
    return walk;
  }

  function closePreview(){
    $('#eecr-android-pdf-preview')?.remove();
    document.documentElement.classList.remove('eecr-preview-open');
  }

  function addStyles(){
    if($('#eecr-android-preview-style'))return;
    const style=document.createElement('style');
    style.id='eecr-android-preview-style';
    style.textContent=`
      html.eecr-preview-open,html.eecr-preview-open body{overflow:hidden!important}
      .eecr-android-preview{position:fixed;inset:0;z-index:2147483647;background:#10171c;display:grid;grid-template-rows:auto 1fr;color:#26333c}
      .eecr-android-preview__bar{display:flex;align-items:center;gap:12px;padding:calc(10px + env(safe-area-inset-top)) 14px 11px;background:#18232b;color:#fff;border-bottom:1px solid #3b4a55}
      .eecr-android-preview__bar div{flex:1;min-width:0}.eecr-android-preview__bar b{display:block;font-size:15px}.eecr-android-preview__bar small{display:block;color:#c2ccd2;margin-top:3px}
      .eecr-android-preview__bar button{border:0;border-radius:10px;background:#ff8b18;color:#161616;font-weight:900;padding:11px 16px;min-width:86px}
      .eecr-android-preview__scroll{overflow:auto;padding:16px 10px calc(24px + env(safe-area-inset-bottom));background:#29343b}
      .eecr-pdf-page{box-sizing:border-box;width:min(100%,760px);min-height:1050px;margin:0 auto;background:#fff;box-shadow:0 8px 30px #0008;font-family:Arial,sans-serif;color:#23313a}
      .eecr-pdf-head{background:#12171c;padding:28px 34px 24px;border-bottom:6px solid #ff8b18}.eecr-pdf-head .brand{font-size:12px;letter-spacing:.11em;color:#ff8b18;font-weight:900}.eecr-pdf-head h1{font-size:25px;color:#fff;margin:9px 0 7px}.eecr-pdf-head p{color:#d8e0e5;margin:0;font-size:12px}
      .eecr-pdf-body{padding:28px 34px 40px}.eecr-pdf-section{margin:0 0 24px}.eecr-pdf-section h2{font-size:13px;letter-spacing:.05em;background:#123d5c;color:#fff;margin:0 0 12px;padding:9px 12px;border-radius:3px}
      .eecr-pdf-grid{display:grid;grid-template-columns:1fr 1fr;gap:0;border:1px solid #cad3d9}.eecr-pdf-field{padding:10px 12px;border-right:1px solid #d9e0e4;border-bottom:1px solid #d9e0e4;min-height:45px}.eecr-pdf-field:nth-child(2n){border-right:0}.eecr-pdf-field b{display:block;font-size:10px;text-transform:uppercase;color:#536671;margin-bottom:5px}.eecr-pdf-field span{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}
      .eecr-pdf-finding{border:1px solid #ccd6dc;margin:0 0 13px;border-radius:4px;overflow:hidden}.eecr-pdf-finding__title{padding:9px 11px;background:#eef3f6;color:#123d5c;font-weight:900;font-size:12px}.eecr-pdf-finding__body{padding:11px 12px;font-size:12px;line-height:1.5}.eecr-pdf-finding__body p{margin:4px 0}.eecr-pdf-empty{border:1px dashed #acbac2;padding:18px;text-align:center;color:#657680;font-size:12px}
      .eecr-pdf-sign{margin-top:42px;display:grid;grid-template-columns:1fr 1fr;gap:34px}.eecr-pdf-sign div{border-top:1px solid #596a74;padding-top:8px;font-size:11px;text-align:center}.eecr-pdf-foot{margin-top:30px;border-top:1px solid #d2d9dd;padding-top:9px;color:#6b7b84;font-size:10px;display:flex;justify-content:space-between;gap:15px}
      @media(max-width:560px){.eecr-android-preview__scroll{padding:8px 4px 18px}.eecr-pdf-page{min-height:calc(100vh - 80px)}.eecr-pdf-head{padding:22px 19px 18px}.eecr-pdf-head h1{font-size:20px}.eecr-pdf-body{padding:20px 17px 30px}.eecr-pdf-grid{grid-template-columns:1fr}.eecr-pdf-field,.eecr-pdf-field:nth-child(2n){border-right:0}.eecr-pdf-sign{grid-template-columns:1fr;gap:42px}}
    `;
    document.head.appendChild(style);
  }

  function field(label,value){return `<div class="eecr-pdf-field"><b>${esc(label)}</b><span>${esc(value||'No informado')}</span></div>`}

  function buildPreview(walk){
    const findings=records().filter(item=>item?.type==='safety'&&item.data?.walkId===walk.id)
      .sort((a,b)=>new Date(a.at)-new Date(b.at));
    const findingsHtml=findings.length?findings.map((item,index)=>`
      <article class="eecr-pdf-finding">
        <div class="eecr-pdf-finding__title">${index+1}. ${esc(item.data?.category||'Observación')} · Riesgo ${esc(item.data?.risk||'No informado')}</div>
        <div class="eecr-pdf-finding__body">
          <p><b>Fecha y hora:</b> ${esc(fmt(item.data?.recordedAt||item.at))}</p>
          <p><b>Descripción:</b> ${esc(item.data?.text||'No informada')}</p>
          <p><b>Acción inmediata:</b> ${esc(item.data?.action||'No informada')}</p>
          <p><b>Medida correctiva:</b> ${esc(item.data?.recommendation||'No informada')}</p>
          <p><b>Responsable:</b> ${esc(item.data?.responsible||'No informado')}</p>
        </div>
      </article>`).join(''):'<div class="eecr-pdf-empty">No se registraron hallazgos asociados a esta caminata.</div>';
    const supervisor=window.MANTPRO_CONFIG?.supervisor||'Esteban Cortez Richards';
    return `<article class="eecr-pdf-page" aria-label="Vista previa del informe de caminata">
      <header class="eecr-pdf-head">
        <div class="brand">SISTEMA DE SUPERVISIÓN REMOTO EECR</div>
        <h1>Informe de caminata de seguridad</h1>
        <p>Vista previa generada: ${esc(fmt(new Date().toISOString()))}</p>
      </header>
      <div class="eecr-pdf-body">
        <section class="eecr-pdf-section"><h2>IDENTIFICACIÓN</h2><div class="eecr-pdf-grid">
          ${field('Planta',walk.data?.plant)}${field('Área o sectores recorridos',walk.data?.area)}
          ${field('Objetivo',walk.data?.objective)}${field('Participantes',walk.data?.participants)}
          ${field('Inicio',fmt(walk.data?.startAt||walk.at))}${field('Término',fmt(walk.data?.endAt))}
          ${field('Duración',duration(walk.data?.startAt||walk.at,walk.data?.endAt))}${field('Estado',walk.data?.endAt?'Finalizada':'En curso')}
        </div></section>
        <section class="eecr-pdf-section"><h2>HALLAZGOS Y OBSERVACIONES (${findings.length})</h2>${findingsHtml}</section>
        <section class="eecr-pdf-section"><h2>CIERRE</h2><div class="eecr-pdf-grid">${field('Supervisor responsable',supervisor)}${field('Condición del documento','Solo visualización')}</div></section>
        <div class="eecr-pdf-sign"><div>${esc(supervisor)}<br>Supervisor Mecánico</div><div>Firma / validación de terreno</div></div>
        <footer class="eecr-pdf-foot"><span>EECR · Gestión de caminatas</span><span>No se guardó ningún PDF en el teléfono</span></footer>
      </div>
    </article>`;
  }

  function preview(){
    const walk=currentWalk();
    if(!walk){alert('No fue posible identificar la caminata abierta.');return}
    closePreview();
    addStyles();
    const overlay=document.createElement('section');
    overlay.id='eecr-android-pdf-preview';
    overlay.className='eecr-android-preview';
    overlay.setAttribute('role','dialog');
    overlay.setAttribute('aria-modal','true');
    overlay.innerHTML=`<header class="eecr-android-preview__bar"><div><b>Vista previa PDF · Caminata</b><small>Presentación temporal dentro de MANTPRO. No se guarda.</small></div><button type="button" data-eecr-android-close>Cerrar</button></header><div class="eecr-android-preview__scroll">${buildPreview(walk)}</div>`;
    document.body.appendChild(overlay);
    document.documentElement.classList.add('eecr-preview-open');
  }

  window.addEventListener('click',event=>{
    const open=event.target?.closest?.('[data-open-walk]');
    if(open)rememberWalk(open.dataset.openWalk);
    if(event.target?.closest?.('[data-eecr-preview-walk]')){
      event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();preview();return;
    }
    if(event.target?.closest?.('[data-eecr-android-close]')){
      event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();closePreview();
    }
  },true);
  window.addEventListener('pagehide',closePreview);
  window.EECR_WALK_ANDROID_FIX={preview,closePreview,build:BUILD};
})();
