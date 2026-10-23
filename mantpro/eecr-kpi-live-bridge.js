/* EECR: transferencia incremental, no destructiva, hacia Informe KPI/MantPro local en Windows.
   El navegador de PC recibe antes la sincronización desde el teléfono vía Supabase.
   Compatible con puente preexistente /api/data en 127.0.0.1:8787. */
(()=>{
  'use strict';
  if(/Android|iPhone|iPad|Mobile/i.test(navigator.userAgent))return;
  const API=['http://127.0.0.1:8787','http://localhost:8787'];
  const types={job:'works',progress:'progress',safety:'deviations',walk:'walks',kpi:'technicianEvaluations',talk_signed:'talkCaptures',technician:'technicians'};
  let running=false,last='';let lastSuccess=null;
  const serial=x=>JSON.stringify(x||[]);
  function mapRecord(x){
    const d=x.data&&typeof x.data==='object'?x.data:{};
    const src={id:x.id,createdAt:x.at,updatedAt:x.updatedAt||x.at,sourceApp:'EECR-MANTPRO-PWA',sourceRecord:x};
    switch(x.type){
      case 'job':return {...src,folio:d.folio||x.title||'',plant:d.plant||'',area:d.area||'',equipment:d.equip||'',tag:d.equip||'',type:d.maintenance||'',priority:d.priority||'',description:d.task||x.title||'',technicians:d.technicians||'',plannedStart:d.plannedStart,plannedEnd:d.plannedEnd,actualStart:d.actualStart,actualEnd:d.actualEnd,progress:d.progress||0,sourcePhotos:x.photo?[x.photo]:[]};
      case 'progress':return {...src,workId:d.jobId,timestamp:d.recordedAt||x.at,percent:d.percent??0,notes:d.text||x.title||'',findings:d.findings||'',photoPaths:x.photo?[x.photo]:[]};
      case 'safety':return {...src,workId:d.jobId,walkId:d.walkId,plant:d.plant,area:d.area,category:d.category,risk:d.risk,description:d.text||'',immediateAction:d.action||'',correctiveAction:d.recommendation||'',responsible:d.responsible||'',dueDate:d.dueDate,closedAt:d.closedAt,detectedAt:d.recordedAt||x.at,photoPaths:x.photo?[x.photo]:[]};
      case 'walk':return {...src,folio:d.folio,date:d.startAt||x.at,plant:d.plant,areas:d.area,objective:d.objective,participants:d.participants,startTime:d.startAt,endTime:d.endAt};
      case 'kpi':return {...src,workId:d.jobId,technicianId:d.technician||'',date:d.recordedAt||x.at,score:d.score,technician:d.technician,safetyScore:d.safety,qualityScore:d.quality,productivityScore:d.productivity,documentationScore:d.documentation};
      case 'technician':return {...src,name:d.name||x.title||'',specialty:d.specialty||'',company:d.company||''};
      case 'talk_signed':return {...src,title:x.title||'Charla de seguridad',date:x.at,photoDataUrl:d.photoDataUrl||x.photo||'',status:'recibida',observations:d.observations||''};
      default:return src;
    }
  }
  function join(exists,incoming){
    const original=Array.isArray(exists)?exists:[];
    const byId=new Map(original.filter(x=>x&&x.id!=null).map(x=>[String(x.id),x]));
    const noId=original.filter(x=>!x||x.id==null);
    let updates=0;
    for(const x of incoming){
      const id=String(x.id),old=byId.get(id);
      if(!old){byId.set(id,x);updates++;continue;}
      const newer=Date.parse(x.updatedAt||'')||0, older=Date.parse(old.updatedAt||'')||0;
      if(newer>older){byId.set(id,{...old,...x});updates++;}
    }
    return {rows:[...noId,...byId.values()],updates};
  }
  async function bridge(){
    if(running||!window.MANTPRO?.records)return false;
    running=true;
    try{
      const all=window.MANTPRO.records();
      if(!Array.isArray(all))return false;
      const buckets={};
      for(const x of all){
        if(!x||!x.id||!types[x.type])continue;
        (buckets[types[x.type]]??=[]).push(mapRecord(x));
      }
      const signature=serial(Object.fromEntries(Object.entries(buckets).map(([k,v])=>[k,v.map(x=>[x.id,x.updatedAt])])));
      if(signature===last)return true;
      for(const base of API){
        try{
          const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),3500);
          let r;try{r=await fetch(base+'/api/data',{cache:'no-store',signal:controller.signal});}finally{clearTimeout(timer);}
          if(!r.ok)continue;
          const result=await r.json(),snapshot=result?.data&&typeof result.data==='object'?result.data:{};
          let changed=0;
          for(const [key,items] of Object.entries(buckets)){
            const merged=join(snapshot[key],items);snapshot[key]=merged.rows;changed+=merged.updates;
          }
          if(changed){
            const save=await fetch(base+'/api/data',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:snapshot,clientId:'eecr-pwa-sync-20261023'})});
            if(!save.ok)throw Error('HTTP '+save.status);
          }
          last=signature;lastSuccess=new Date().toISOString();
          window.dispatchEvent(new CustomEvent('eecr-kpi-bridge-synced',{detail:{changed,date:lastSuccess}}));
          return true;
        }catch(error){console.debug('EECR: Informe KPI local no disponible',error);}
      }
      return false;
    }finally{running=false;}
  }
  window.EECR_KPI_BRIDGE={sync:bridge,status:()=>({lastSuccess})};
  const start=()=>{bridge();setInterval(()=>{if(!document.hidden)bridge()},20000);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.addEventListener('mantpro-sync-complete',()=>bridge());
  window.addEventListener('online',()=>bridge());
  window.addEventListener('focus',()=>bridge());
})();
