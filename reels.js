const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();

/* Biblioteca de videos publicados. Los archivos se sirven desde /reels. */
const reels = [
  {
    category: 'FRENOS Y SEGURIDAD',
    title: 'Tus frenos te están hablando',
    description: 'Ruidos al frenar, vibraciones o cambios en el pedal son señales que requieren una revisión profesional.',
    video: 'reels/tus-frenos-te-estan-hablando.mp4',
    poster: 'assets/autoguard-frenos-premium.png',
    layout: 'vertical'
  },
  {
    category: 'AUTOGUARD SERVICIOS',
    title: 'Seguridad mecánica a domicilio',
    description: 'Conoce nuestros servicios de frenos, baterías, asistencia rápida y chequeos preventivos en Antofagasta.',
    video: 'reels/autoguard-servicios-a-domicilio.mp4',
    poster: 'assets/autoguard-menu-premium.png',
    layout: 'wide'
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
    <article class="reel-card${reel.layout === 'wide' ? ' reel-card-wide' : ''}">
      <div class="reel-media${reel.layout === 'wide' ? ' reel-media-wide' : ''}">${createMedia(reel)}</div>
      <div class="reel-body">
        <span class="reel-kicker">${reel.category}</span>
        <h3>${reel.title}</h3>
        <p>${reel.description}</p>
        <div class="reel-actions">
          ${reel.video ? `<a href="${reel.video}" target="_blank" rel="noopener">Abrir video</a>` : ''}
          <a href="${whatsappUrl}" target="_blank" rel="noopener">Agendar revisión</a>
        </div>
      </div>
    </article>`).join('');
}
