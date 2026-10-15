<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { corte, pct } from '@/formato'

type Serie = { nombre: string; valores: (number | null)[]; destacada?: boolean }
const props = defineProps<{ etiquetas: string[]; series: Serie[] }>()

// El ancho del SVG sigue al contenedor: el texto queda siempre en 11-12 px.
const contenedor = ref<HTMLDivElement | null>(null)
const ancho = ref(720)
let observador: ResizeObserver | null = null
onMounted(() => {
  observador = new ResizeObserver(([e]) => (ancho.value = Math.max(280, Math.round(e.contentRect.width))))
  if (contenedor.value) observador.observe(contenedor.value)
})
onBeforeUnmount(() => observador?.disconnect())

const angosto = computed(() => ancho.value < 560)
const ALTO = 260
const M = computed(() => ({ arriba: 14, derecha: angosto.value ? 72 : 110, abajo: 26, izquierda: 36 }))
// Paleta categórica corta; la serie destacada (Global) usa el acento.
const COLORES = ['#2f6fb5', '#b5562f', '#7a52b3', '#2f9a8f', '#a3842a']

// Eje con pasos redondos (1, 2, 5, 10…) que termina en 100.
const escala = computed(() => {
  const valores = props.series.flatMap((s) => s.valores).filter((v): v is number => v !== null)
  const menor = valores.length ? Math.min(...valores) : 0
  const rango = Math.max(1, 100 - menor)
  const paso = [1, 2, 5, 10, 20, 25].find((p) => rango / p <= 5) ?? 25
  const minimo = Math.max(0, Math.floor(menor / paso) * paso)
  const ticks: number[] = []
  for (let t = minimo; t <= 100; t += paso) ticks.push(t)
  return { minimo, ticks }
})
const x = (i: number) => M.value.izquierda + (i * (ancho.value - M.value.izquierda - M.value.derecha)) / Math.max(1, props.etiquetas.length - 1)
const y = (v: number) => M.value.arriba + ((100 - v) / (100 - escala.value.minimo)) * (ALTO - M.value.arriba - M.value.abajo)

function camino(valores: (number | null)[]): string {
  return valores
    .map((v, i) => (v === null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`))
    .filter(Boolean)
    .map((p, i) => `${i ? 'L' : 'M'}${p}`)
    .join(' ')
}
const color = (s: Serie, i: number) => (s.destacada ? 'var(--accent)' : COLORES[i % COLORES.length])
const etiqueta = (iso: string) => (angosto.value ? corte(iso).split(' ')[0] : corte(iso))
const foco = ref<number | null>(null)

// Etiquetas al final de cada línea, separadas al menos 14 px para que no se encimen.
const leyendas = computed(() => {
  const SEPARACION = 14
  const items = props.series
    .map((s, i) => ({ nombre: s.nombre, color: color(s, i), destacada: s.destacada, y: y(s.valores.at(-1) ?? escala.value.minimo) + 4 }))
    .sort((a, b) => a.y - b.y)
  for (let k = 1; k < items.length; k++) items[k].y = Math.max(items[k].y, items[k - 1].y + SEPARACION)
  const exceso = (items.at(-1)?.y ?? 0) - (ALTO - M.value.abajo)
  if (exceso > 0) items.forEach((it) => (it.y -= exceso))
  return items
})
</script>

<template>
  <div ref="contenedor" class="contenedor">
    <svg :width="ancho" :height="ALTO" :viewBox="`0 0 ${ancho} ${ALTO}`" role="img" aria-label="Tendencia del score por fecha de corte">
      <g v-for="t in escala.ticks" :key="t">
        <line :x1="M.izquierda" :x2="ancho - M.derecha" :y1="y(t)" :y2="y(t)" class="guia" />
        <text :x="M.izquierda - 6" :y="y(t) + 4" text-anchor="end" class="eje">{{ t }}</text>
      </g>
      <text v-for="(e, i) in etiquetas" :key="e" :x="x(i)" :y="ALTO - 6" text-anchor="middle" class="eje">{{ etiqueta(e) }}</text>
      <line v-if="foco !== null" :x1="x(foco)" :x2="x(foco)" :y1="M.arriba" :y2="ALTO - M.abajo" class="foco" />
      <g v-for="(s, i) in series" :key="s.nombre">
        <path :d="camino(s.valores)" fill="none" :stroke="color(s, i)" :stroke-width="s.destacada ? 3 : 1.6" stroke-linejoin="round" />
        <template v-for="(v, j) in s.valores" :key="j">
          <circle v-if="v !== null" :cx="x(j)" :cy="y(v)" :r="s.destacada ? 4 : 2.6" :fill="color(s, i)">
            <title>{{ s.nombre }} · {{ corte(etiquetas[j]) }}: {{ pct(v) }}</title>
          </circle>
        </template>
      </g>
      <text
        v-for="l in leyendas"
        :key="`leyenda-${l.nombre}`"
        :x="ancho - M.derecha + 8"
        :y="l.y"
        class="leyenda"
        :fill="l.color"
        :font-weight="l.destacada ? 700 : 500"
      >{{ l.nombre }}</text>
      <rect
        v-for="(e, i) in etiquetas"
        :key="`zona-${e}`"
        :x="x(i) - 18"
        :y="M.arriba"
        width="36"
        :height="ALTO - M.arriba - M.abajo"
        fill="transparent"
        @mouseenter="foco = i"
        @mouseleave="foco = null"
      />
    </svg>
  </div>
</template>

<style scoped>
.contenedor { width: 100%; overflow: hidden; }
svg { display: block; }
.guia { stroke: var(--line); stroke-width: 1; }
.foco { stroke: var(--muted); stroke-dasharray: 3 3; }
.eje { fill: var(--muted); font-size: 11px; }
.leyenda { font-size: 12px; }
</style>
