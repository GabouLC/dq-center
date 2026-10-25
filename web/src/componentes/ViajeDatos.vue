<script setup lang="ts">
import { BadgeCheck, Briefcase, Database, FileInput, FileText, Lock, RotateCcw, ShieldCheck } from 'lucide-vue-next'
import { ref } from 'vue'

/**
 * Cómo viajan los datos: RAW → MASTER → Gate → BUSINESS. Un archivo recorre la franja una
 * sola vez: entra a MASTER y sale cifrado, entra al Gate y sale certificado, y llega a negocio.
 * Es explicativo (recorrido guiado e inicio de sesión), no se repite solo; «Ver de nuevo» lo
 * vuelve a reproducir. Con «reducir movimiento» se ve directamente el estado final.
 */
withDefaults(defineProps<{ tono?: 'claro' | 'oscuro'; repetible?: boolean; retraso?: number }>(), {
  tono: 'claro',
  repetible: false,
  retraso: 0,
})

const ESTACIONES = [
  { clave: 'raw', nombre: 'RAW', que: 'Llega el archivo tal cual', icono: FileInput, t: 0 },
  { clave: 'master', nombre: 'MASTER', que: 'Se ordena y se cifran los datos personales', icono: Database, t: 0.26 },
  { clave: 'gate', nombre: 'Gate', que: 'Control de calidad y privacidad', icono: ShieldCheck, t: 0.6 },
  { clave: 'business', nombre: 'BUSINESS', que: 'Solo lo certificado llega a negocio', icono: Briefcase, t: 0.92 },
]
const vuelta = ref(0)
</script>

<template>
  <div class="viaje" :class="tono" :style="{ '--r': `${vuelta ? 0 : retraso}ms` }">
    <div :key="vuelta" class="escena">
      <div class="riel" aria-hidden="true"><span class="relleno" /></div>
      <div class="carro" aria-hidden="true">
        <span class="ficha doc"><FileText :size="14" :stroke-width="2.4" /></span>
        <span class="ficha cifrada"><Lock :size="13" :stroke-width="2.6" /></span>
        <span class="ficha certificada"><BadgeCheck :size="14" :stroke-width="2.4" /></span>
      </div>
      <ol class="estaciones" aria-label="Cómo viajan los datos">
        <li v-for="e in ESTACIONES" :key="e.clave" :class="e.clave" :style="{ '--t': e.t }">
          <span class="nodo" aria-hidden="true"><component :is="e.icono" :size="19" :stroke-width="2.2" /></span>
          <strong>{{ e.nombre }}</strong>
          <span class="que">{{ e.que }}</span>
        </li>
      </ol>
    </div>
    <button v-if="repetible" type="button" class="fantasma repetir" @click="vuelta++">
      <RotateCcw :size="14" aria-hidden="true" /> Ver de nuevo
    </button>
  </div>
</template>

<style scoped>
.viaje {
  --d: 3.6s;
  --c-raw: var(--aviso);
  --c-master: var(--sello);
  --c-gate: var(--marca);
  --c-business: var(--bien);
  --fondo-nodo: var(--superficie);
  --riel: var(--linea-fuerte);
  --apagado: var(--tenue);
  --texto: var(--tinta);
  --texto-2: var(--tinta-2);
  display: grid;
  gap: 8px;
  justify-items: center;
}
/* Sobre el panel azul del inicio de sesión. */
.viaje.oscuro {
  --c-raw: #fab219;
  --c-master: #ada2f7;
  --c-gate: #6cb2ff;
  --c-business: #53d153;
  --fondo-nodo: #18304f;
  --riel: rgb(255 255 255 / 0.16);
  --apagado: #8a9bb5;
  --texto: #ffffff;
  --texto-2: #b9c7dc;
}
.escena { position: relative; width: 100%; }

/* Riel entre el centro del primer nodo y el del último; el relleno avanza con el archivo. */
.riel, .carro { position: absolute; left: 12.5%; right: 12.5%; top: 21px; }
.riel { height: 3px; margin-top: -1.5px; border-radius: 2px; background: var(--riel); overflow: hidden; }
.relleno {
  position: absolute; inset: 0; border-radius: inherit;
  background: linear-gradient(90deg, var(--c-raw), var(--c-master) 33%, var(--c-gate) 66%, var(--c-business));
  animation: avanzar var(--d) var(--ease-in-out) var(--r) both;
}
.carro { height: 0; z-index: 1; animation: viajar var(--d) var(--ease-in-out) var(--r) both; }
.ficha {
  position: absolute; left: 0; top: 0; width: 26px; height: 26px; margin: -13px 0 0 -13px;
  display: grid; place-items: center; border-radius: 8px; border: 1.5px solid; box-shadow: 0 4px 10px -4px rgb(8 16 28 / 0.45);
}
.ficha.doc { background: var(--fondo-nodo); border-color: var(--apagado); color: var(--texto-2); animation: ver-doc var(--d) linear var(--r) both; }
.ficha.cifrada {
  background: color-mix(in srgb, var(--c-master) 22%, var(--fondo-nodo)); border-color: var(--c-master); color: var(--c-master);
  animation: ver-cifrada var(--d) linear var(--r) both;
}
.ficha.certificada {
  background: color-mix(in srgb, var(--c-business) 22%, var(--fondo-nodo)); border-color: var(--c-business); color: var(--c-business);
  animation: ver-certificada var(--d) linear var(--r) both;
}

.estaciones { position: relative; z-index: 2; list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; }
.estaciones li { display: grid; justify-items: center; align-content: start; gap: 2px; text-align: center; min-width: 0; }
.raw { --c: var(--c-raw); }
.master { --c: var(--c-master); }
.gate { --c: var(--c-gate); }
.business { --c: var(--c-business); }
.nodo {
  display: grid; place-items: center; width: 42px; height: 42px; margin-bottom: 4px; border-radius: 50%;
  border: 2px solid var(--riel); background: var(--fondo-nodo); color: var(--apagado);
  animation: encender 0.4s var(--ease-out) both;
  animation-delay: calc(var(--r) + var(--d) * var(--t));
}
.estaciones strong { font-size: 12.5px; font-weight: 800; color: var(--texto); letter-spacing: 0.01em; }
.que { font-size: 11.5px; line-height: 1.35; color: var(--texto-2); max-width: 15ch; }
.repetir { font-size: 12.5px; padding: 4px 10px; color: var(--texto-2); }
.oscuro .repetir:hover { background: rgb(255 255 255 / 0.08); color: #fff; }

/* Tramos: sale de RAW, se queda dentro de MASTER (sale cifrado), del Gate (sale certificado) y llega. */
@keyframes viajar {
  0%, 6% { transform: translateX(0); }
  28%, 40% { transform: translateX(33.333%); }
  62%, 74% { transform: translateX(66.667%); }
  94%, 100% { transform: translateX(100%); }
}
/* Recorte (no escala) para que el degradado no se comprima mientras avanza. */
@keyframes avanzar {
  0%, 6% { clip-path: inset(0 100% 0 0); }
  28%, 40% { clip-path: inset(0 66.667% 0 0); }
  62%, 74% { clip-path: inset(0 33.333% 0 0); }
  94%, 100% { clip-path: inset(0 0 0 0); }
}
@keyframes ver-doc { 0%, 33% { opacity: 1; } 34%, 100% { opacity: 0; } }
@keyframes ver-cifrada { 0%, 33% { opacity: 0; } 34%, 67% { opacity: 1; } 68%, 100% { opacity: 0; } }
@keyframes ver-certificada { 0%, 67% { opacity: 0; } 68%, 100% { opacity: 1; } }
@keyframes encender {
  0% { border-color: var(--riel); color: var(--apagado); transform: scale(1); }
  45% { transform: scale(1.12); }
  100% { border-color: var(--c); color: var(--c); background: color-mix(in srgb, var(--c) 18%, var(--fondo-nodo)); transform: scale(1); }
}
</style>
