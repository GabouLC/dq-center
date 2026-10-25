<script setup lang="ts">
import { ChevronLeft, ChevronRight, CircleCheck, CircleX } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import { corte, corteCorto, corteMedio, esFinDeSemana, pct } from '@/formato'
import { useCortes, type Corte } from '@/stores/cortes'
import { useVivo } from '@/stores/vivo'

/**
 * Línea de tiempo de los cortes diarios. Cada día es una barra: su altura sigue el
 * puntaje, el rojo marca días con alguna tabla no certificada y el fin de semana va
 * más claro. Se elige con clic, con las flechas del teclado o con los botones.
 */
const cortes = useCortes()
const vivo = useVivo()
onMounted(() => cortes.cargar())

const indice = computed(() => cortes.lista.findIndex((c) => c.fecha_corte === cortes.elegido))
const actual = computed(() => cortes.lista[indice.value])
const escala = computed(() => {
  const valores = cortes.lista.map((c) => c.global).filter((v): v is number => v !== null)
  const menor = Math.min(...valores, 99)
  return { menor: Math.floor(menor - 0.5), mayor: 100 }
})
const altura = (c: Corte) =>
  c.global === null ? 20 : 22 + ((c.global - escala.value.menor) / (escala.value.mayor - escala.value.menor)) * 78
const meses = computed(() =>
  cortes.lista.flatMap((c, i) => (c.fecha_corte.endsWith('-01') || i === 0 ? [{ i, nombre: corteCorto(c.fecha_corte).split(' ')[1] }] : [])),
)

const noCertificadas = (n: number) => `${n} no ${n === 1 ? 'certificada' : 'certificadas'}`
const valorTexto = computed(() =>
  actual.value
    ? `${corte(actual.value.fecha_corte)} · puntaje ${pct(actual.value.global)}${actual.value.no_certificadas ? ` · ${noCertificadas(actual.value.no_certificadas)}` : ''}`
    : '',
)

function mover(paso: number) {
  const i = Math.min(cortes.lista.length - 1, Math.max(0, indice.value + paso))
  if (cortes.lista[i]) cortes.elegido = cortes.lista[i].fecha_corte
}
function teclado(e: KeyboardEvent) {
  const pasos: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, PageUp: -7, PageDown: 7, Home: -999, End: 999 }
  if (!(e.key in pasos)) return
  e.preventDefault()
  mover(pasos[e.key])
}
</script>

<template>
  <div class="linea">
    <button type="button" class="icono fantasma" aria-label="Día anterior" :disabled="indice <= 0" @click="mover(-1)">
      <ChevronLeft :size="17" />
    </button>
    <div
      class="franja"
      role="slider"
      tabindex="0"
      aria-label="Día de datos"
      :aria-valuemin="0"
      :aria-valuemax="cortes.lista.length - 1"
      :aria-valuenow="indice"
      :aria-valuetext="valorTexto"
      @keydown="teclado"
    >
      <div class="barras">
        <span
          v-for="c in cortes.lista"
          :key="c.fecha_corte"
          class="dia"
          :class="{ critico: c.no_certificadas > 0, finde: esFinDeSemana(c.fecha_corte), activo: c.fecha_corte === cortes.elegido }"
          :style="{ height: `${altura(c)}%` }"
          :title="`${corte(c.fecha_corte)} · puntaje ${pct(c.global)}${c.no_certificadas ? ` · ${noCertificadas(c.no_certificadas)}` : ''}`"
          @click="cortes.elegido = c.fecha_corte"
        />
        <span v-if="vivo.estado?.corte_en_curso" class="dia llegando" title="Día que está llegando ahora" />
      </div>
      <div class="meses" aria-hidden="true">
        <span v-for="m in meses" :key="m.i" :style="{ left: `calc(${m.i} * var(--paso))` }">{{ m.nombre }}</span>
      </div>
    </div>
    <button type="button" class="icono fantasma" aria-label="Día siguiente" :disabled="indice >= cortes.lista.length - 1" @click="mover(1)">
      <ChevronRight :size="17" />
    </button>
    <div v-if="actual" class="elegido">
      <strong>{{ corteMedio(actual.fecha_corte) }}</strong>
      <span class="detalle">
        <CircleX v-if="actual.no_certificadas" :size="13" class="critico" />
        <CircleCheck v-else :size="13" class="bien" />
        puntaje {{ pct(actual.global) }}<template v-if="actual.no_certificadas"> · {{ noCertificadas(actual.no_certificadas) }}</template>
      </span>
    </div>
  </div>
</template>

<style scoped>
.linea { --paso: 5px; display: flex; align-items: center; gap: 6px; min-width: 0; }
.franja { position: relative; padding: 4px 6px 14px; border-radius: 10px; background: var(--superficie-2); cursor: pointer; min-width: 0; overflow: hidden; }
.franja:focus-visible { outline: 2px solid var(--marca); outline-offset: 2px; }
.barras { display: flex; align-items: flex-end; gap: 1px; height: 30px; }
.dia { width: 4px; flex: none; border-radius: 2px 2px 1px 1px; background: color-mix(in srgb, var(--marca) 55%, var(--superficie-2)); transition: height 0.4s ease, background 0.15s; }
.dia.finde { background: color-mix(in srgb, var(--marca) 28%, var(--superficie-2)); }
.dia.critico { background: var(--critico); }
.dia:hover { background: var(--marca); }
.dia.activo { background: var(--tinta); box-shadow: 0 0 0 1.5px var(--superficie-2), 0 0 0 3px var(--marca); }
.dia.llegando { height: 60%; background: var(--bien); animation: latido 1.2s ease-in-out infinite; }
@keyframes latido { 50% { opacity: 0.25; } }
.meses { position: absolute; left: 6px; right: 6px; bottom: 1px; height: 12px; }
.meses span { position: absolute; font-size: 10px; font-weight: 700; color: var(--tenue); text-transform: capitalize; }
.elegido { display: grid; line-height: 1.2; flex-shrink: 0; margin-left: 4px; }
.elegido strong { font-size: 13.5px; white-space: nowrap; text-transform: capitalize; }
.detalle { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; color: var(--tenue); font-weight: 600; white-space: nowrap; }
.bien { color: var(--bien); }
.critico { color: var(--critico); }
/* En pantallas medianas la franja se angosta para que el día elegido se lea completo. */
@media (max-width: 1500px) { .linea { --paso: 4px; } .dia { width: 3px; } }
@media (max-width: 1180px) { .franja { display: none; } }
</style>
