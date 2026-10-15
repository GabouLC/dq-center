<script setup lang="ts">
import { computed } from 'vue'
import { pct } from '@/formato'

/** Cumplimiento contra el umbral (la marca vertical). La escala empieza en "desde" para que 2 puntos se noten. */
const props = defineProps<{ valor: number | null; umbral: number; estado: string; desde?: number }>()
const minimo = computed(() => props.desde ?? 90)
const posicion = (v: number) => `${Math.max(0, Math.min(100, ((v - minimo.value) / (100 - minimo.value)) * 100))}%`
const color = computed(() => ({ OK: 'var(--bien)', ALERTA: 'var(--aviso)', FALLA: 'var(--critico)' })[props.estado] ?? 'var(--tenue)')
</script>

<template>
  <div class="cumplimiento" :title="`Cumplimiento ${pct(valor)} · umbral ${pct(umbral)} · escala desde ${minimo} %`">
    <div class="barra">
      <span v-if="valor !== null" :style="{ width: posicion(valor), background: color }" />
      <i :style="{ left: posicion(umbral) }" />
    </div>
    <span class="num valor">{{ pct(valor) }}</span>
  </div>
</template>

<style scoped>
.cumplimiento { display: flex; align-items: center; gap: 10px; }
.barra { flex: 1; }
.valor { width: 66px; text-align: right; font-size: 13px; font-weight: 600; }
</style>
