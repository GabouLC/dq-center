<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ estado: string; compacto?: boolean }>()

// Versión corta para matrices con muchas columnas; el nombre completo va en el título.
const CORTO: Record<string, string> = {
  CERTIFICADO: '✓',
  CERTIFICADO_CON_OBSERVACIONES: 'Obs.',
  NO_CERTIFICADO: '✕ No',
}

const ESTADOS: Record<string, [string, string]> = {
  OK: ['ok', 'PASS'],
  ALERTA: ['alerta', 'Alerta'],
  FALLA: ['falla', 'FAIL'],
  SIN_DATOS: ['', 'Sin datos'],
  CERTIFICADO: ['ok', 'Certificada'],
  CERTIFICADO_CON_OBSERVACIONES: ['alerta', 'Con observaciones'],
  NO_CERTIFICADO: ['falla', 'No certificada'],
  EXITOSA: ['ok', 'Exitosa'],
  RECHAZADA: ['falla', 'Rechazada'],
}
const datos = computed(() => ESTADOS[props.estado] ?? ['', props.estado])
</script>

<template>
  <span class="chip" :class="datos[0]" :title="datos[1]">{{ compacto ? (CORTO[estado] ?? datos[1]) : datos[1] }}</span>
</template>
