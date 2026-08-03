/* SISTEMA DE SUPERVISIÓN REMOTO EECR — modo productivo sin registros demostrativos. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3',LEGACY='mantpro-records';
  const IDS=new Set(['eecr-demo-job-001','eecr-demo-progress-001','eecr-demo-safety-001','eecr-demo-walk-001','eecr-demo-walk-safety-001','eecr-demo-kpi-001']);
  const C=window.MANTPRO_CONFIG||{};
  const isDemo=record=>!!record&&(IDS.has(record.id)||/^eecr-demo-/i.test(String(record.id||''))||/^EECR-DEMO-/i.test(String(record.data?.folio||'')));
  const parse=key=>{try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value:[]}catch{return[]}};
  let cleaning=false;
  function cleanLocal({render=false}={}){
    if(cleaning)return false;cleaning=true;
    try{
      let changed=false;
      for(const key of [STORE,LEGACY]){
        const current=parse(key),clean=current.filter(record=>!isDemo(record));
        if(clean.length!==current.length){localStorage.setItem(key,JSON.stringify(clean));changed=true}
      }
      ['eecr-demo-six-pending-v2','eecr-force-build','eecr-demo-six-pending','eecr-demo-loaded'].forEach(key=>localStorage.removeItem(key));
      if(changed){window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{demoRemoved:true,productionMode:true}}));if(render)setTimeout(()=>window.MANTPRO?.render?.(),0)}
      return changed;
    }finally{cleaning=false}
  }
  function cleanInterface(){
    document.querySelector('#eecr-demo-panel')?.remove();
    document.querySelectorAll('[data-simple-demo],[data-eecr-demo-load],[data-eecr-demo-remove]').forEach(node=>node.remove());
    document.querySelectorAll('button,a').forEach(node=>{if(/ejemplos eecr|cargar 6 ejemplos|eliminar ejemplos/i.test(node.textContent||''))node.remove()});
  }
  let cloudCleaning=false;
  async function cleanCloud(){
    if(cloudCleaning||!navigator.onLine||!C.supabaseUrl||!window.MANTPRO_AUTH?.token?.())return false;
    cloudCleaning=true;let ok=true;
    try{
      for(const id of IDS){
        const response=await fetch(`${C.supabaseUrl}/rest/v1/mantpro_records?id=eq.${encodeURIComponent(id)}`,{method:'DELETE',headers:{Prefer:'return=minimal'}});
        if(!response.ok)ok=false;
      }
      if(ok)localStorage.setItem('eecr-no-demo-cloud-clean','1');
      cleanLocal({render:true});
      return ok;
    }catch(error){console.warn('EECR limpieza demostración:',error);return false}
    finally{cloudCleaning=false}
  }
  function productionGuard(){cleanInterface();cleanLocal({render:false})}
  const originalRecords=window.MANTPRO?.records;
  if(typeof originalRecords==='function'&&!originalRecords.__noDemoWrapped){
    const wrapped=function(){const rows=originalRecords.apply(this,arguments);return Array.isArray(rows)?rows.filter(record=>!isDemo(record)):rows};
    wrapped.__noDemoWrapped=true;window.MANTPRO.records=wrapped;
  }
  cleanLocal({render:false});cleanInterface();
  window.addEventListener('mantpro-auth-ready',()=>cleanCloud());
  window.addEventListener('mantpro-auth-changed',()=>cleanCloud());
  window.addEventListener('online',()=>cleanCloud());
  window.addEventListener('mantpro-records-changed',()=>setTimeout(()=>cleanLocal({render:false}),80));
  new MutationObserver(productionGuard).observe(document.body,{childList:true,subtree:true});
  let cycles=0;const timer=setInterval(()=>{const changed=cleanLocal({render:true});cleanInterface();if(changed)cleanCloud();if(++cycles>=80)clearInterval(timer)},750);
  setTimeout(()=>cleanCloud(),800);
  window.EECR_PRODUCTION_MODE={cleanLocal,cleanCloud,isDemo,build:'2026-08-02-no-examples'};
})();
