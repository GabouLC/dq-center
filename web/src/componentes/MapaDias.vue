<script setup lang="ts">
import { computed } from 'vue'
import { corte, corteCorto, esFinDeSemana, NOMBRE_CERTIFICACION } from '@/formato'

/**
 * Mapa de certificación por día: una fila por tabla y un cuadro por día, con el
 * color de su certificación. Clic en un cuadro para elegir ese día (y esa tabla).
 * Con teclado, cada fila es una sola parada de Tab y las flechas recorren los días.
 * El nombre de la tabla solo es un botón cuando la vista escucha `seleccionar`.
 */
type Fila = { clave: string; nombre: string; color?: string; estados: Record<string, string | undefined>; detalle?: (dia: string) => string }
const props = defineProps<{
  dias: string[]
  filas: Fila[]
  elegido?: string | null
  seleccionada?: string | null
  seleccionable?: boolean
}>()
const emit = defineEmits<{ elegir: [dia: string, clave: string]; seleccionar: [clave: string] }>()

const TONO: Record<string, string> = { CERTIFICADO: 'bien', CERTIFICADO_CON_OBSERVACIONES: 'aviso', NO_CERTIFICADO: 'critico' }
const meses = computed(() => props.dias.flatMap((d, i) => (d.endsWith('-01') || i === 0 ? [{ i, nombre: corteCorto(d) }] : [])))
const conteo = (f: Fila) =>
  props.dias.reduce((n, d) => ({ ...n, [f.estados[d] ?? 'SIN_DATOS']: (n[f.estados[d] ?? 'SIN_DATOS'] ?? 0) + 1 }), {} as Record<string, number>)

// Tabindex móvil: en cada fila, solo el día elegido (o el último) entra en el orden de Tab.
const diaConFoco = computed(() => (props.elegido && props.dias.includes(props.elegido) ? props.elegido : props.dias.at(-1)))
function flechas(evento: KeyboardEvent) {
  const paso = ({ ArrowLeft: -1, ArrowRight: 1 } as Record<string, number>)[evento.key]
  if (!paso) return
  evento.preventDefault()
  const actual = evento.target as HTMLElement
  const siguiente = (paso < 0 ? actual.previousElementSibling : actual.nextElementSibling) as HTMLElement | null
  siguiente?.focus()
}
</script>

<template>
  <div class="mapa-dias">
    <p class="leyenda-mapa">
      <span><i class="cuadro bien" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO }}</span>
      <span><i class="cuadro aviso" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO_CON_OBSERVACIONES }}</span>
      <span><i class="cuadro critico" /> {{ NOMBRE_CERTIFICACION.NO_CERTIFICADO }}</span>
    </p>
    <div class="mapa" :style="{ '--dias': dias.length }">
      <template v-for="f in filas" :key="f.clave">
        <button
          v-if="seleccionable"
          type="button"
          class="fantasma nombre"
          :class="{ seleccionada: f.clave === seleccionada }"
          :aria-pressed="f.clave === seleccionada"
          @click="emit('seleccionar', f.clave)"
        >
          <span v-if="f.color" class="clave" :style="{ background: f.color }" />{{ f.nombre }}
        </button>
        <span v-else class="nombre">
          <span v-if="f.color" class="clave" :style="{ background: f.color }" />{{ f.nombre }}
        </span>
        <div class="celdas" role="group" :aria-label="`${f.nombre}: certificación por día`" @keydown="flechas">
          <button
            v-for="d in dias"
            :key="d"
            type="button"
            class="celda"
            :class="[TONO[f.estados[d] ?? ''], { actual: d === elegido, finde: esFinDeSemana(d) }]"
            :tabindex="d === diaConFoco ? 0 : -1"
            :title="`${f.nombre} · ${corte(d)} · ${NOMBRE_CERTIFICACION[f.estados[d] ?? ''] ?? 'sin datos'}${f.detalle ? ` · ${f.detalle(d)}` : ''}`"
            :aria-label="`${f.nombre}, ${corte(d)}: ${NOMBRE_CERTIFICACION[f.estados[d] ?? ''] ?? 'sin datos'}`"
            @click="emit('elegir', d, f.clave)"
          />
        </div>
        <span class="resumen tenue" title="Días certificados, con observaciones y no certificados">
          <b class="t-bien">{{ conteo(f).CERTIFICADO ?? 0 }}</b> cert. · <b class="t-aviso">{{ conteo(f).CERTIFICADO_CON_OBSERVACIONES ?? 0 }}</b> obs. ·
          <b class="t-critico">{{ conteo(f).NO_CERTIFICADO ?? 0 }}</b> no cert.
        </span>
      </template>
      <span />
      <div class="meses" aria-hidden="true">
        <span v-for="m in meses" :key="m.i" :style="{ left: `calc(${m.i} / var(--dias) * 100%)` }">{{ m.nombre }}</span>
      </div>
      <span />
    </div>
  </div>
</template>

<style scoped>
.mapa-dias { display: grid; gap: 10px; }
.leyenda-mapa { display: flex; justify-content: flex-end; align-items: center; gap: 4px 14px; font-size: 12.5px; color: var(--tinta-2); flex-wrap: wrap; }
.leyenda-mapa span { display: inline-flex; align-items: center; gap: 6px; }
.cuadro { width: 11px; height: 11px; border-radius: 3px; display: inline-block; background: var(--superficie-3); }
.mapa { display: grid; grid-template-columns: 112px minmax(0, 1fr) max-content; gap: 6px 10px; align-items: center; }
.nombre { display: inline-flex; align-items: center; border: 0; padding: 4px 8px; font-size: 13.5px; font-weight: 600; color: var(--tinta); gap: 8px; justify-content: flex-start; }
.nombre.seleccionada { background: var(--superficie-2); }
.clave { display: inline-block; width: 14px; height: 4px; border-radius: 2px; }
.celdas { display: grid; grid-template-columns: repeat(var(--dias), minmax(0, 1fr)); gap: 2px; }
.celda { height: 22px; padding: 0; min-width: 0; border-radius: 3px; border: 0; background: var(--superficie-3); }
/* Estado con dos señales: el color y, en los no certificados, un borde interior oscuro. */
.celda.bien, .cuadro.bien { background: var(--bien); }
.celda.aviso, .cuadro.aviso { background: var(--celda-aviso); }
.celda.critico, .cuadro.critico { background: var(--celda-critico); box-shadow: inset 0 0 0 1.5px var(--tinta); }
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
  .leyenda-mapa { justify-content: flex-start; }
  .mapa { grid-template-columns: 1fr; }
  .celdas { gap: 1px; }
  .celda { height: 16px; border-radius: 1px; }
  .celda.critico { box-shadow: inset 0 0 0 1px var(--tinta); }
  .resumen { display: none; }
}
</style>
