<script setup lang="ts">
import { CircleAlert, RotateCw } from 'lucide-vue-next'

/** Carga: mientras recarga, el contenido anterior queda atenuado (sin parpadeos ni saltos). */
defineProps<{ cargando: boolean; error: string | null; vacio?: boolean }>()
defineEmits<{ reintentar: [] }>()
</script>

<template>
  <div v-if="error" class="aviso-caja error entre" role="alert">
    <CircleAlert :size="18" />
    <span class="mensaje">No se pudo leer: {{ error }}</span>
    <button type="button" @click="$emit('reintentar')"><RotateCw :size="15" /> Reintentar</button>
  </div>
  <div v-else-if="cargando && vacio" class="cargando" aria-live="polite">
    <span class="punto" /><span class="punto" /><span class="punto" />
    <span class="tenue">Cargando…</span>
  </div>
  <div v-else class="pila" :class="{ recargando: cargando }">
    <slot />
  </div>
</template>

<style scoped>
.mensaje { flex: 1; }
.cargando { display: flex; gap: 6px; align-items: center; justify-content: center; padding: 56px 0; }
.punto { width: 8px; height: 8px; border-radius: 50%; background: var(--marca); animation: latido 1s infinite ease-in-out; }
.punto:nth-child(2) { animation-delay: 0.15s; }
.punto:nth-child(3) { animation-delay: 0.3s; }
@keyframes latido { 0%, 100% { opacity: 0.25; transform: scale(0.8); } 50% { opacity: 1; transform: scale(1); } }
.recargando { opacity: 0.55; transition: opacity 0.15s; }
</style>
