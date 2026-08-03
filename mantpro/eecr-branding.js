/* SISTEMA DE SUPERVISIÓN REMOTO EECR — identidad e identificación de informes. */
(()=>{
  'use strict';
  const FULL='SISTEMA DE SUPERVISIÓN REMOTO EECR';
  const SHORT='SUPERVISIÓN REMOTA EECR';
  const $=(s,r=document)=>r.querySelector(s);
  const records=()=>{try{return window.MANTPRO?.records?.()||[]}catch{return[]}};
  const localDay=()=>{const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-')};
  const selectedDay=()=>$('#ehs-report-date')?.value||$('#report-form [name="date"]')?.value||sessionStorage.getItem('mantpro-report-day')||localDay();
  const compactDay=value=>String(value||selectedDay()).replace(/-/g,'');
  const tail=value=>String(value||'REG').replace(/[^a-z0-9]/gi,'').slice(-6).toUpperCase()||'REG';
  const jobById=id=>records().find(x=>x.id===id&&x.type==='job');
  function reportContext(button){
    const day=selectedDay();
    if(button?.dataset?.pdfSafetyId)return{type:'DES',id:button.dataset.pdfSafetyId,code:`EECR-DES-${compactDay(day)}-${tail(button.dataset.pdfSafetyId)}`};
    if(button?.dataset?.pdfWalkId)return{type:'CAM',id:button.dataset.pdfWalkId,code:`EECR-CAM-${compactDay(day)}-${tail(button.dataset.pdfWalkId)}`};
    if(button?.dataset?.pdfKpiId)return{type:'KPI',id:button.dataset.pdfKpiId,code:`EECR-KPI-${compactDay(day)}-${tail(button.dataset.pdfKpiId)}`};
    if(button?.matches?.('[data-pdf-job]')){
      const id=sessionStorage.getItem('mantpro-active-report-job')||'';
      const job=jobById(id);
      const folio=String(job?.data?.folio||tail(id)).replace(/[^a-z0-9-]/gi,'').toUpperCase();
      return{type:'OT',id,code:`EECR-OT-${folio}`};
    }
    if(button?.matches?.('[data-pdf-safety-day]'))return{type:'SEG',code:`EECR-SEG-${compactDay(day)}`};
    if(button?.matches?.('[data-pdf-walks-day]'))return{type:'CAM',code:`EECR-CAM-${compactDay(day)}`};
    if(button?.matches?.('[data-pdf-kpi-day]'))return{type:'KPI',code:`EECR-KPI-${compactDay(day)}`};
    if(button?.matches?.('[data-pdf-ehs]'))return{type:'EHS',code:`EECR-EHS-${compactDay(day)}`};
    if(button?.matches?.('[data-pdf-daily]'))return{type:'DIA',code:`EECR-DIA-${compactDay(day)}`};
    return{type:'REG',code:`EECR-REG-${compactDay(day)}`};
  }
  let current={type:'REG',code:`EECR-REG-${compactDay()}`};
  window.addEventListener('click',event=>{
    const button=event.target?.closest?.('[data-pdf-job],[data-pdf-daily],[data-pdf-ehs],[data-pdf-safety-day],[data-pdf-walks-day],[data-pdf-kpi-day],[data-pdf-safety-id],[data-pdf-walk-id],[data-pdf-kpi-id]');
    if(!button)return;
    current=reportContext(button);
    sessionStorage.setItem('eecr-report-code',current.code);
  },true);
  function replaceText(root=document.body){
    if(!root)return;
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    nodes.forEach(node=>{if(/MANTPRO IA Cloud|MANTPRO IA/i.test(node.nodeValue||''))node.nodeValue=node.nodeValue.replace(/MANTPRO IA Cloud|MANTPRO IA/gi,FULL)});
    const brand=$('.brand');
    if(brand&&brand.dataset.eecrBrand!=='1'){brand.dataset.eecrBrand='1';brand.innerHTML='<b>SUPERVISIÓN <i>EECR</i></b><small>Remota</small>'}
    const authTitle=$('#auth-overlay h1');
    if(authTitle&&authTitle.textContent!==`Ingresar al ${FULL}`)authTitle.textContent=`Ingresar al ${FULL}`;
    if(document.title!==FULL)document.title=FULL;
  }
  function previewIdentifier(){
    const sheet=$('.report-sheet');if(!sheet)return;
    const code=sessionStorage.getItem('eecr-report-code')||reportContext(sheet.querySelector('[data-pdf-job],[data-pdf-daily]')).code;
    let tag=$('.eecr-report-id',sheet);
    if(!tag){tag=document.createElement('p');tag.className='eecr-report-id';const h1=sheet.querySelector('h1');h1?.insertAdjacentElement('afterend',tag)}
    if(tag&&tag.dataset.code!==code){tag.dataset.code=code;tag.innerHTML=`<b>Registro:</b> ${code}`}
  }
  function patchJsPdf(){
    const API=window.jspdf?.jsPDF?.API;if(!API||API.__eecrPatched)return false;
    const original=API.text;
    API.text=function(value,x,y,...rest){
      let text=value;
      if(typeof text==='string'){
        if(/MANTPRO IA/i.test(text)){
          text=FULL;
          try{this.setFontSize((this.getFontSize?.()||11)>13?11:7.5)}catch{}
        }else if(/^Informe |^Reporte /i.test(text)){
          this.__eecrAwaitingSubtitle=true;
        }else if(this.__eecrAwaitingSubtitle&&Number(y)>=30&&Number(y)<=38){
          const code=sessionStorage.getItem('eecr-report-code')||current.code;
          text=`${text} · Registro: ${code}`;
          this.__eecrAwaitingSubtitle=false;
        }
      }
      return original.call(this,text,x,y,...rest);
    };
    API.__eecrPatched=true;return true;
  }
  let timer;
  function enhance(){clearTimeout(timer);timer=setTimeout(()=>{replaceText();previewIdentifier();patchJsPdf()},60)}
  const start=()=>{new MutationObserver(enhance).observe(document.body,{childList:true,subtree:true});enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.EECR_IDENTITY={full:FULL,short:SHORT,reportContext,current:()=>current,build:'2026-08-02-eecr'};
})();
