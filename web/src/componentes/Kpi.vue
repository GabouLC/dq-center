<script setup lang="ts">
defineProps<{ titulo: string; valor: string; detalle?: string; tono?: 'ok' | 'alerta' | 'falla' }>()
</script>

<template>
  <div class="tarjeta kpi">
    <span class="muted titulo">{{ titulo }}</span>
    <strong class="valor num" :class="tono">{{ valor }}</strong>
    <span v-if="detalle" class="muted detalle">{{ detalle }}</span>
  </div>
</template>

<style scoped>
.kpi { display: grid; gap: 2px; }
.titulo { font-size: 12px; }
.valor { font-size: 26px; font-weight: 650; letter-spacing: -0.02em; }
.valor.ok { color: var(--ok); }
.valor.alerta { color: var(--alerta); }
.valor.falla { color: var(--falla); }
.detalle { font-size: 12px; }
</style>
