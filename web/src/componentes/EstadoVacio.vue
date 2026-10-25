<script setup lang="ts">
import { Inbox } from 'lucide-vue-next'
import type { Component } from 'vue'

/** Estado vacío: por qué no hay nada y qué va a aparecer (o qué hacer para verlo). */
withDefaults(defineProps<{ titulo: string; texto?: string; icono?: Component; tono?: 'neutro' | 'bien' }>(), {
  icono: () => Inbox,
  tono: 'neutro',
  texto: '',
})
</script>

<template>
  <div class="estado-vacio" :class="`tono-${tono}`" role="status">
    <span class="icono-vacio" aria-hidden="true"><component :is="icono" :size="22" :stroke-width="2" /></span>
    <strong>{{ titulo }}</strong>
    <p v-if="texto">{{ texto }}</p>
    <div v-if="$slots.default" class="accion"><slot /></div>
  </div>
</template>

<style scoped>
.estado-vacio { display: grid; justify-items: center; gap: 6px; text-align: center; padding: 32px 18px; }
.icono-vacio {
  display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: 4px; border-radius: 50%;
  background: var(--superficie-2); color: var(--tenue);
}
.tono-bien .icono-vacio { background: var(--bien-suave); color: var(--bien-texto); }
strong { font-size: 15px; }
p { font-size: 13.5px; color: var(--tinta-2); max-width: 52ch; }
.accion { margin-top: 8px; }
</style>
