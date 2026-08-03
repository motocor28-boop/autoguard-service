/* MANTPRO IA Cloud — interfaz móvil simplificada y sin controles redundantes. */
(()=>{
  'use strict';
  const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)];
  const text=node=>node?.textContent?.replace(/\s+/g,' ').trim()||'';
  function route(name){
    closeActions();
    try{if(window.MANTPRO?.go){window.MANTPRO.go(name);return}}catch{}
    const direct=$(`[data-go="${name}"]`);if(direct){direct.click();return}
    $('[data-route="home"]')?.click();setTimeout(()=>document.querySelector(`[data-go="${name}"]`)?.click(),120);
  }
  function closeActions(){$('#simple-actions-overlay')?.remove()}
  function openActions(){
    closeActions();const overlay=document.createElement('div');overlay.id='simple-actions-overlay';overlay.className='simple-actions-overlay';
    overlay.innerHTML=`<section class="simple-actions-sheet"><header><div><span>ACCIÓN RÁPIDA</span><h2>¿Qué necesita registrar?</h2></div><button type="button" data-simple-close>×</button></header><div class="simple-action-grid"><button type="button" data-simple-route="job_new"><b>▣</b><span>Nueva OT</span></button><button type="button" data-simple-route="progress_new"><b>＋</b><span>Avance</span></button><button type="button" data-simple-route="safety_new"><b>⚠</b><span>Desviación</span></button><button type="button" data-simple-route="walk_new"><b>◉</b><span>Caminata</span></button><button type="button" data-simple-photo><b>📷</b><span>Fotografía</span></button><button type="button" data-simple-ai><b>✨</b><span>Redacción IA</span></button></div><button type="button" class="simple-sync" data-simple-sync>↻ Sincronizar ahora</button></section>`;
    document.body.appendChild(overlay);overlay.querySelector('[data-simple-close]').onclick=closeActions;overlay.onclick=e=>{if(e.target===overlay)closeActions()};overlay.querySelectorAll('[data-simple-route]').forEach(button=>button.onclick=()=>route(button.dataset.simpleRoute));overlay.querySelector('[data-simple-photo]').onclick=()=>{closeActions();window.MANTPRO_PHOTO_DESCRIPTIONS?.open?.()};overlay.querySelector('[data-simple-ai]').onclick=()=>{closeActions();window.MANTPRO_AI_ASSISTANT?.open?.()};overlay.querySelector('[data-simple-sync]').onclick=async button=>{button.disabled=true;button.textContent='Sincronizando…';try{await window.MANTPRO?.sync?.();button.textContent='✓ Sincronizado'}catch{button.textContent='No fue posible sincronizar'}setTimeout(closeActions,900)};
  }
  function actionButton(){if($('#simple-action-button'))return;const button=document.createElement('button');button.id='simple-action-button';button.type='button';button.innerHTML='<b>＋</b><span>Acción</span>';button.onclick=openActions;document.body.appendChild(button)}
  function hideLegacyPhoto(form){form.querySelector('[data-stage-panel]')?.setAttribute('hidden','');form.querySelector('[data-photo]')?.setAttribute('hidden','');form.querySelector('#photo-preview')?.setAttribute('hidden','');const photoType=form.querySelector('[name="photoType"]');photoType?.closest('label')?.setAttribute('hidden','')}
  function moveIntoDetails(nodes,title,open=false){const valid=nodes.filter(Boolean).filter(node=>!node.closest('details.simple-details'));if(!valid.length)return null;const details=document.createElement('details');details.className='simple-details';details.open=open;details.innerHTML=`<summary>${title}</summary><div class="simple-details-body"></div>`;valid[0].parentNode.insertBefore(details,valid[0]);const body=details.querySelector('.simple-details-body');valid.forEach(node=>body.appendChild(node));return details}
  function simplifyForm(form){
    if(form.dataset.simpleUi)return;form.dataset.simpleUi='1';hideLegacyPhoto(form);
    const type=form.dataset.form;
    const dateFields=$$('.manual-date-time',form);
    if(dateFields.length)moveIntoDetails(dateFields,type==='job'?'Programación opcional':'Cambiar fecha y hora',false);
    if(type==='safety'){
      const recommendation=form.querySelector('[name="recommendation"]')?.closest('label');
      const responsible=form.querySelector('[name="responsible"]')?.closest('.grid')||form.querySelector('[name="responsible"]')?.closest('label');
      moveIntoDetails([recommendation,responsible],'Seguimiento y cierre (opcional)',false);
    }
    $$('button.mantpro-ai-field',form).forEach(button=>button.textContent='✨ Redactar');
  }
  function wrapManualSection(app){
    if(app.querySelector('details.simple-manual-times'))return;
    const headings=$$('h2',app).filter(h=>/Registro manual de fechas y horas/i.test(text(h)));
    headings.forEach(heading=>{const nodes=[heading],next=heading.nextElementSibling;if(next&&next.classList.contains('callout'))nodes.push(next);const section=nodes[nodes.length-1].nextElementSibling;if(section?.classList.contains('manual-time'))nodes.push(section);const details=moveIntoDetails(nodes,'Ajustar fechas y horas',false);if(details)details.classList.add('simple-manual-times')});
  }
  function simplifyHome(app){
    const h1=app.querySelector('h1');if(!/Registro en terreno/i.test(text(h1)))return;
    app.classList.add('simple-home');
    const hero=h1.closest('.hero');if(hero){const p=hero.querySelector('p');if(p)p.textContent='Registre trabajos, seguridad y evidencias desde el teléfono.'}
    const quickHeading=$$('h2',app).find(h=>/Acciones rápidas/i.test(text(h)));if(quickHeading){quickHeading.hidden=true;quickHeading.nextElementSibling?.setAttribute('hidden','')}
  }
  function simplifyReports(app){
    if(!/^Informes$/i.test(text(app.querySelector('h1'))))return;
    app.classList.add('simple-reports');
    const form=$('#report-form',app);if(form)form.hidden=true;
    $('#mantpro-ai-report-panel',app)?.setAttribute('hidden','');
    const center=$('#mantpro-ehs-report-center',app);if(center){center.classList.add('simple-report-center');const title=center.querySelector('h2');if(title)title.textContent='Generar informe';const individual=$('#ehs-individual-reports',center);if(individual&&!individual.closest('details'))moveIntoDetails([individual],'Informes individuales',false)}
    if(!app.querySelector('details.simple-job-reports')){const heading=$$('h2',app).find(h=>/Informes por trabajo/i.test(text(h)));if(heading&&heading.nextElementSibling){const details=moveIntoDetails([heading,heading.nextElementSibling],'Informes por orden de trabajo',false);details?.classList.add('simple-job-reports')}}
  }
  function simplifyMore(app){
    if(!/^Más opciones$/i.test(text(app.querySelector('h1')))||app.dataset.simpleMore)return;app.dataset.simpleMore='1';
    const stack=app.querySelector('.stack');if(!stack)return;
    const info=stack.querySelector('.callout');
    const make=(title,subtitle)=>{const section=document.createElement('section');section.className='simple-more-section';section.innerHTML=`<h2>${title}</h2><p>${subtitle}</p><div class="simple-more-actions"></div>`;stack.insertBefore(section,info||null);return section.querySelector('.simple-more-actions')};
    const personal=make('Personal y evaluación','Técnicos y resultados KPI.');
    [stack.querySelector('[data-go="technician_new"]'),stack.querySelector('[data-go="kpi_overview"]')].filter(Boolean).forEach(node=>personal.appendChild(node));
    const data=make('Datos y sincronización','Guardar, recuperar o sincronizar información.');
    [$('#sync-now',stack),$('#backup',stack),$('#restore',stack),$('#choose-backup',stack)].filter(Boolean).forEach(node=>data.appendChild(node));
    const application=make('Aplicación','Instalación, ayuda y sesión.');
    [$('#install',stack),$('#guide',stack),$('#signout',stack)].filter(Boolean).forEach(node=>application.appendChild(node));
    const reset=$('#reset',stack);if(reset){reset.textContent='Respaldar y comenzar desde cero';const danger=app.querySelector('#danger-record-zone')||make('Zona de cuidado','Acciones irreversibles o de reinicio.').closest('.simple-more-section');(danger.querySelector?.('.simple-more-actions')||danger).appendChild(reset)}
  }
  function enhance(){
    actionButton();$('.install-guide-link')?.setAttribute('hidden','');
    $('#mantpro-ai-float')?.setAttribute('hidden','');$('#mantpro-photo-float')?.setAttribute('hidden','');$('#mantpro-photo-desc-float')?.setAttribute('hidden','');
    const app=$('#app');if(!app)return;
    simplifyHome(app);$$('#record-form[data-form]',app).forEach(simplifyForm);wrapManualSection(app);simplifyReports(app);simplifyMore(app);
  }
  let timer;const refresh=()=>{clearTimeout(timer);timer=setTimeout(enhance,90)},start=()=>{new MutationObserver(refresh).observe(document.body,{childList:true,subtree:true});enhance()};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
  window.MANTPRO_SIMPLE_UI={openActions,build:'2026-08-02-simple-mobile'};
})();
