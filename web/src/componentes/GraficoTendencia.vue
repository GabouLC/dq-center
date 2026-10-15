<script setup lang="ts">
import { Table2, TrendingUp } from 'lucide-vue-next'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { corte, pct } from '@/formato'

/**
 * Tendencia por corte (dataviz): líneas de 2 px, una sola escala, crosshair que se
 * ajusta al corte más cercano con un tooltip de todas las series, leyenda que
 * activa/desactiva series (el color sigue a la serie), etiquetas directas al final
 * y vista de tabla como alternativa accesible.
 */
type Serie = { clave: string; nombre: string; color: string; valores: (number | null)[]; destacada?: boolean }
const props = defineProps<{ etiquetas: string[]; series: Serie[]; elegido?: string | null }>()
const emit = defineEmits<{ elegir: [fecha: string] }>()

const contenedor = ref<HTMLDivElement | null>(null)
const ancho = ref(720)
let observador: ResizeObserver | null = null
onMounted(() => {
  // El contenedor no se dimensiona por el SVG (min-width: 0), así que su ancho es el disponible.
  if (contenedor.value) ancho.value = Math.max(280, contenedor.value.clientWidth)
  observador = new ResizeObserver(([e]) => (ancho.value = Math.max(280, Math.round(e.contentRect.width))))
  if (contenedor.value) observador.observe(contenedor.value)
})
onBeforeUnmount(() => observador?.disconnect())

const ocultas = ref(new Set<string>())
const vistaTabla = ref(false)
const visibles = computed(() => props.series.filter((s) => !ocultas.value.has(s.clave)))
function alternar(clave: string) {
  const nuevas = new Set(ocultas.value)
  if (nuevas.has(clave)) nuevas.delete(clave)
  else if (visibles.value.length > 1) nuevas.add(clave)
  ocultas.value = nuevas
}

const angosto = computed(() => ancho.value < 560)
const ALTO = 280
const M = computed(() => ({ arriba: 18, derecha: angosto.value ? 76 : 104, abajo: 30, izquierda: 38 }))

// Una sola escala, con pasos redondos que terminan en 100.
const escala = computed(() => {
  const valores = visibles.value.flatMap((s) => s.valores).filter((v): v is number => v !== null)
  const menor = valores.length ? Math.min(...valores) : 0
  const paso = [1, 2, 5, 10, 20, 25].find((p) => Math.max(1, 100 - menor) / p <= 5) ?? 25
  const minimo = Math.max(0, Math.floor(menor / paso) * paso)
  const ticks: number[] = []
  for (let t = minimo; t <= 100; t += paso) ticks.push(t)
  return { minimo, ticks }
})
const x = (i: number) => M.value.izquierda + (i * (ancho.value - M.value.izquierda - M.value.derecha)) / Math.max(1, props.etiquetas.length - 1)
const y = (v: number) => M.value.arriba + ((100 - v) / (100 - escala.value.minimo)) * (ALTO - M.value.arriba - M.value.abajo)
const camino = (valores: (number | null)[]) =>
  valores
    .map((v, i) => (v === null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`))
    .filter(Boolean)
    .map((p, i) => `${i ? 'L' : 'M'}${p}`)
    .join(' ')
const etiqueta = (iso: string) => (angosto.value ? corte(iso).split(' ')[0] : corte(iso))

// Etiquetas directas al final, separadas para que no se encimen.
const leyendas = computed(() => {
  const items = visibles.value
    .map((s) => ({ ...s, y: y(s.valores.at(-1) ?? escala.value.minimo) + 4 }))
    .sort((a, b) => a.y - b.y)
  for (let k = 1; k < items.length; k++) items[k].y = Math.max(items[k].y, items[k - 1].y + 14)
  const exceso = (items.at(-1)?.y ?? 0) - (ALTO - M.value.abajo)
  if (exceso > 0) items.forEach((it) => (it.y -= exceso))
  return items
})

// Crosshair: el puntero busca el corte más cercano; con teclado, flechas.
const foco = ref<number | null>(null)
function mover(evento: PointerEvent) {
  const caja = (evento.currentTarget as SVGElement).getBoundingClientRect()
  const px = evento.clientX - caja.left
  const paso = (ancho.value - M.value.izquierda - M.value.derecha) / Math.max(1, props.etiquetas.length - 1)
  foco.value = Math.max(0, Math.min(props.etiquetas.length - 1, Math.round((px - M.value.izquierda) / paso)))
}
function teclado(evento: KeyboardEvent) {
  const actual = foco.value ?? props.etiquetas.length - 1
  if (evento.key === 'ArrowLeft') foco.value = Math.max(0, actual - 1)
  else if (evento.key === 'ArrowRight') foco.value = Math.min(props.etiquetas.length - 1, actual + 1)
  else if (evento.key === 'Enter' && foco.value !== null) emit('elegir', props.etiquetas[foco.value])
  else return
  evento.preventDefault()
}
const tooltip = computed(() => {
  if (foco.value === null) return null
  const i = foco.value
  const filas = visibles.value
    .map((s) => ({ nombre: s.nombre, color: s.color, valor: s.valores[i] }))
    .sort((a, b) => (b.valor ?? 0) - (a.valor ?? 0))
  const izquierda = x(i) > ancho.value / 2
  return { i, filas, estilo: { top: '12px', [izquierda ? 'right' : 'left']: `${izquierda ? ancho.value - x(i) + 14 : x(i) + 14}px` } }
})
</script>

<template>
  <div class="grafico">
    <div class="fila entre controles">
      <div class="fila leyenda" role="group" aria-label="Series">
        <button
          v-for="s in series"
          :key="s.clave"
          type="button"
          class="serie"
          :class="{ apagada: ocultas.has(s.clave) }"
          :aria-pressed="!ocultas.has(s.clave)"
          @click="alternar(s.clave)"
        >
          <span class="clave" :style="{ background: s.color, height: s.destacada ? '4px' : '3px' }" />
          {{ s.nombre }}
        </button>
      </div>
      <button type="button" class="fantasma" @click="vistaTabla = !vistaTabla">
        <component :is="vistaTabla ? TrendingUp : Table2" :size="15" />
        {{ vistaTabla ? 'Ver gráfico' : 'Ver tabla' }}
      </button>
    </div>

    <div v-show="!vistaTabla" ref="contenedor" class="lienzo">
      <svg
        :width="ancho"
        :height="ALTO"
        :viewBox="`0 0 ${ancho} ${ALTO}`"
        role="img"
        aria-label="Tendencia del score por fecha de corte. Usa las flechas para recorrer los cortes y Enter para elegir uno."
        tabindex="0"
        @pointermove="mover"
        @pointerleave="foco = null"
        @click="foco !== null && emit('elegir', etiquetas[foco])"
        @keydown="teclado"
        @blur="foco = null"
      >
        <g v-for="t in escala.ticks" :key="t">
          <line :x1="M.izquierda" :x2="ancho - M.derecha" :y1="y(t)" :y2="y(t)" class="guia" />
          <text :x="M.izquierda - 8" :y="y(t) + 4" text-anchor="end" class="eje num">{{ t }}</text>
        </g>
        <template v-for="(e, i) in etiquetas" :key="e">
          <rect
            v-if="e === elegido"
            :x="x(i) - 22"
            :y="M.arriba - 6"
            width="44"
            :height="ALTO - M.arriba - M.abajo + 6"
            rx="8"
            class="elegido"
          />
          <text :x="x(i)" :y="ALTO - 8" text-anchor="middle" class="eje" :class="{ fuerte: e === elegido }">{{ etiqueta(e) }}</text>
        </template>
        <line v-if="foco !== null" :x1="x(foco)" :x2="x(foco)" :y1="M.arriba" :y2="ALTO - M.abajo" class="cruz" />
        <g v-for="s in visibles" :key="s.clave">
          <path :d="camino(s.valores)" fill="none" :stroke="s.color" :stroke-width="s.destacada ? 3.2 : 2" stroke-linejoin="round" stroke-linecap="round" />
          <template v-for="(v, j) in s.valores" :key="j">
            <circle
              v-if="v !== null"
              :cx="x(j)"
              :cy="y(v)"
              :r="foco === j ? (s.destacada ? 6 : 5) : s.destacada ? 4.5 : 3.2"
              :fill="s.color"
              stroke="var(--superficie)"
              stroke-width="2"
            />
          </template>
        </g>
        <text
          v-for="l in leyendas"
          :key="`l-${l.clave}`"
          :x="ancho - M.derecha + 10"
          :y="l.y"
          class="directa"
          :font-weight="l.destacada ? 800 : 600"
        >{{ l.nombre }}</text>
      </svg>
      <div v-if="tooltip" class="tooltip" :style="tooltip.estilo" role="status">
        <div class="t-titulo">{{ corte(etiquetas[tooltip.i]) }}</div>
        <div v-for="f in tooltip.filas" :key="f.nombre" class="t-fila">
          <span class="t-clave" :style="{ background: f.color }" />
          <span class="secundario">{{ f.nombre }}</span>
          <strong>{{ pct(f.valor) }}</strong>
        </div>
        <div class="t-pie tenue">Clic para ver este corte</div>
      </div>
    </div>

    <div v-if="vistaTabla" class="tabla-envoltura">
      <table>
        <thead>
          <tr><th>Serie</th><th v-for="e in etiquetas" :key="e" class="der">{{ corte(e) }}</th></tr>
        </thead>
        <tbody>
          <tr v-for="s in series" :key="s.clave">
            <td><span class="clave" :style="{ background: s.color }" /> {{ s.nombre }}</td>
            <td v-for="(v, i) in s.valores" :key="i" class="der num">{{ pct(v) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.grafico { display: grid; gap: 10px; min-width: 0; }
.leyenda { gap: 6px; }
.serie { padding: 4px 11px; font-size: 12.5px; gap: 7px; }
.serie.apagada { opacity: 0.45; text-decoration: line-through; }
.clave { display: inline-block; width: 16px; border-radius: 2px; vertical-align: middle; height: 3px; }
.lienzo { position: relative; width: 100%; min-width: 0; overflow: hidden; }
svg { display: block; max-width: 100%; cursor: crosshair; outline-offset: 4px; border-radius: 8px; }
.guia { stroke: var(--linea); stroke-width: 1; }
.cruz { stroke: var(--tinta-2); stroke-width: 1; }
.elegido { fill: var(--marca-suave); }
.eje { fill: var(--tenue); font-size: 11.5px; font-weight: 600; }
.eje.fuerte { fill: var(--marca); font-weight: 800; }
.directa { fill: var(--tinta-2); font-size: 12px; }
.t-pie { margin-top: 6px; font-size: 11.5px; }
</style>
