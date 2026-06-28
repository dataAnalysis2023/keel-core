// keel SOS — lógica de descifrado y presentación
// Todo ocurre en el navegador. Ningún dato sale del dispositivo.

const MAGIC = 'KSOS';
const SALT_SIZE = 16;
const NONCE_SIZE = 12;
const PBKDF2_ITER = 260_000;

// ── Crypto ────────────────────────────────────────────────────────────────────

async function derivarClave(passphrase, salt) {
  const keyMat = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(passphrase),
    'PBKDF2',
    false,
    ['deriveKey'],
  );
  return crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: PBKDF2_ITER, hash: 'SHA-256' },
    keyMat,
    { name: 'AES-GCM', length: 256 },
    false,
    ['decrypt'],
  );
}

async function descifrarKsos(buffer, passphrase) {
  const data = new Uint8Array(buffer);

  const magic = new TextDecoder().decode(data.slice(0, 4));
  if (magic !== MAGIC) throw new Error('Archivo no reconocido como .ksos');

  let offset = 4;
  const salt   = data.slice(offset, offset + SALT_SIZE);  offset += SALT_SIZE;
  const nonce  = data.slice(offset, offset + NONCE_SIZE); offset += NONCE_SIZE;
  const cipher = data.slice(offset);

  const clave = await derivarClave(passphrase, salt);

  try {
    return await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, clave, cipher);
  } catch {
    throw new Error('Passphrase incorrecto o archivo dañado.');
  }
}

// ── ZIP ───────────────────────────────────────────────────────────────────────

async function leerZip(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const [personaJson, briefingMd, metaJson] = await Promise.all([
    zip.file('persona.json').async('string'),
    zip.file('briefing.md').async('string'),
    zip.file('meta.json').async('string'),
  ]);
  return {
    persona: JSON.parse(personaJson),
    briefing: briefingMd,
    meta: JSON.parse(metaJson),
  };
}

// ── Markdown mínimo ───────────────────────────────────────────────────────────

function mdAHtml(md) {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm,  '<h2>$1</h2>')
    .replace(/^# (.+)$/gm,   '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/^(?!<[hul])(.+)$/gm, '<p>$1</p>')
    .replace(/<p><\/p>/g, '');
}

// ── Semáforo de promesas ──────────────────────────────────────────────────────

function semaforo(fechaLimite) {
  if (!fechaLimite) return '🟢';
  const hoy = new Date();
  const limite = new Date(fechaLimite);
  const dias = Math.ceil((limite - hoy) / 86_400_000);
  if (dias <= 2) return '🔴';
  if (dias <= 5) return '🟡';
  return '🟢';
}

// ── UI ────────────────────────────────────────────────────────────────────────

let archivoSeleccionado = null;

const zonaArchivo     = document.getElementById('zona-archivo');
const inputArchivo    = document.getElementById('input-archivo');
const nombreArchivo   = document.getElementById('nombre-archivo');
const inputPass       = document.getElementById('input-pass');
const btnDescifrar    = document.getElementById('btn-descifrar');
const errorMsg        = document.getElementById('error-msg');
const spinner         = document.getElementById('spinner');
const pantallaInicio  = document.getElementById('pantalla-inicio');
const pantallaResult  = document.getElementById('pantalla-resultado');

// Zona drag & drop
zonaArchivo.addEventListener('click', () => inputArchivo.click());
zonaArchivo.addEventListener('dragover', e => { e.preventDefault(); zonaArchivo.classList.add('drag-over'); });
zonaArchivo.addEventListener('dragleave', () => zonaArchivo.classList.remove('drag-over'));
zonaArchivo.addEventListener('drop', e => {
  e.preventDefault();
  zonaArchivo.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) seleccionarArchivo(f);
});

inputArchivo.addEventListener('change', () => {
  if (inputArchivo.files[0]) seleccionarArchivo(inputArchivo.files[0]);
});

function seleccionarArchivo(f) {
  archivoSeleccionado = f;
  nombreArchivo.textContent = f.name;
  nombreArchivo.classList.remove('oculto');
  errorMsg.classList.add('oculto');
}

// Enter en passphrase dispara descifrado
inputPass.addEventListener('keydown', e => { if (e.key === 'Enter') btnDescifrar.click(); });

btnDescifrar.addEventListener('click', async () => {
  errorMsg.classList.add('oculto');

  if (!archivoSeleccionado) return mostrarError('Selecciona un archivo .ksos primero.');
  const pass = inputPass.value.trim();
  if (!pass) return mostrarError('Ingresa tu passphrase.');

  btnDescifrar.disabled = true;
  spinner.classList.remove('oculto');

  try {
    const buffer = await archivoSeleccionado.arrayBuffer();
    const zipBuffer = await descifrarKsos(buffer, pass);
    const { persona, briefing, meta } = await leerZip(zipBuffer);
    mostrarResultado(persona, briefing, meta);
  } catch (err) {
    mostrarError(err.message);
  } finally {
    btnDescifrar.disabled = false;
    spinner.classList.add('oculto');
  }
});

function mostrarError(msg) {
  errorMsg.textContent = msg;
  errorMsg.classList.remove('oculto');
}

// ── Pantalla de resultado ─────────────────────────────────────────────────────

function mostrarResultado(persona, briefing, meta) {
  pantallaInicio.style.display = 'none';
  pantallaResult.style.display = 'flex';

  // Cabecera
  document.getElementById('res-nombre').textContent = persona.nombre;
  const badge = document.getElementById('res-relacion');
  if (persona.tipo_relacion) {
    badge.textContent = persona.tipo_relacion;
    badge.classList.remove('oculto');
  }

  // Narrativa
  const secNarrativa = document.getElementById('sec-narrativa');
  if (persona.narrativa) {
    document.getElementById('res-narrativa').textContent = persona.narrativa;
  } else {
    secNarrativa.classList.add('oculto');
  }

  // Promesas pendientes
  const secPromesas = document.getElementById('sec-promesas');
  const listaPromesas = document.getElementById('res-promesas');
  const pendientes = (persona.promesas_pendientes || []).filter(p => !p.completada);
  if (pendientes.length) {
    listaPromesas.innerHTML = pendientes.map(p => `
      <div class="promesa-item">
        <span class="semaforo">${semaforo(p.fecha_limite)}</span>
        <span>${p.descripcion}${p.fecha_limite ? ` <span style="color:var(--texto-dim);font-size:0.8rem">[${p.fecha_limite}]</span>` : ''}</span>
      </div>
    `).join('');
  } else {
    secPromesas.classList.add('oculto');
  }

  // Briefing completo
  document.getElementById('res-briefing').innerHTML = mdAHtml(briefing);

  // Contexto situacional
  const secContexto = document.getElementById('sec-contexto');
  if (persona.contexto_situacional) {
    document.getElementById('res-contexto').textContent = persona.contexto_situacional;
  } else {
    secContexto.classList.add('oculto');
  }

  // Metadatos
  document.getElementById('res-meta').textContent =
    `Generado ${meta.fecha} · ${meta.perfil_nombre}`;

  // Botón copiar briefing
  document.getElementById('btn-copiar-briefing').addEventListener('click', () => {
    navigator.clipboard.writeText(briefing).then(() => {
      const btn = document.getElementById('btn-copiar-briefing');
      btn.textContent = '✓ Copiado';
      btn.classList.add('copiado');
      setTimeout(() => { btn.textContent = 'Copiar briefing'; btn.classList.remove('copiado'); }, 2000);
    });
  });
}

document.getElementById('btn-volver').addEventListener('click', () => {
  pantallaInicio.style.display = 'flex';
  pantallaResult.style.display = 'none';
  archivoSeleccionado = null;
  inputArchivo.value = '';
  inputPass.value = '';
  nombreArchivo.classList.add('oculto');
});

// ── Service Worker ────────────────────────────────────────────────────────────

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('./sw.js').catch(() => {});
}
