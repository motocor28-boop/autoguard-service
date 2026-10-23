/* EECR / HEPI: identification per device, additive to existing MantPro features.
   Does not modify, erase, or migrate any work-order, KPI, safety or photo record. */
(()=>{
  'use strict';
  const KEY='eecr-operator-profile-v1', C=window.MANTPRO_CONFIG||{};
  const originalSupervisor=String(C.supervisor||'').trim();
  const shifts=['Turno Día','Turno Noche','Turno A','Turno B','Turno C','Turno Único'];
  const roles={supervisor:'Supervisor',inspector:'Inspector Técnico de Calidad'};
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const safe=s=>String(s||'').replace(/[\u0000-\u001f\u007f]/g,' ').trim().slice(0,120);
  function read(){
    let v=null;try{v=JSON.parse(localStorage.getItem(KEY)||'null')}catch{}
    const role=v?.role==='inspector'?'inspector':'supervisor';
    return {role,name:safe(v?.name||originalSupervisor),shift:safe(v?.shift||''),configured:!!(v?.name&&v?.shift)};
  }
  let profile=read(),dialog=null,updateQueued=false;
  function current(){return {...profile,roleLabel:roles[profile.role],organization:'HEPI / H-E PARTS INTERNATIONAL'};}
  function applyName(){if(profile.name)C.supervisor=profile.name;}
  function change(next){
    const name=safe(next?.name),shift=safe(next?.shift),role=next?.role;
    if(!roles[role])throw Error('Seleccione Supervisor o Inspector Técnico.');
    if(name.length<3)throw Error('Ingrese el nombre completo (mínimo tres caracteres).');
    if(!shift||shift.length<3)throw Error('Identifique el turno de trabajo.');
    const newValue={role,name,shift};
    // El perfil permanece únicamente en el dispositivo que se está utilizando.
    localStorage.setItem(KEY,JSON.stringify(newValue));
    profile={...newValue,configured:true};
    applyName();refresh();
    window.dispatchEvent(new CustomEvent('eecr-operator-changed',{detail:current()}));
    return current();
  }
  function close(){dialog?.remove();dialog=null;}
  function form(){
    if(dialog)return;
    dialog=document.createElement('div');dialog.id='eecr-profile-dialog';
    dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');
    dialog.setAttribute('aria-label','Identificación de usuario HEPI');
    dialog.className='eecr-profile-backdrop';
    const other=profile.shift&&!shifts.includes(profile.shift);
    dialog.innerHTML='<form id="eecr-operator-form" class="eecr-profile-form">'+
      '<p class="eecr-profile-org">HEPI / H-E PARTS INTERNATIONAL</p>'+
      '<h2>Identificación del usuario</h2>'+
      '<p>Tu cargo, nombre y turno quedarán guardados en este teléfono o computador hasta que los cambies. No se modifican OT, fotografías, KPI ni otros registros.</p>'+
      '<label>Cargo<select name="role"><option value="supervisor">Supervisor</option><option value="inspector">Inspector Técnico de Calidad</option></select></label>'+
      '<label>Nombre completo<input name="name" type="text" autocomplete="name" maxlength="120" required placeholder="Nombre y apellidos"></label>'+
      '<label>Turno<select name="shift" id="eecr-shift-choice">'+shifts.map(s=>'<option value="'+esc(s)+'">'+esc(s)+'</option>').join('')+'<option value="_other">Otro turno</option></select></label>'+
      '<label id="eecr-shift-other-row" hidden>Especificar turno<input name="otherShift" maxlength="80" placeholder="Ej. 7x7, Turno 1"></label>'+
      '<p id="eecr-operator-error" class="eecr-profile-error" role="status"></p>'+
      '<div class="eecr-profile-actions"><button type="button" id="eecr-profile-cancel">Cancelar</button><button type="submit" class="eecr-profile-save">Guardar identificación</button></div>'+
      '</form>';
    document.body.appendChild(dialog);
    const f=dialog.querySelector('form'),selection=f.elements.namedItem('shift'),otherRow=dialog.querySelector('#eecr-shift-other-row');
    f.elements.namedItem('role').value=profile.role;
    f.elements.namedItem('name').value=profile.name;
    selection.value=other?'_other':profile.shift||shifts[0];
    f.elements.namedItem('otherShift').value=other?profile.shift:'';
    const updateOther=()=>{otherRow.hidden=selection.value!=='_other';};
    selection.onchange=updateOther;updateOther();
    dialog.querySelector('#eecr-profile-cancel').onclick=close;
    f.onsubmit=ev=>{
      ev.preventDefault();
      try{
        const shift=selection.value==='_other'?f.elements.namedItem('otherShift').value:selection.value;
        change({role:f.elements.namedItem('role').value,name:f.elements.namedItem('name').value,shift});
        close();
      }catch(e){dialog.querySelector('#eecr-operator-error').textContent=e.message;}
    };
  }
  function badge(){
    let el=document.querySelector('#eecr-operator-button');
    if(!el){
      const header=document.querySelector('.topbar'),before=document.querySelector('#state');
      if(!header)return;
      el=document.createElement('button');el.type='button';el.id='eecr-operator-button';el.className='eecr-operator-badge';
      el.onclick=form;
      if(before)header.insertBefore(el,before);else header.appendChild(el);
    }
    const label=profile.name||'Identificar usuario';
    el.textContent=(profile.role==='inspector'?'ITO · ':'SUP · ')+label.split(/\s+/).slice(0,2).join(' ')+(profile.shift?' · '+profile.shift:' · Definir turno');
    el.title='Editar usuario, cargo y turno — HEPI';
    el.setAttribute('aria-label','Editar identificación: '+roles[profile.role]+', '+label+', '+(profile.shift||'turno sin definir'));
  }
  function home(){
    const app=document.querySelector('#app');
    if(!app)return;
    const isHome=!!app.querySelector('.hero h1') && /Registro en terreno/i.test(app.querySelector('.hero h1')?.textContent||'');
    if(!isHome)return;
    let el=app.querySelector('#eecr-operator-home');
    if(!el){el=document.createElement('section');el.id='eecr-operator-home';el.className='eecr-operator-home';const hero=app.querySelector('.hero');hero?.insertAdjacentElement('afterend',el);}
    el.innerHTML='<div><b>'+esc(roles[profile.role])+'</b><span>'+esc(profile.name||'Usuario por identificar')+' · '+esc(profile.shift||'Turno pendiente')+'</span></div>'+
      '<button type="button" id="eecr-change-operator">Cambiar identificación</button>';
    el.querySelector('button').onclick=form;
  }
  function more(){
    const app=document.querySelector('#app');
    if(!app || !/Más opciones/i.test(app.querySelector('h1')?.textContent||''))return;
    let b=app.querySelector('#eecr-more-profile');
    if(!b){b=document.createElement('button');b.type='button';b.id='eecr-more-profile';b.className='outline';const box=app.querySelector('.stack');box?.insertBefore(b,box.firstChild);}
    b.textContent='Usuario y turno: '+roles[profile.role]+' · '+(profile.shift||'Pendiente');
    b.onclick=form;
  }
  function htmlReport(){
    const sheet=document.querySelector('#app .report-sheet');
    if(!sheet)return;
    let head=sheet.querySelector('#eecr-hepi-report-identity');
    if(!head){head=document.createElement('section');head.id='eecr-hepi-report-identity';head.className='eecr-hepi-report-identity';sheet.insertBefore(head,sheet.firstChild);}
    const code=sessionStorage.getItem('eecr-report-code')||'HEPI-EECR-REGISTRO';
    head.innerHTML='<div class="eecr-hepi-report-title"><b>HEPI / H-E PARTS INTERNATIONAL</b><span>INSPECCIÓN TÉCNICA Y CONTROL DE CALIDAD</span></div>'+
      '<div class="eecr-hepi-report-meta"><span><b>Código:</b> '+esc(code)+'</span><span><b>Revisión:</b> 00</span><span><b>Cargo:</b> '+esc(roles[profile.role])+'</span><span><b>Responsable:</b> '+esc(profile.name)+'</span><span><b>Turno:</b> '+esc(profile.shift||'Sin indicar')+'</span></div>';
    // Solo rotulación de cargo en la vista: no se alteran los registros.
    if(profile.role==='inspector'){
      const walker=document.createTreeWalker(sheet,NodeFilter.SHOW_TEXT);
      const edits=[];while(walker.nextNode()){const t=walker.currentNode;if(t.parentElement?.closest('#eecr-hepi-report-identity'))continue;if(/Supervisor:/i.test(t.nodeValue||''))edits.push(t);}
      edits.forEach(t=>{t.nodeValue=t.nodeValue.replace(/Supervisor:/gi,'Inspector Técnico de Calidad:');});
    }
  }
  function refresh(){badge();home();more();htmlReport();}
  function schedule(){if(updateQueued)return;updateQueued=true;setTimeout(()=>{updateQueued=false;refresh()},80);}
  function start(){
    applyName();refresh();
    // La supervisión de la UI es aditiva: no interfiere con eventos ni formularios originales.
    const root=document.querySelector('#app');
    if(root)new MutationObserver(schedule).observe(root,{childList:true,subtree:false});
    window.addEventListener('eecr-operator-changed',schedule);
    if(!profile.configured)setTimeout(form,650);
  }
  window.EECR_PROFILE={get:current,save:change,edit:form,storageKey:KEY};
  applyName();
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();