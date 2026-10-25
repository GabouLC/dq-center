<script setup lang="ts">
import { ArrowLeft, ArrowRight, X } from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ViajeDatos from '@/componentes/ViajeDatos.vue'
import { corteCorto } from '@/formato'
import { useCortes } from '@/stores/cortes'
import { useRecorrido } from '@/stores/recorrido'
import { useSesion } from '@/stores/sesion'

/**
 * Recorrido guiado (primera visita): ilumina, en el Resumen, la línea de días, la lectura
 * rápida, los sellos y el menú, y cierra con cómo viajan los datos. Es un diálogo modal:
 * el foco queda dentro, Esc lo cierra, las flechas cambian de paso y, al cerrar, el foco
 * vuelve a donde estaba.
 */
const recorrido = useRecorrido()
const sesion = useSesion()
const cortes = useCortes()
const ruta = useRoute()
const router = useRouter()

type Paso = { titulo: string; texto: string; objetivo?: string[]; viaje?: boolean }

const angosto = () => window.matchMedia('(max-width: 1180px)').matches
const movil = () => window.matchMedia('(max-width: 960px)').matches
const periodo = computed(() => {
  const primero = cortes.lista[0]?.fecha_corte
  const ultimo = cortes.lista.at(-1)?.fecha_corte
  return primero && ultimo ? `del ${corteCorto(primero)} al ${corteCorto(ultimo)}` : 'de cada día'
})
const conAdmin = computed(() => sesion.modulos.some((m) => ['reglas', 'ejecuciones', 'usuarios', 'auditoria'].includes(m.clave)))

const pasos = computed<Paso[]>(() => [
  {
    titulo: 'Elige el día',
    objetivo: ['[data-recorrido="linea"]'],
    texto: angosto()
      ? `Aquí eliges el día de datos (${periodo.value}). Usa las flechas para ir al día anterior o al siguiente.`
      : `Aquí eliges el día de datos (${periodo.value}). Cada barra es un día: más alta, mejor puntaje; en rojo, los días con alguna tabla no certificada. Cambia de día con un clic o con las flechas del teclado.`,
  },
  {
    titulo: 'Empieza por la lectura rápida',
    objetivo: ['[data-recorrido="lectura"]'],
    texto: 'En una frase: cuántas tablas llegaron a negocio ese día, cuál se retuvo y por qué, y qué cambió frente al día anterior.',
  },
  {
    titulo: 'Un sello por tabla',
    objetivo: ['[data-recorrido="sellos"]'],
    texto: 'Cada sello dice si la tabla quedó Certificada, Con observaciones o No certificada. Las dos primeras llegan a negocio; la última se retiene. Más abajo, el mapa muestra el sello de cada tabla en todos los días.',
  },
  {
    titulo: 'El menú, por objetivo',
    objetivo: ['[data-recorrido="menu"]', '[data-recorrido="menu-movil"]'],
    texto:
      `${movil() ? 'Abre el menú con este botón. ' : ''}Está ordenado por lo que quieres hacer: Calidad del día, para revisar un día; Origen y gobierno, para saber de dónde vienen los datos` +
      `${conAdmin.value ? '; y Administración, para reglas, ejecuciones y usuarios' : ''}. ` +
      `En cada página, «¿Cómo se lee?» explica sus colores y marcas.`,
  },
  {
    titulo: 'Cómo viajan los datos',
    viaje: true,
    texto: 'Cada día llega un archivo por tabla. En MASTER se ordena y se cifran los datos personales; el Gate revisa calidad y privacidad, y solo lo certificado llega a negocio.',
  },
])

const indice = ref(0)
const paso = computed(() => pasos.value[indice.value])
const ultimo = computed(() => indice.value === pasos.value.length - 1)

// Posición del foco (hueco iluminado) y de la tarjeta.
type Caja = { top: number; left: number; width: number; height: number }
const foco = ref<Caja | null>(null)
const lugar = ref({ x: 0, y: 0 })
const ubicada = ref(false)
const tarjeta = ref<HTMLElement | null>(null)
const principal = ref<HTMLButtonElement | null>(null)
let objetivo: HTMLElement | null = null
let abridor: HTMLElement | null = null
let turno = 0

function visible(el: HTMLElement): boolean {
  const r = el.getBoundingClientRect()
  return r.width > 0 && r.height > 0 && r.right > 0 && r.left < window.innerWidth && getComputedStyle(el).visibility !== 'hidden'
}
/** Espera (hasta ~3 s) a que aparezca en pantalla alguno de los selectores del paso. */
async function buscar(selectores: string[], miTurno: number): Promise<HTMLElement | null> {
  for (let intento = 0; intento < 30; intento++) {
    if (miTurno !== turno) return null
    for (const s of selectores) {
      const el = document.querySelector<HTMLElement>(s)
      if (el && visible(el)) return el
    }
    await new Promise((r) => setTimeout(r, 100))
  }
  return null
}

function medir(): void {
  if (!objetivo || !objetivo.isConnected) {
    foco.value = null
  } else {
    const r = objetivo.getBoundingClientRect()
    const m = 8
    foco.value = { top: r.top - m, left: r.left - m, width: r.width + m * 2, height: r.height + m * 2 }
  }
  ubicar()
}
function ubicar(): void {
  const t = tarjeta.value
  if (!t) return
  const W = window.innerWidth
  const H = window.innerHeight
  const m = 12
  const ancho = t.offsetWidth
  const alto = t.offsetHeight
  const enX = (x: number) => Math.min(Math.max(m, x), W - ancho - m)
  const enY = (y: number) => Math.min(Math.max(m, y), H - alto - m)
  const f = foco.value
  if (!f) {
    lugar.value = { x: (W - ancho) / 2, y: enY((H - alto) / 2) }
  } else if (f.height > H * 0.4 && f.left + f.width + 16 + ancho <= W - m) {
    lugar.value = { x: f.left + f.width + 16, y: enY(f.top + f.height / 2 - alto / 2) } // a la derecha (menú)
  } else if (f.top + f.height + 14 + alto <= H - m) {
    lugar.value = { x: enX(f.left), y: f.top + f.height + 14 } // debajo
  } else if (f.top - 14 - alto >= m) {
    lugar.value = { x: enX(f.left), y: f.top - 14 - alto } // encima
  } else {
    lugar.value = { x: (W - ancho) / 2, y: H - alto - m } // abajo, centrada
  }
}

async function mostrar(): Promise<void> {
  const miTurno = ++turno
  objetivo = paso.value.objetivo ? await buscar(paso.value.objetivo, miTurno) : null
  if (miTurno !== turno) return
  // Lo iluminado debe quedar a la vista (los de la barra superior y el menú siempre lo están).
  if (objetivo && !objetivo.closest('.barra-superior, .lateral')) {
    const r = objetivo.getBoundingClientRect()
    const arriba = window.innerWidth <= 960 ? 120 : 84
    if (r.top < arriba || r.bottom + 260 > window.innerHeight) window.scrollBy({ top: r.top - arriba, behavior: 'auto' })
  }
  await nextTick()
  medir()
  if (!ubicada.value) {
    // Primera ubicación: se fija sin animar desde la esquina y recién entonces se muestra.
    await nextTick()
    tarjeta.value?.getBoundingClientRect()
    ubicada.value = true
  }
}

function ir(i: number): void {
  if (i < 0 || i >= pasos.value.length) return
  indice.value = i
  void mostrar()
}
const siguiente = () => (ultimo.value ? recorrido.cerrar() : ir(indice.value + 1))
const anterior = () => ir(indice.value - 1)

function teclado(e: KeyboardEvent): void {
  if (e.key === 'Escape') {
    e.preventDefault()
    recorrido.cerrar()
  } else if (e.key === 'ArrowRight') {
    e.preventDefault()
    siguiente()
  } else if (e.key === 'ArrowLeft') {
    e.preventDefault()
    anterior()
  } else if (e.key === 'Tab' && tarjeta.value) {
    const enfocables = [...tarjeta.value.querySelectorAll<HTMLElement>('button:not([disabled]), a[href]')]
    if (!enfocables.length) return
    const primero = enfocables[0]
    const final = enfocables[enfocables.length - 1]
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault()
      final.focus()
    } else if (!e.shiftKey && document.activeElement === final) {
      e.preventDefault()
      primero.focus()
    } else if (!tarjeta.value.contains(document.activeElement)) {
      e.preventDefault()
      primero.focus()
    }
  }
}

// Al desplazar o cambiar el tamaño de la ventana, el foco sigue a su objetivo sin animación.
let cuadro = 0
let reposo = 0
const siguiendo = ref(false)
const alMover = () => {
  siguiendo.value = true
  clearTimeout(reposo)
  reposo = window.setTimeout(() => (siguiendo.value = false), 160)
  cancelAnimationFrame(cuadro)
  cuadro = requestAnimationFrame(medir)
}

watch(
  () => recorrido.abierto,
  async (abierto) => {
    if (abierto) {
      abridor = document.activeElement instanceof HTMLElement && document.activeElement !== document.body ? document.activeElement : null
      ubicada.value = false
      indice.value = 0
      if (ruta.path !== '/resumen') await router.push('/resumen')
      window.scrollTo({ top: 0, behavior: 'auto' })
      window.addEventListener('resize', alMover)
      window.addEventListener('scroll', alMover, { passive: true })
      window.addEventListener('keydown', teclado)
      await mostrar()
      principal.value?.focus()
    } else {
      turno++
      window.removeEventListener('resize', alMover)
      window.removeEventListener('scroll', alMover)
      window.removeEventListener('keydown', teclado)
      objetivo = null
      const destino = abridor?.isConnected ? abridor : document.getElementById('boton-recorrido')
      destino?.focus()
    }
  },
)
onBeforeUnmount(() => {
  window.removeEventListener('resize', alMover)
  window.removeEventListener('scroll', alMover)
  window.removeEventListener('keydown', teclado)
  cancelAnimationFrame(cuadro)
  clearTimeout(reposo)
})
</script>

<template>
  <Teleport to="body">
    <Transition name="recorrido">
      <div v-if="recorrido.abierto" class="recorrido" :class="{ siguiendo }">
        <div class="bloqueo" aria-hidden="true" @mousedown.prevent />
        <div
          class="hueco"
          :class="{ sin: !foco, listo: ubicada }"
          :style="foco ? { top: `${foco.top}px`, left: `${foco.left}px`, width: `${foco.width}px`, height: `${foco.height}px` } : undefined"
          aria-hidden="true"
        />
        <section
          ref="tarjeta"
          class="tarjeta"
          :class="{ ancha: paso.viaje, listo: ubicada }"
          :style="{ transform: `translate(${lugar.x}px, ${lugar.y}px)` }"
          role="dialog"
          aria-modal="true"
          tabindex="-1"
          aria-labelledby="recorrido-titulo"
          aria-describedby="recorrido-texto"
        >
          <div class="cabecera-paso">
            <ol class="progreso" aria-hidden="true">
              <li v-for="(p, i) in pasos" :key="p.titulo" :class="{ hecho: i < indice, actual: i === indice }" />
            </ol>
            <span class="numero">Paso {{ indice + 1 }} de {{ pasos.length }}</span>
            <button type="button" class="icono fantasma cerrar" aria-label="Cerrar el recorrido" @click="recorrido.cerrar()"><X :size="17" /></button>
          </div>
          <div class="cuerpo" aria-live="polite">
            <h2 id="recorrido-titulo">{{ paso.titulo }}</h2>
            <p id="recorrido-texto">{{ paso.texto }}</p>
          </div>
          <ViajeDatos v-if="paso.viaje" repetible class="viaje" />
          <p v-if="ultimo" class="nota">Puedes volver a ver este recorrido con el botón <strong>?</strong> de la barra superior.</p>
          <div class="botones">
            <button v-if="!ultimo" type="button" class="fantasma saltar" aria-label="Saltar recorrido" @click="recorrido.cerrar()">
              <span class="largo" aria-hidden="true">Saltar recorrido</span><span class="corto" aria-hidden="true">Saltar</span>
            </button>
            <span class="espacio" />
            <button v-if="indice > 0" type="button" @click="anterior"><ArrowLeft :size="15" aria-hidden="true" /> Anterior</button>
            <button ref="principal" type="button" class="primario" @click="siguiente">
              {{ ultimo ? 'Empezar' : 'Siguiente' }}<ArrowRight v-if="!ultimo" :size="15" aria-hidden="true" />
            </button>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.recorrido { position: fixed; inset: 0; z-index: 90; }
.bloqueo { position: fixed; inset: 0; }
/* El hueco iluminado: su sombra enorme oscurece todo lo demás. */
.hueco {
  position: fixed; border-radius: 14px; pointer-events: none;
  box-shadow: 0 0 0 2px var(--nav-acento), 0 0 0 9999px rgb(8 16 28 / 0.58);
}
.hueco.sin { top: 50%; left: 50%; width: 0; height: 0; box-shadow: 0 0 0 9999px rgb(8 16 28 / 0.58); }
.hueco.listo { transition: top 0.28s var(--ease-in-out), left 0.28s var(--ease-in-out), width 0.28s var(--ease-in-out), height 0.28s var(--ease-in-out); }

.tarjeta {
  position: fixed; top: 0; left: 0; width: min(400px, calc(100vw - 24px)); display: grid; gap: 12px;
  padding: 16px 18px 16px; border-radius: 16px; background: var(--superficie); border: 1px solid var(--linea);
  box-shadow: 0 24px 60px -20px rgb(8 16 28 / 0.55); visibility: hidden;
}
.tarjeta.listo { visibility: visible; transition: transform 0.28s var(--ease-in-out); animation: asomar 0.24s var(--ease-out); }
.siguiendo :is(.hueco, .tarjeta) { transition: none; }
.tarjeta.ancha { width: min(540px, calc(100vw - 24px)); }
.tarjeta:focus { outline: none; }
.cabecera-paso { display: flex; align-items: center; gap: 10px; }
.progreso { display: flex; gap: 4px; list-style: none; margin: 0; padding: 0; }
.progreso li { width: 16px; height: 4px; border-radius: 2px; background: var(--superficie-3); transition: background-color 0.2s ease, width 0.2s var(--ease-out); }
.progreso li.hecho { background: color-mix(in srgb, var(--marca) 45%, var(--superficie-3)); }
.progreso li.actual { width: 26px; background: var(--marca); }
.numero { font-size: 12px; font-weight: 700; color: var(--tenue); }
.cerrar { margin-left: auto; margin-right: -6px; }
.cuerpo { display: grid; gap: 6px; }
h2 { font-size: 18px; font-weight: 800; letter-spacing: -0.015em; }
.cuerpo p { font-size: 14px; color: var(--tinta-2); line-height: 1.55; }
.viaje { padding: 14px 6px 6px; border-radius: 12px; background: var(--superficie-2); }
.nota { font-size: 12.5px; color: var(--tenue); }
.botones { display: flex; align-items: center; gap: 8px; margin-top: 2px; }
.espacio { flex: 1; }
.saltar { color: var(--tinta-2); padding-left: 8px; padding-right: 8px; white-space: nowrap; }
.saltar .corto { display: none; }
@media (max-width: 440px) {
  .saltar .largo { display: none; }
  .saltar .corto { display: inline; }
}

.recorrido-enter-active { transition: opacity 0.22s var(--ease-out); }
.recorrido-leave-active { transition: opacity 0.15s ease; }
.recorrido-enter-from, .recorrido-leave-to { opacity: 0; }
@keyframes asomar { from { opacity: 0; scale: 0.96; } }
</style>
