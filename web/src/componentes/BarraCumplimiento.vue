<script setup lang="ts">
import { computed } from 'vue'
import { pct } from '@/formato'

const props = defineProps<{ valor: number | null; umbral: number; estado: string; desde?: number }>()
// La escala empieza en "desde" para que una diferencia de 2 puntos se vea.
const minimo = computed(() => props.desde ?? 90)
const posicion = (v: number) => `${Math.max(0, Math.min(100, ((v - minimo.value) / (100 - minimo.value)) * 100))}%`
const color = computed(() => ({ OK: 'var(--ok)', ALERTA: 'var(--alerta)', FALLA: 'var(--falla)' })[props.estado] ?? 'var(--neutro)')
</script>

<template>
  <div class="fila cumplimiento">
    <div class="barra" :title="`Umbral ${pct(umbral)}`">
      <span v-if="valor !== null" :style="{ width: posicion(valor), background: color }" />
      <i :style="{ left: posicion(umbral) }" />
    </div>
    <span class="num valor">{{ pct(valor) }}</span>
  </div>
</template>

<style scoped>
.cumplimiento { flex-wrap: nowrap; gap: 8px; }
.barra { flex: 1; }
.valor { width: 64px; text-align: right; font-size: 13px; }
</style>
