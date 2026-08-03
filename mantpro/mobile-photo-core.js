/* MANTPRO IA Cloud — núcleo fotográfico sin interfaz duplicada. */
(()=>{
  'use strict';
  const STORE='mantpro-records-v3',LEGACY='mantpro-records';
  const parse=key=>{try{const value=JSON.parse(localStorage.getItem(key)||'[]');return Array.isArray(value)?value:[]}catch{return[]}};
  const categories={
    job:['Antes del trabajo','Durante el trabajo','Después del trabajo','Hallazgo técnico','Medida inmediata','Condición corregida'],
    progress:['Durante el trabajo','Después del trabajo','Hallazgo técnico','Medida inmediata','Condición corregida'],
    safety:['Desviación o hallazgo detectado','Medida inmediata aplicada','Condición corregida','Verificación de cierre'],
    walk:['Vista general de la caminata','Hallazgo de caminata','Medida inmediata aplicada','Condición corregida'],
    kpi:['Evidencia de desempeño','Evidencia de seguridad','Evidencia de calidad']
  };
  function records(){
    const sources=[];
    try{const live=window.MANTPRO?.records?.();if(Array.isArray(live))sources.push(live)}catch{}
    sources.push(parse(STORE),parse(LEGACY));
    const map=new Map();
    sources.flat().forEach(record=>{
      if(!record?.id)return;
      const previous=map.get(record.id);
      const previousDate=new Date(previous?.updatedAt||previous?.at||0);
      const currentDate=new Date(record.updatedAt||record.at||0);
      if(!previous||currentDate>=previousDate)map.set(record.id,record);
    });
    return [...map.values()];
  }
  function write(record){
    const all=parse(STORE),index=all.findIndex(item=>item.id===record.id);
    if(index<0)all.push(record);else all[index]=record;
    localStorage.setItem(STORE,JSON.stringify(all));
  }
  function attachToRecord(record,photos){
    if(!record||!Array.isArray(photos)||!photos.length)return false;
    record.data=record.data||{};
    record.data.stagePhotos=[...(Array.isArray(record.data.stagePhotos)?record.data.stagePhotos:[]),...photos];
    record.updatedAt=new Date().toISOString();
    record.dirty=true;
    record.synced=false;
    write(record);
    window.dispatchEvent(new CustomEvent('mantpro-records-changed',{detail:{id:record.id,type:record.type,photos:photos.length}}));
    try{window.MANTPRO?.sync?.()}catch{}
    return true;
  }
  window.MANTPRO_STAGE_PHOTOS={categories,attachToRecord,records,build:'2026-08-02-photo-core'};
})();
