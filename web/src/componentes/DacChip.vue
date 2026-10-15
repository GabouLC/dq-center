<script setup lang="ts">
import { Eye, EyeOff, Lock, ShieldQuestion } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps<{ dac: string }>()
const datos = computed(
  () =>
    ({
      PUBLICO: { tono: '', texto: 'Público', icono: Eye },
      SENSIBLE: { tono: 'aviso', texto: 'Sensible', icono: EyeOff },
      SENSIBLE_CIFRADO: { tono: 'sello', texto: 'Sensible cifrado', icono: Lock },
    })[props.dac] ?? { tono: 'critico', texto: 'Sin clasificar', icono: ShieldQuestion },
)
</script>

<template>
  <span class="chip" :class="datos.tono">
    <component :is="datos.icono" :size="13" :stroke-width="2.4" aria-hidden="true" />
    {{ datos.texto }}
  </span>
</template>
