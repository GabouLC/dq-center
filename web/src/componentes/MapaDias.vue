<script setup lang="ts">
import { CircleCheck, CircleX, TriangleAlert } from 'lucide-vue-next'
import { computed, onBeforeUnmount, ref } from 'vue'
import { corte, corteCorto, esFinDeSemana, NOMBRE_CERTIFICACION } from '@/formato'

/**
 * Mapa de certificación por día: una fila por tabla y un cuadro por día, con el
 * color de su certificación. Clic en un cuadro para elegir ese día (y esa tabla).
 * Con teclado, cada fila es una sola parada de Tab y las flechas recorren los días.
 * Al pasar el puntero o llegar con el teclado, una tarjeta dice el día, la tabla, su
 * estado y qué significa (el lector de pantalla lo recibe en la etiqueta del cuadro).
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
const ICONO: Record<string, unknown> = { bien: CircleCheck, aviso: TriangleAlert, critico: CircleX }
const SIGNIFICA: Record<string, string> = {
  CERTIFICADO: 'Llegó a negocio sin observaciones.',
  CERTIFICADO_CON_OBSERVACIONES: 'Llegó a negocio con observaciones que no impiden publicarla.',
  NO_CERTIFICADO: 'Se retuvo: no llegó a negocio (BUSINESS) ese día.',
}
const meses = computed(() => props.dias.flatMap((d, i) => (d.endsWith('-01') || i === 0 ? [{ i, nombre: corteCorto(d) }] : [])))
const iElegido = computed(() => props.dias.indexOf(props.elegido ?? ''))
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

// Tarjeta del cuadro: se ubica sobre el cuadro, sin salirse del mapa.
const mapa = ref<HTMLElement | null>(null)
const tarjeta = ref<{ fila: Fila; dia: string; x: number; y: number; abajo: boolean } | null>(null)
// Al pasar de un cuadro al vecino la tarjeta se mueve, sin apagarse y volver a aparecer.
let esperaOcultar = 0
onBeforeUnmount(() => clearTimeout(esperaOcultar))
function mostrar(fila: Fila, dia: string, evento: Event) {
  clearTimeout(esperaOcultar)
  const cuadro = (evento.currentTarget as HTMLElement).getBoundingClientRect()
  const caja = mapa.value?.getBoundingClientRect()
  if (!caja) return
  const centro = cuadro.left + cuadro.width / 2 - caja.left
  const x = Math.min(Math.max(centro, 130), caja.width - 130)
  const arriba = cuadro.top - caja.top
  tarjeta.value = { fila, dia, x, y: arriba < 120 ? cuadro.bottom - caja.top + 8 : arriba - 8, abajo: arriba < 120 }
}
function ocultar(fila: Fila, dia: string) {
  clearTimeout(esperaOcultar)
  esperaOcultar = window.setTimeout(() => {
    if (tarjeta.value?.fila.clave === fila.clave && tarjeta.value.dia === dia) tarjeta.value = null
  }, 70)
}
</script>

<template>
  <div class="mapa-dias">
    <p class="leyenda-mapa">
      <span><i class="cuadro bien" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO }}</span>
      <span><i class="cuadro aviso" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO_CON_OBSERVACIONES }}</span>
      <span><i class="cuadro critico" /> {{ NOMBRE_CERTIFICACION.NO_CERTIFICADO }}</span>
      <span v-if="elegido"><i class="cuadro elegido" /> Día elegido</span>
    </p>
    <div ref="mapa" class="mapa" :style="{ '--dias': dias.length }">
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
            :aria-label="`${f.nombre}, ${corte(d)}: ${NOMBRE_CERTIFICACION[f.estados[d] ?? ''] ?? 'sin datos'}${f.detalle ? `, ${f.detalle(d)}` : ''}`"
            @click="emit('elegir', d, f.clave)"
            @mouseenter="mostrar(f, d, $event)"
            @mouseleave="ocultar(f, d)"
            @focus="mostrar(f, d, $event)"
            @blur="ocultar(f, d)"
          />
        </div>
        <span class="resumen" title="Días certificados, con observaciones y no certificados">
          <b class="t-bien">{{ conteo(f).CERTIFICADO ?? 0 }}</b> cert. · <b class="t-aviso">{{ conteo(f).CERTIFICADO_CON_OBSERVACIONES ?? 0 }}</b> obs. ·
          <b class="t-critico">{{ conteo(f).NO_CERTIFICADO ?? 0 }}</b> no cert.
        </span>
      </template>
      <span />
      <div class="meses" aria-hidden="true">
        <span v-for="m in meses" :key="m.i" :style="{ left: `calc(${m.i} / var(--dias) * 100%)` }">{{ m.nombre }}</span>
        <span v-if="iElegido >= 0" class="marca-elegido" :style="{ left: `calc(${iElegido + 0.5} / var(--dias) * 100%)` }">{{ corteCorto(elegido!) }}</span>
      </div>
      <span />

      <Transition name="tarjeta">
        <div
          v-if="tarjeta"
          class="tarjeta-celda"
          :class="{ abajo: tarjeta.abajo }"
          :style="{ left: `${tarjeta.x}px`, top: `${tarjeta.y}px` }"
          aria-hidden="true"
        >
          <span class="t-dia">{{ corte(tarjeta.dia) }}</span>
          <span class="t-tabla"><i v-if="tarjeta.fila.color" class="clave" :style="{ background: tarjeta.fila.color }" />{{ tarjeta.fila.nombre }}</span>
          <span class="chip" :class="TONO[tarjeta.fila.estados[tarjeta.dia] ?? '']">
            <component :is="ICONO[TONO[tarjeta.fila.estados[tarjeta.dia] ?? '']]" v-if="ICONO[TONO[tarjeta.fila.estados[tarjeta.dia] ?? '']]" :size="13" :stroke-width="2.4" />
            {{ NOMBRE_CERTIFICACION[tarjeta.fila.estados[tarjeta.dia] ?? ''] ?? 'Sin datos' }}
          </span>
          <span class="t-porque">{{ SIGNIFICA[tarjeta.fila.estados[tarjeta.dia] ?? ''] ?? 'Ese día no llegaron sus datos.' }}</span>
          <span v-if="tarjeta.fila.detalle" class="t-detalle">{{ tarjeta.fila.detalle(tarjeta.dia) }}</span>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.mapa-dias { display: grid; gap: 12px; }
.leyenda-mapa { display: flex; justify-content: flex-end; align-items: center; gap: 4px 16px; font-size: 12.5px; color: var(--tinta-2); flex-wrap: wrap; }
.leyenda-mapa span { display: inline-flex; align-items: center; gap: 7px; }
.cuadro { width: 12px; height: 12px; border-radius: 4px; display: inline-block; background: var(--superficie-3); }
.cuadro.elegido { background: transparent; box-shadow: inset 0 0 0 2px var(--marca); }
.mapa { position: relative; display: grid; grid-template-columns: 116px minmax(0, 1fr) max-content; gap: 8px 12px; align-items: center; }
.nombre { display: inline-flex; align-items: center; border: 0; padding: 5px 9px; font-size: 13.5px; font-weight: 600; color: var(--tinta); gap: 8px; justify-content: flex-start; border-radius: 10px; }
.nombre.seleccionada { background: var(--marca-suave); color: var(--tinta); }
.clave { display: inline-block; width: 14px; height: 4px; border-radius: 2px; flex: none; }
.celdas { display: grid; grid-template-columns: repeat(var(--dias), minmax(0, 1fr)); gap: 2px; }
.celda {
  height: 30px; padding: 0; min-width: 0; border-radius: 4px; border: 0; background: var(--superficie-3);
  transition: transform 0.12s var(--ease-out), filter 0.12s ease;
}
/* Estado con dos señales: el color y, en los no certificados, un borde interior oscuro. */
.celda.bien, .cuadro.bien { background: var(--bien); }
.celda.aviso, .cuadro.aviso { background: var(--celda-aviso); }
.celda.critico, .cuadro.critico { background: var(--celda-critico); box-shadow: inset 0 0 0 1.5px var(--tinta); }
.celda.finde { opacity: 0.78; }
@media (hover: hover) and (pointer: fine) {
  .celda:hover { transform: scaleY(1.14); filter: brightness(1.08); }
}
.celda:focus-visible { outline: 2px solid var(--tinta); outline-offset: 1px; transform: scaleY(1.14); }
/* Día elegido: un marco de marca alrededor del cuadro de cada fila. */
.celda.actual { outline: 2px solid var(--marca); outline-offset: 1px; position: relative; z-index: 1; }
.resumen { font-size: 12px; white-space: nowrap; color: var(--tenue); }
.t-bien { color: var(--bien-texto); }
.t-aviso { color: var(--aviso-texto); }
.t-critico { color: var(--critico-texto); }
.meses { position: relative; height: 22px; }
.meses span { position: absolute; top: 2px; font-size: 11px; font-weight: 700; color: var(--tenue); }
.meses .marca-elegido {
  top: 0; transform: translateX(-50%); padding: 1px 7px; border-radius: 999px; z-index: 1;
  background: var(--marca); color: var(--sobre-marca); font-size: 11px; white-space: nowrap; box-shadow: 0 0 0 2px var(--superficie);
}

/* Tarjeta del cuadro (puntero o teclado). */
.tarjeta-celda {
  position: absolute; z-index: 5; width: 240px; transform: translate(-50%, -100%); pointer-events: none;
  display: grid; gap: 4px; justify-items: start; padding: 11px 13px; border-radius: 12px;
  background: var(--superficie); border: 1px solid var(--linea); box-shadow: var(--elev-3); font-size: 12.5px;
}
.tarjeta-celda.abajo { transform: translate(-50%, 0); }
.t-dia { font-weight: 800; font-size: 13px; }
.t-dia::first-letter { text-transform: uppercase; }
.t-tabla { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; color: var(--tinta-2); }
.t-porque { color: var(--tinta-2); line-height: 1.4; }
.t-detalle { color: var(--tenue); font-variant-numeric: tabular-nums; }
/* Aparece rápido y sin desplazarse: los siguientes cuadros solo la mueven. */
.tarjeta-enter-active { transition: opacity 0.12s var(--ease-out); }
.tarjeta-leave-active { transition: opacity 0.08s ease; }
.tarjeta-enter-from, .tarjeta-leave-to { opacity: 0; }

@media (max-width: 760px) {
  .leyenda-mapa { justify-content: flex-start; }
  .mapa { grid-template-columns: 1fr; gap: 6px; }
  .celdas { gap: 1px; }
  .celda { height: 20px; border-radius: 2px; }
  .celda.critico { box-shadow: inset 0 0 0 1px var(--tinta); }
  .resumen { display: none; }
  .tarjeta-celda { display: none; }
}
</style>
