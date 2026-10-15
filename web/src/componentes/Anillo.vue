<script setup lang="ts">
import { computed } from 'vue'
import { usarConteo } from '@/composables/usarConteo'

/** Proporción como anillo (parte de un todo): p. ej. reglas en PASS sobre las reglas con datos. */
const props = withDefaults(defineProps<{ parte: number; total: number; etiqueta: string; tamano?: number }>(), { tamano: 150 })

const R = 52
const CIRC = 2 * Math.PI * R
const proporcion = computed(() => (props.total ? props.parte / props.total : 0))
const animada = usarConteo(proporcion, 1100)
const parteAnimada = usarConteo(computed(() => props.parte), 1100)
</script>

<template>
  <div class="anillo" :style="{ width: `${tamano}px` }">
    <svg viewBox="0 0 120 120" :width="tamano" :height="tamano" role="img" :aria-label="`${etiqueta}: ${parte} de ${total}`">
      <circle cx="60" cy="60" :r="R" fill="none" stroke="var(--superficie-3)" stroke-width="11" />
      <circle
        cx="60"
        cy="60"
        :r="R"
        fill="none"
        stroke="var(--marca)"
        stroke-width="11"
        stroke-linecap="round"
        :stroke-dasharray="`${CIRC * (animada ?? 0)} ${CIRC}`"
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="58" text-anchor="middle" class="valor">{{ Math.round(parteAnimada ?? 0) }}<tspan class="de">/{{ total }}</tspan></text>
      <text x="60" y="76" text-anchor="middle" class="pie">{{ etiqueta }}</text>
    </svg>
  </div>
</template>

<style scoped>
.anillo { display: grid; place-items: center; }
.valor { font-size: 26px; font-weight: 800; fill: var(--tinta); letter-spacing: -0.02em; }
.de { font-size: 14px; font-weight: 600; fill: var(--tenue); }
.pie { font-size: 9.5px; font-weight: 700; fill: var(--tinta-2); }
</style>
