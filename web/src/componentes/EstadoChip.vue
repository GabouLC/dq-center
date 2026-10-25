<script setup lang="ts">
import { CircleCheck, CircleDashed, CircleX, TriangleAlert } from 'lucide-vue-next'
import { computed } from 'vue'

/** Estado con ícono + texto: el color nunca va solo (dataviz: status palette). */
const props = defineProps<{ estado: string; compacto?: boolean }>()

const ESTADOS: Record<string, { tono: string; texto: string; corto: string; icono: unknown }> = {
  OK: { tono: 'bien', texto: 'Cumple', corto: 'Cumple', icono: CircleCheck },
  ALERTA: { tono: 'aviso', texto: 'Alerta', corto: 'Alerta', icono: TriangleAlert },
  FALLA: { tono: 'critico', texto: 'Falla', corto: 'Falla', icono: CircleX },
  SIN_DATOS: { tono: '', texto: 'Sin datos', corto: 'S/d', icono: CircleDashed },
  CERTIFICADO: { tono: 'bien', texto: 'Certificada', corto: 'Cert.', icono: CircleCheck },
  CERTIFICADO_CON_OBSERVACIONES: { tono: 'aviso', texto: 'Con observaciones', corto: 'Obs.', icono: TriangleAlert },
  NO_CERTIFICADO: { tono: 'critico', texto: 'No certificada', corto: 'No cert.', icono: CircleX },
  EXITOSA: { tono: 'bien', texto: 'Exitosa', corto: 'Exitosa', icono: CircleCheck },
  RECHAZADA: { tono: 'critico', texto: 'Rechazada', corto: 'Rech.', icono: CircleX },
}
const datos = computed(() => ESTADOS[props.estado] ?? { tono: '', texto: props.estado, corto: props.estado, icono: CircleDashed })
</script>

<template>
  <span class="chip" :class="datos.tono" :title="datos.texto">
    <component :is="datos.icono" :size="13" :stroke-width="2.4" aria-hidden="true" />
    {{ compacto ? datos.corto : datos.texto }}
  </span>
</template>
