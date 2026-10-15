<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ dac: string }>()
const datos = computed(
  () =>
    ({
      PUBLICO: ['', 'Público'],
      SENSIBLE: ['sensible', 'Sensible'],
      SENSIBLE_CIFRADO: ['cifrado', '🔒 Sensible cifrado'],
    })[props.dac] ?? ['falla', 'Sin clasificar'],
)
</script>

<template>
  <span class="chip" :class="datos[0]">{{ datos[1] }}</span>
</template>
