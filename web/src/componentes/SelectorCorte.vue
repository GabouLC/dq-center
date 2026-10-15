<script setup lang="ts">
import { onMounted } from 'vue'
import { corte } from '@/formato'
import { useCortes } from '@/stores/cortes'

const cortes = useCortes()
onMounted(() => cortes.cargar())
</script>

<template>
  <label class="fila selector">
    <span class="muted">Fecha de corte</span>
    <select v-model="cortes.elegido" :disabled="!cortes.lista.length">
      <option v-for="c in cortes.lista" :key="c.fecha_corte" :value="c.fecha_corte">
        {{ c.fecha_corte }} · {{ corte(c.fecha_corte) }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.selector { gap: 8px; font-size: 13px; }
</style>
