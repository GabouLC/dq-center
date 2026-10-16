<script setup lang="ts">
import { computed } from 'vue'
import { corte, corteCorto, esFinDeSemana, NOMBRE_CERTIFICACION } from '@/formato'

/**
 * Mapa de certificación por día: una fila por tabla y un cuadro por corte, con el
 * color del sello. Clic en un cuadro para elegir ese día (y esa tabla).
 */
type Fila = { clave: string; nombre: string; color?: string; estados: Record<string, string | undefined>; detalle?: (dia: string) => string }
const props = defineProps<{ dias: string[]; filas: Fila[]; elegido?: string | null; seleccionada?: string | null }>()
const emit = defineEmits<{ elegir: [dia: string, clave: string]; seleccionar: [clave: string] }>()

const TONO: Record<string, string> = { CERTIFICADO: 'bien', CERTIFICADO_CON_OBSERVACIONES: 'aviso', NO_CERTIFICADO: 'critico' }
const meses = computed(() => props.dias.flatMap((d, i) => (d.endsWith('-01') || i === 0 ? [{ i, nombre: corteCorto(d) }] : [])))
const conteo = (f: Fila) =>
  props.dias.reduce((n, d) => ({ ...n, [f.estados[d] ?? 'SIN_DATOS']: (n[f.estados[d] ?? 'SIN_DATOS'] ?? 0) + 1 }), {} as Record<string, number>)
</script>

<template>
  <div class="mapa" :style="{ '--dias': dias.length }">
    <template v-for="f in filas" :key="f.clave">
      <button type="button" class="fantasma nombre" :class="{ seleccionada: f.clave === seleccionada }" @click="emit('seleccionar', f.clave)">
        <span v-if="f.color" class="clave" :style="{ background: f.color }" />{{ f.nombre }}
      </button>
      <div class="celdas">
        <button
          v-for="d in dias"
          :key="d"
          type="button"
          class="celda"
          :class="[TONO[f.estados[d] ?? ''], { actual: d === elegido, finde: esFinDeSemana(d) }]"
          :title="`${f.nombre} · ${corte(d)} · ${NOMBRE_CERTIFICACION[f.estados[d] ?? ''] ?? 'sin datos'}${f.detalle ? ` · ${f.detalle(d)}` : ''}`"
          :aria-label="`${f.nombre}, ${corte(d)}: ${NOMBRE_CERTIFICACION[f.estados[d] ?? ''] ?? 'sin datos'}`"
          @click="emit('elegir', d, f.clave)"
        />
      </div>
      <span class="resumen tenue" :title="`Días certificados, con observaciones y sin certificar`">
        <b class="t-bien">{{ conteo(f).CERTIFICADO ?? 0 }}</b> · <b class="t-aviso">{{ conteo(f).CERTIFICADO_CON_OBSERVACIONES ?? 0 }}</b> · <b class="t-critico">{{ conteo(f).NO_CERTIFICADO ?? 0 }}</b>
      </span>
    </template>
    <span />
    <div class="meses">
      <span v-for="m in meses" :key="m.i" :style="{ left: `calc(${m.i} / var(--dias) * 100%)` }">{{ m.nombre }}</span>
    </div>
    <span />
  </div>
</template>

<style scoped>
.mapa { display: grid; grid-template-columns: 112px minmax(0, 1fr) 84px; gap: 6px 10px; align-items: center; }
.nombre { border: 0; padding: 4px 8px; font-size: 13.5px; color: var(--tinta); gap: 8px; justify-content: flex-start; }
.nombre.seleccionada { background: var(--superficie-2); }
.clave { display: inline-block; width: 14px; height: 4px; border-radius: 2px; }
.celdas { display: grid; grid-template-columns: repeat(var(--dias), minmax(0, 1fr)); gap: 2px; }
.celda { height: 22px; padding: 0; min-width: 0; border-radius: 3px; border: 0; background: var(--superficie-3); }
.celda.bien { background: var(--bien); }
.celda.aviso { background: color-mix(in srgb, var(--aviso) 70%, var(--superficie)); }
.celda.critico { background: var(--critico); }
.celda.finde { opacity: 0.78; }
.celda:hover { transform: scaleY(1.15); outline: 2px solid var(--tinta-2); outline-offset: 1px; }
.celda.actual { outline: 2px solid var(--marca); outline-offset: 1px; }
.resumen { font-size: 12px; white-space: nowrap; }
.t-bien { color: var(--bien-texto); }
.t-aviso { color: var(--aviso-texto); }
.t-critico { color: var(--critico-texto); }
.meses { position: relative; height: 14px; }
.meses span { position: absolute; font-size: 11px; font-weight: 700; color: var(--tenue); }
@media (max-width: 760px) {
  .mapa { grid-template-columns: 1fr; }
  .celdas { gap: 1px; }
  .celda { height: 16px; border-radius: 1px; }
  .resumen { display: none; }
}
</style>
