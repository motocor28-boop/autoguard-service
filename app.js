const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();

const toggle = document.querySelector('.menu-toggle');
const nav = document.getElementById('main-nav');

if (toggle && nav) {
  toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  nav.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      nav.classList.remove('open');
      toggle.setAttribute('aria-expanded', 'false');
    });
  });
}

const diagnosticDetails = {
  'Lectura e interpretación de códigos DTC': [
    'Lectura de códigos activos, pendientes e históricos en los módulos compatibles.',
    'Registro de los códigos antes de cualquier borrado autorizado.',
    'Explicación del sistema o condición relacionada con cada hallazgo.',
    'Resumen técnico para conservar y compartir.'
  ],
  'Revisión de módulos compatibles': [
    'Intento de acceso a motor, transmisión, ABS, airbag y otros módulos disponibles.',
    'La cobertura exacta depende de la marca, modelo, año y equipamiento del vehículo.',
    'Confirmación previa de compatibilidad con los antecedentes enviados por WhatsApp.'
  ],
  'Resumen técnico para el cliente': [
    'Listado de códigos identificados.',
    'Descripción breve de los hallazgos.',
    'Próximas verificaciones recomendadas.',
    'Entrega del resumen por WhatsApp.'
  ],
  'Borrado responsable de códigos, cuando corresponda': [
    'Solo se realiza con autorización del cliente.',
    'Se conservan los códigos registrados antes del borrado.',
    'Borrar un código no corrige la causa de la falla.',
    'El código o testigo puede volver si la condición continúa.'
  ],
  'Confirmación de compatibilidad': [
    'Envía marca, modelo, año y motorización.',
    'Agrega una foto clara del testigo encendido.',
    'AutoGuard confirma el alcance disponible antes de agendar.'
  ],
  'Diagnóstico electrónico avanzado': [
    'El alcance se define según el sistema, el vehículo y la información disponible.',
    'La factibilidad y el valor se confirman exclusivamente por WhatsApp.'
  ]
};

document.querySelectorAll('.price-line').forEach((line) => {
  const serviceName = line.querySelector('span')?.textContent.trim();
  const details = diagnosticDetails[serviceName];
  if (!details || line.closest('.price-item')) return;

  const wrapper = document.createElement('div');
  wrapper.className = 'price-item';
  line.parentNode.insertBefore(wrapper, line);
  wrapper.appendChild(line);

  const detailBox = document.createElement('details');
  detailBox.className = 'price-detail';
  detailBox.innerHTML = `
    <summary>Ver detalle</summary>
    <ul>${details.map((item) => `<li>${item}</li>`).join('')}</ul>`;
  wrapper.appendChild(detailBox);
});

