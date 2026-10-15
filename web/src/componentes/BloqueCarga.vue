<script setup lang="ts">
defineProps<{ cargando: boolean; error: string | null; vacio?: boolean }>()
defineEmits<{ reintentar: [] }>()
</script>

<template>
  <div v-if="error" class="aviso error fila entre" role="alert">
    <span>No se pudo leer: {{ error }}</span>
    <button type="button" @click="$emit('reintentar')">Reintentar</button>
  </div>
  <div v-else-if="cargando && vacio" class="cargando muted" aria-live="polite">Cargando…</div>
  <slot v-else />
</template>

<style scoped>
.cargando { padding: 40px 0; text-align: center; }
</style>
