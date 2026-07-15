const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();

/*
  Para publicar un nuevo reel:
  1. Sube el MP4 a la carpeta /reels del repositorio o usa una URL pública.
  2. Agrega una nueva ficha al inicio de este listado.
  3. Completa video: 'reels/nombre-del-video.mp4'.
*/
const reels = [
  {
    category: 'FRENOS Y SEGURIDAD',
    title: 'Señales de alerta en el sistema de frenos',
    description: 'Ruidos, vibraciones, pedal diferente y señales que requieren una revisión profesional.',
    video: '',
    poster: 'assets/autoguard-frenos-premium.png',
    status: 'PRÓXIMAMENTE'
  },
  {
    category: 'BATERÍA Y ARRANQUE',
    title: 'Cómo anticipar una falla de batería',
    description: 'Síntomas frecuentes antes de que el vehículo deje de arrancar y qué revisar a tiempo.',
    video: '',
    poster: 'assets/autoguard-menu-premium.png',
    status: 'PRÓXIMAMENTE'
  },
  {
    category: 'MANTENCIÓN PREVENTIVA',
    title: 'Chequeos esenciales antes de viajar',
    description: 'Frenos, neumáticos, niveles, batería y elementos de seguridad que conviene revisar.',
    video: '',
    poster: 'logo.svg',
    status: 'PRÓXIMAMENTE'
  }
];

const grid = document.getElementById('reels-grid');
const whatsappUrl = 'https://wa.me/56977482821?text=Hola%20AutoGuard%2C%20vi%20sus%20reels%20y%20quiero%20agendar%20una%20revisi%C3%B3n';

function createMedia(reel) {
  if (reel.video) {
    return `
      <video controls preload="metadata" playsinline poster="${reel.poster || ''}">
        <source src="${reel.video}" type="video/mp4">
        Tu navegador no puede reproducir este video.
      </video>`;
  }

  return `
    <div class="reel-placeholder">
      <div>
        <img src="${reel.poster || 'logo.svg'}" alt="" loading="lazy">
        <span>${reel.status || 'PRÓXIMAMENTE'}</span>
      </div>
    </div>`;
}

if (grid) {
  grid.innerHTML = reels.map((reel) => `
    <article class="reel-card">
      <div class="reel-media">${createMedia(reel)}</div>
      <div class="reel-body">
        <span class="reel-kicker">${reel.category}</span>
        <h3>${reel.title}</h3>
        <p>${reel.description}</p>
        <div class="reel-actions">
          ${reel.video ? `<a href="${reel.video}" target="_blank" rel="noopener">Abrir video</a>` : '<a href="#videos" aria-disabled="true">En preparación</a>'}
          <a href="${whatsappUrl}" target="_blank" rel="noopener">Agendar revisión</a>
        </div>
      </div>
    </article>`).join('');
}
