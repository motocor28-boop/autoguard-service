const guides = [
  {
    number: '01',
    title: 'Qué es un código DTC',
    description: 'Es un registro generado por un módulo cuando detecta una condición fuera de lo esperado. Orienta el diagnóstico, pero no siempre identifica por sí solo una pieza defectuosa.'
  },
  {
    number: '02',
    title: 'Check Engine fijo o parpadeando',
    description: 'Un testigo parpadeando puede indicar una condición más severa. Evita exigir el vehículo y coordina la lectura de códigos para obtener información concreta.'
  },
  {
    number: '03',
    title: 'Por qué no conviene borrar primero',
    description: 'Antes de borrar, se deben registrar los códigos y datos disponibles. El borrado no corrige la causa y puede eliminar información útil para interpretar la falla.'
  }
];

const grid = document.getElementById('reels-grid');
if (grid) {
  grid.innerHTML = guides.map((guide) => `
    <article class="reel-card">
      <div class="reel-poster" aria-hidden="true">
        <span class="reel-number">${guide.number}</span>
        <span class="reel-play">DTC</span>
        <span class="reel-format">OBD</span>
      </div>
      <div class="reel-copy">
        <span>GUÍA AUTOGUARD</span>
        <h3>${guide.title}</h3>
        <p>${guide.description}</p>
      </div>
    </article>
  `).join('');
}

const year = document.getElementById('year');
if (year) year.textContent = new Date().getFullYear();

