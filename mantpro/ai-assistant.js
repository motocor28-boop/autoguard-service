/* MANTPRO IA Cloud — asistente transversal de redacción técnica.
   Funciona en modo local seguro y admite un backend IA privado cuando se configure. */
(()=>{
  'use strict';
  const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  let target=null;
  function labelName(label){const c=label.cloneNode(true);c.querySelectorAll('textarea,input,select,button').forEach(x=>x.remove());return c.textContent.replace(/\s+/g,' ').trim()||'Campo del registro'}
  function context(area){const root=area?.closest('form,.report-sheet,#app')||$('#app')||document,title=root.querySelector('h1,h2')?.textContent?.trim()||'Registro MANTPRO',values=[];root.querySelectorAll('label').forEach(l=>{const x=l.querySelector('input,select,textarea');if(!x||x===area||!x.value?.trim()||values.length>=14)return;values.push(`${labelName(l)}: ${x.value.trim()}`)});return{title,values}}
  function clean(v){return String(v||'').trim().replace(/\s+/g,' ').replace(/[.;:,\s]+$/,'')}
  function local(mode,current,field,ctx,notes=''){
    const text=clean(current||notes),key=(field+' '+ctx.title).toLowerCase(),facts=ctx.values.slice(0,8).join('; ');
    if(mode==='missing'){
      const m=[];if(!text)m.push('descripción objetiva');
      if(/desvi|seguridad|hallazgo/.test(key))m.push('ubicación','personas expuestas','acción inmediata','responsable y plazo','verificación');
      else if(/caminata/.test(key))m.push('objetivo','áreas recorridas','participantes','hallazgos y seguimiento');
      else if(/kpi|técnic|evaluación/.test(key))m.push('conductas observadas','fortalezas','brechas','plan de mejora');
      else m.push('equipo o TAG','actividades ejecutadas','hallazgos','pruebas','condición final');
      return `Antes de cerrar, verifique:\n• ${[...new Set(m)].join('\n• ')}\n\nNo complete datos mediante supuestos.`;
    }
    if(mode==='recommend'){
      const base=text||facts||'el antecedente registrado';
      if(/desvi|seguridad|hallazgo/.test(key))return `Se recomienda controlar la condición descrita (${base}), asignar responsable y plazo, priorizar eliminación o ingeniería cuando corresponda y verificar la efectividad antes del cierre.`;
      if(/caminata/.test(key))return `Se recomienda formalizar cada hallazgo con responsable, fecha y evidencia, y comprobar en terreno la efectividad de las acciones antes de cerrar la caminata.`;
      if(/kpi|técnic|evaluación/.test(key))return `Se recomienda acordar una mejora específica y medible, con fecha de revisión, manteniendo la seguridad y la calidad como criterios prioritarios.`;
      return `Se recomienda verificar la condición final, registrar pruebas y pendientes reales, y comunicar cualquier restricción operacional antes de entregar el equipo.`;
    }
    if(mode==='report'){
      const base=text||facts||'No se ingresaron antecedentes suficientes.';
      if(/desvi|seguridad|hallazgo/.test(key))return `ANTECEDENTE OBSERVADO\n${base}.\n\nCONTROL\nRegistrar la acción inmediata aplicada, responsable y plazo.\n\nVERIFICACIÓN\nComprobar la efectividad antes del cierre, sin incorporar causas no demostradas.`;
      if(/caminata/.test(key))return `OBJETIVO Y ALCANCE\n${base}.\n\nDESARROLLO\nSe recorrieron las áreas registradas con los participantes informados.\n\nRESULTADO\nConsolidar hallazgos, acciones, responsables, plazos y evidencia de cierre.`;
      if(/kpi|técnic|evaluación/.test(key))return `RESUMEN DE EVALUACIÓN\n${base}.\n\nFORTALEZAS Y BRECHAS\nFundamentar la evaluación en conductas observables.\n\nPLAN DE MEJORA\nDefinir acción, responsable, plazo y seguimiento.`;
      return `OBJETIVO DEL TRABAJO\n${ctx.title}.\n\nACTIVIDADES EJECUTADAS\n${base}.\n\nRESULTADO Y CONDICIÓN FINAL\nRegistrar hallazgos, pruebas, condición de entrega y pendientes reales.`;
    }
    if(!text&&facts)return `De acuerdo con los antecedentes registrados: ${facts}. Revise y confirme cada dato antes de guardar.`;
    if(/desvi|seguridad|hallazgo/.test(key))return `Durante la inspección se observó ${text}. El antecedente se registra objetivamente para su evaluación, control y seguimiento, sin atribuir causas no verificadas.`;
    if(/caminata/.test(key))return `Durante la caminata de seguridad se registró ${text}. El resultado deberá vincularse con acciones, responsables, plazos y evidencia.`;
    if(/kpi|técnic|evaluación/.test(key))return `En el período evaluado se observó ${text}. La valoración se fundamenta en hechos verificables de seguridad, calidad, cumplimiento y documentación.`;
    return `Durante la ejecución del trabajo se realizaron las siguientes actividades: ${text}. La redacción se limita a los antecedentes registrados y debe revisarse antes de guardar.`;
  }
  async function generate(mode,current,field,ctx,notes){
    const fallback=local(mode,current,field,ctx,notes),endpoint=window.MANTPRO_CONFIG?.aiEndpoint;
    if(!endpoint)return fallback;
    try{const token=window.MANTPRO_AUTH?.token?.()||'',r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify({mode,current,field,context:ctx,notes})}),j=await r.json();if(!r.ok)throw Error(j.error||`Error ${r.status}`);return String(j.text||fallback)}catch(e){console.warn('MANTPRO AI:',e);return fallback+'\n\n[Se utilizó el modo local seguro.]'}
  }
  function close(){document.getElementById('mantpro-ai-overlay')?.remove();target=null}
  function open(area=null){
    close();target=area;const label=area?.closest('label'),field=label?labelName(label):'Borrador general del segmento',ctx=context(area),current=area?.value||'',o=document.createElement('div');o.id='mantpro-ai-overlay';o.className='mantpro-ai-overlay';
    o.innerHTML=`<section class="mantpro-ai-card"><div class="mantpro-ai-head"><div><span>ASISTENCIA IA DE REDACCIÓN</span><h2>${esc(ctx.title)}</h2><p>${esc(field)}</p></div><button type="button" data-ai-close>×</button></div><label>Antecedentes comprobados<textarea id="mantpro-ai-source" placeholder="Escriba hechos, actividades o condiciones observadas.">${esc(current)}</textarea></label><label>Contexto adicional opcional<textarea id="mantpro-ai-notes" placeholder="No incluya supuestos."></textarea></label><div class="mantpro-ai-actions"><button type="button" data-mode="improve">Mejorar texto</button><button type="button" class="primary" data-mode="report">Borrador técnico</button><button type="button" data-mode="recommend">Conclusión</button><button type="button" data-mode="missing">Datos faltantes</button></div><label>Propuesta editable<textarea id="mantpro-ai-result"></textarea></label><div class="mantpro-ai-warning">Revise la propuesta antes de guardarla. El asistente no reemplaza la verificación del supervisor ni puede inventar información.</div><div class="mantpro-ai-foot"><small id="mantpro-ai-state">${window.MANTPRO_CONFIG?.aiEndpoint?'Servicio IA privado disponible':'Modo local seguro'}</small><button type="button" data-copy>Copiar</button>${area?'<button type="button" class="primary" data-apply>Aplicar</button>':''}</div></section>`;
    document.body.appendChild(o);o.querySelector('[data-ai-close]').onclick=close;o.onclick=e=>{if(e.target===o)close()};
    o.querySelectorAll('[data-mode]').forEach(b=>b.onclick=async()=>{const st=o.querySelector('#mantpro-ai-state'),out=o.querySelector('#mantpro-ai-result');st.textContent='Redactando…';b.disabled=true;out.value=await generate(b.dataset.mode,o.querySelector('#mantpro-ai-source').value,field,ctx,o.querySelector('#mantpro-ai-notes').value);st.textContent=window.MANTPRO_CONFIG?.aiEndpoint?'Propuesta generada con IA':'Propuesta generada en modo local';b.disabled=false});
    o.querySelector('[data-copy]').onclick=async()=>{const v=o.querySelector('#mantpro-ai-result').value;if(!v)return;try{await navigator.clipboard.writeText(v)}catch{}o.querySelector('#mantpro-ai-state').textContent='Texto copiado'};
    o.querySelector('[data-apply]')?.addEventListener('click',()=>{const v=o.querySelector('#mantpro-ai-result').value;if(!v)return;target.value=v;target.dispatchEvent(new Event('input',{bubbles:true}));target.dispatchEvent(new Event('change',{bubbles:true}));close()});
  }
  function enhance(){
    $$('label').forEach(l=>{const a=l.querySelector(':scope > textarea');if(!a||a.dataset.aiEnhanced)return;a.dataset.aiEnhanced='1';const b=document.createElement('button');b.type='button';b.className='mantpro-ai-field';b.textContent='✨ Asistencia IA';b.onclick=e=>{e.preventDefault();e.stopPropagation();open(a)};l.insertBefore(b,a)});
    if(!$('#mantpro-ai-float')){const b=document.createElement('button');b.id='mantpro-ai-float';b.className='mantpro-ai-float';b.type='button';b.innerHTML='✨<span>Asistente IA</span>';b.onclick=()=>open();document.body.appendChild(b)}
    const reports=$('#report-form');if(reports&&!$('#mantpro-ai-report-panel')){const p=document.createElement('section');p.id='mantpro-ai-report-panel';p.className='callout section mantpro-ai-report-panel';p.innerHTML='<div><b>Asistente IA para confeccionar reportes</b><br><small>Prepare resumen, conclusión y recomendaciones con datos comprobados.</small></div><button type="button">Abrir asistente</button>';p.querySelector('button').onclick=()=>open();reports.insertAdjacentElement('afterend',p)}
  }
  let t;const refresh=()=>{clearTimeout(t);t=setTimeout(enhance,80)},start=()=>{new MutationObserver(refresh).observe($('#app')||document.body,{childList:true,subtree:true});enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.MANTPRO_AI_ASSISTANT={open,local,build:'2026-07-23-universal-writing'};
})();