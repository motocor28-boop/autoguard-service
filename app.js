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

// Carga los estilos de las mejoras sin alterar la estructura original del sitio.
if (!document.querySelector('link[href="enhancements.css"]')) {
  const enhancementStyles = document.createElement('link');
  enhancementStyles.rel = 'stylesheet';
  enhancementStyles.href = 'enhancements.css';
  document.head.appendChild(enhancementStyles);
}

// Acceso visible a la biblioteca de reels desde la navegación principal.
if (nav && !nav.querySelector('a[href="reels.html"]')) {
  const reelsLink = document.createElement('a');
  reelsLink.href = 'reels.html';
  reelsLink.textContent = 'Reels';
  const pricesLink = nav.querySelector('a[href="#precios"]');
  nav.insertBefore(reelsLink, pricesLink || nav.firstChild);
}

// Sección destacada en la página principal para reunir los reels publicados.
const servicesSection = document.getElementById('servicios');
const priceSection = document.getElementById('precios');
if (servicesSection && priceSection && !document.getElementById('reels')) {
  const reelsSection = document.createElement('section');
  reelsSection.className = 'section reels-preview-section';
  reelsSection.id = 'reels';
  reelsSection.innerHTML = `
    <div class="container reels-preview-grid">
      <div class="reels-preview-copy">
        <p class="eyebrow"><span></span>AutoGuard TV</p>
        <h2>Consejos mecánicos en formato reel</h2>
        <p>Ya puedes ver nuestros videos de seguridad, señales de alerta y servicios mecánicos a domicilio.</p>
        <a class="button primary" href="reels.html">Ver biblioteca de reels</a>
      </div>
      <div class="reels-preview-cards" aria-label="Videos publicados">
        <article><b>01 · PUBLICADO</b><strong>Tus frenos te están hablando</strong><span>Ruidos, vibraciones y cambios en el pedal.</span></article>
        <article><b>02 · PUBLICADO</b><strong>AutoGuard Servicios</strong><span>Seguridad mecánica a domicilio.</span></article>
      </div>
    </div>`;
  priceSection.parentNode.insertBefore(reelsSection, priceSection);
}

const serviceDetails = {
  'Diagnóstico y evaluación OBD2': [
    'Lectura de códigos activos e históricos mediante escáner básico OBD2.',
    'Revisión de testigos encendidos y datos disponibles del vehículo.',
    'Borrado de códigos únicamente después de informar el resultado.',
    'Resumen técnico y recomendaciones por WhatsApp.'
  ],
  'AutoGuard Full Check': [
    'Inspección visual de motor, fugas, correas y mangueras accesibles.',
    'Revisión de batería, alternador y condición básica del arranque.',
    'Chequeo visual de frenos, neumáticos, suspensión, luces y niveles.',
    'Registro de hallazgos y prioridades de reparación.'
  ],
  'AutoGuard Compra Segura': [
    'Inspección visual del vehículo antes de la compra.',
    'Revisión de fugas, niveles, batería, frenos, neumáticos y suspensión.',
    'Comprobación de testigos y funcionamiento general disponible en terreno.',
    'Informe de observaciones para apoyar la decisión de compra.'
  ],
  'Combo frenos delanteros': [
    'Desmontaje de ruedas delanteras e inspección de pastillas, discos y cálipers.',
    'Cambio de pastillas delanteras cuando corresponda y esté autorizado.',
    'Limpieza del conjunto y lubricación de puntos de apoyo permitidos.',
    'Montaje, verificación del pedal y prueba funcional básica.'
  ],
  'Combo frenos completo': [
    'Inspección de frenos delanteros y traseros.',
    'Cambio de pastillas o elementos autorizados según configuración del vehículo.',
    'Limpieza, revisión de discos o tambores y condición visible del líquido.',
    'Verificación final del sistema y recomendaciones de seguridad.'
  ],
  'AutoGuard Battery Check': [
    'Medición de voltaje de batería en reposo.',
    'Comprobación básica durante el arranque.',
    'Revisión de carga del alternador y estado visible de terminales.',
    'Recomendación de carga, mantención o reemplazo.'
  ],
  'Cambio de batería': [
    'Retiro seguro de la batería instalada.',
    'Limpieza básica de terminales y revisión de la fijación.',
    'Instalación y conexión de la batería nueva.',
    'Comprobación de encendido y carga básica del sistema.'
  ],
  'Servicio Express': [
    'Evaluación inicial cuando el vehículo no parte o presenta una falla menor.',
    'Revisión básica de batería, conexiones, fusibles y elementos accesibles.',
    'Solución en terreno cuando la falla lo permite y cuenta con autorización.',
    'Orientación técnica cuando se requiere taller, repuesto o reparación mayor.'
  ],
  'Servicio nocturno 22:00–07:00': [
    'Atención coordinada fuera del horario habitual.',
    'Evaluación inicial de no partida, batería, fusibles y fallas menores.',
    'Aplicación del mismo protocolo del Servicio Express.',
    'El valor puede variar según ubicación, horario y complejidad.'
  ],
  'Combo suspensión': [
    'Inspección visual de amortiguadores, bieletas, bujes y rótulas accesibles.',
    'Búsqueda de holguras, daños, fugas y señales de desgaste.',
    'Revisión básica de neumáticos asociada al estado del tren delantero.',
    'Informe de componentes que requieren corrección o revisión especializada.'
  ],
  'Combo dirección segura': [
    'Inspección visual de terminales, extremos, rótulas y componentes accesibles.',
    'Revisión básica de holguras y ruidos informados por el cliente.',
    'Comprobación de fijaciones visibles y condición general del sistema.',
    'Recomendación de reparación y alineación cuando corresponda.'
  ],
  'Escáner básico adicional': [
    'Lectura básica OBD2 añadida a otro servicio contratado.',
    'Identificación de códigos disponibles y testigos relacionados.',
    'No reemplaza un diagnóstico electrónico avanzado ni programación.'
  ],
  'Cambio de ampolletas': [
    'Acceso y retiro de la ampolleta defectuosa cuando el diseño lo permite.',
    'Instalación de la ampolleta compatible suministrada o autorizada.',
    'Prueba de funcionamiento de la luz intervenida.'
  ],
  'Diagnóstico eléctrico': [
    'Revisión inicial de batería, carga, fusibles y conexiones accesibles.',
    'Inspección visual de cableado relacionado con el síntoma informado.',
    'Mediciones básicas para orientar la causa de la falla.',
    'Cotización separada si se requiere desmontaje o reparación avanzada.'
  ],
  'Limpieza cuerpo de aceleración': [
    'Retiro de ductos accesibles y evaluación visual del cuerpo de aceleración.',
    'Limpieza de mariposa y alojamiento con producto apropiado.',
    'Reinstalación, revisión de conexiones y comprobación de ralentí.',
    'Adaptaciones electrónicas especiales se cotizan por separado.'
  ],
  'Limpieza de sensores': [
    'Identificación del sensor accesible relacionado con el servicio.',
    'Inspección del conector y limpieza con producto compatible.',
    'Reinstalación y comprobación básica de funcionamiento.',
    'El servicio no incluye reemplazo del sensor ni reparación del cableado.'
  ],
  'Traslado fuera de Antofagasta': [
    'Recargo por distancia, combustible y tiempo de desplazamiento.',
    'Se informa y aprueba antes de confirmar la atención.',
    'No modifica el alcance ni el valor técnico del servicio contratado.'
  ]
};

// Convierte cada precio en un bloque desplegable que explica exactamente qué incluye.
document.querySelectorAll('.price-line').forEach((line) => {
  if (line.closest('.price-item')) return;
  const serviceName = line.querySelector('span')?.textContent.trim();
  const details = serviceDetails[serviceName];
  if (!details) return;

  const wrapper = document.createElement('div');
  wrapper.className = 'price-item';
  line.parentNode.insertBefore(wrapper, line);
  wrapper.appendChild(line);

  const detailBox = document.createElement('details');
  detailBox.className = 'price-detail';
  detailBox.innerHTML = `
    <summary>Ver qué incluye este servicio</summary>
    <ul>${details.map((item) => `<li>${item}</li>`).join('')}</ul>`;
  wrapper.appendChild(detailBox);
});

// Información adicional en los combos para dejar claro el alcance del mantenimiento.
const comboNotes = {
  'AutoGuard Seguridad': 'Chequeo orientado a seguridad básica: frenos, neumáticos, luces, batería y lectura OBD2 disponible.',
  'AutoGuard Viajero': 'Revisión preventiva para viajes: niveles, frenos, suspensión, batería, alternador y hallazgos prioritarios.',
  'AutoGuard Premium': 'Evaluación ampliada de 30 puntos con registro de hallazgos, informe PDF y atención prioritaria.'
};

document.querySelectorAll('.combo-card').forEach((card) => {
  const title = card.querySelector('h3')?.textContent.trim();
  if (!title || !comboNotes[title] || card.querySelector('.combo-scope')) return;
  const note = document.createElement('p');
  note.className = 'combo-scope';
  note.textContent = comboNotes[title];
  const price = card.querySelector('.combo-price');
  card.insertBefore(note, price || null);
});
