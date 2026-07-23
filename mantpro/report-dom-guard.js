/* Evita renderizados repetidos del listado dinámico de informes KPI/EHS. */
(()=>{
  'use strict';
  const d=Object.getOwnPropertyDescriptor(Element.prototype,'innerHTML');
  if(!d?.get||!d?.set)return;
  Object.defineProperty(Element.prototype,'innerHTML',{
    configurable:true,
    enumerable:d.enumerable,
    get(){return d.get.call(this)},
    set(value){
      if(this.id==='ehs-individual-reports'){
        const next=String(value);
        if(this.__mantproReportHtml===next)return;
        this.__mantproReportHtml=next;
      }
      d.set.call(this,value);
    }
  });
})();