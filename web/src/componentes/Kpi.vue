<script setup lang="ts">
defineProps<{ titulo: string; valor: string; detalle?: string; tono?: 'bien' | 'aviso' | 'critico'; icono?: unknown }>()
</script>

<template>
  <div class="kpi" :class="tono">
    <span class="titulo">
      <component :is="icono" v-if="icono" :size="16" :stroke-width="2.2" aria-hidden="true" />
      {{ titulo }}
    </span>
    <strong class="valor">{{ valor }}</strong>
    <span v-if="detalle" class="detalle">{{ detalle }}</span>
  </div>
</template>

<style scoped>
.kpi { display: grid; gap: 2px; padding: 14px 16px; border-radius: 12px; background: var(--superficie-2); min-width: 0; }
.titulo { display: flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 700; color: var(--tinta-2); }
.titulo svg { color: var(--marca); }
.kpi.bien .titulo svg { color: var(--bien); }
.kpi.aviso .titulo svg { color: var(--aviso); }
.kpi.critico .titulo svg { color: var(--critico); }
.valor { font-size: 28px; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
.detalle { font-size: 12.5px; color: var(--tenue); }
</style>
