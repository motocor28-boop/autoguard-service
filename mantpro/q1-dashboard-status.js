/* MANTPRO — verificación visual y recarga de casos Q1 2026. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3';
  const BUILD='20260921-q1-cases-v7';
  const read=()=>{try{const v=JSON.parse(localStorage.getItem(STORE)||'[]');return Array.isArray(v)?v:[]}catch{return[]}};
  const counts=()=>{const a=read();return {
    jobs:a.filter(x=>x.type==='job'&&/^q1-job-/.test(x.id||'')).length,
    progress:a.filter(x=>x.type==='progress'&&/^q1-progress-/.test(x.id||'')).length,
    safety:a.filter(x=>x.type==='safety'&&/^q1-safety-/.test(x.id||'')).length,
    walks:a.filter(x=>x.type==='walk'&&/^q1-walk-/.test(x.id||'')).length,
    kpi:a.filter(x=>x.type==='kpi'&&/^q1-kpi-/.test(x.id||'')).length,
    talks:a.filter(x=>x.type==='talk_signed'&&/^q1-talk-/.test(x.id||'')).length
  }};
  const total=c=>Object.values(c).reduce((n,v)=>n+v,0);
  function inject(){
    const app=document.querySelector('#app');if(!app)return;
    const home=/Registro en terreno/i.test(app.textContent||'');
    document.querySelector('#q1-history-panel')?.remove();
    if(!home)return;
    const c=counts();
    const panel=document.createElement('section');panel.id='q1-history-panel';panel.className='card section';
    panel.style.marginTop='18px';panel.innerHTML=`<div class="line"><div><span class="eyebrow">Historial enero–marzo 2026</span><h2 style="margin:.35rem 0">Registros operacionales cargados</h2></div><span class="badge green">${c.jobs} OT</span></div><div class="grid stats" style="margin-top:12px"><div class="card stat"><div class="label">Avances</div><div class="num">${c.progress}</div></div><div class="card stat"><div class="label">Desviaciones</div><div class="num">${c.safety}</div></div><div class="card stat"><div class="label">Caminatas</div><div class="num">${c.walks}</div></div><div class="card stat"><div class="label">KPI</div><div class="num">${c.kpi}</div></div></div><p class="muted">También hay ${c.talks} registros documentales de charlas. Las OT están cerradas, por eso “OT de hoy” y “En ejecución” permanecen en 0.</p><button type="button" class="primary" id="q1-open-jobs">Ver órdenes de enero a marzo</button>`;
    const active=[...app.querySelectorAll('h2')].find(h=>/Trabajos activos/i.test(h.textContent||''));
    if(active)active.before(panel);else app.prepend(panel);
    panel.querySelector('#q1-open-jobs').onclick=()=>document.querySelector('#nav [data-route="jobs"]')?.click();
  }
  let attempts=0;
  function ensure(){
    const c=counts();
    if(c.jobs<9&&window.MANTPRO_Q1_CASES?.load)window.MANTPRO_Q1_CASES.load();
    inject();
    if(++attempts<30)setTimeout(ensure,500);
  }
  window.addEventListener('mantpro-records-changed',()=>setTimeout(inject,80));
  new MutationObserver(()=>setTimeout(inject,20)).observe(document.body,{childList:true,subtree:true});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ensure,{once:true});else ensure();
  window.MANTPRO_Q1_DASHBOARD={counts,inject,build:BUILD};
})();