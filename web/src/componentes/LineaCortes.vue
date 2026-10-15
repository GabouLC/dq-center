<script setup lang="ts">
import { CircleCheck, CircleX } from 'lucide-vue-next'
import { onMounted } from 'vue'
import { corte, pct } from '@/formato'
import { useCortes } from '@/stores/cortes'

/** Línea de tiempo de cortes: cada mes muestra su score y si alguna tabla quedó sin certificar. */
const cortes = useCortes()
onMounted(() => cortes.cargar())
</script>

<template>
  <nav class="linea" aria-label="Fecha de corte">
    <button
      v-for="c in cortes.lista"
      :key="c.fecha_corte"
      type="button"
      class="mes"
      :class="{ activo: c.fecha_corte === cortes.elegido, alerta: c.no_certificadas > 0 }"
      :aria-pressed="c.fecha_corte === cortes.elegido"
      :title="`${c.fecha_corte} · score ${pct(c.global)} · ${c.no_certificadas ? `${c.no_certificadas} tabla(s) sin certificar` : 'todas certificadas'}`"
      @click="cortes.elegido = c.fecha_corte"
    >
      <span class="nombre">{{ corte(c.fecha_corte).split(' ')[0] }}</span>
      <span class="score num">{{ pct(c.global) }}</span>
      <CircleX v-if="c.no_certificadas" :size="14" class="icono critico" aria-label="con tablas sin certificar" />
      <CircleCheck v-else :size="14" class="icono bien" aria-label="todas certificadas" />
    </button>
  </nav>
</template>

<style scoped>
.linea { display: flex; gap: 4px; padding: 4px; background: var(--superficie-2); border-radius: 14px; overflow-x: auto; max-width: 100%; }
.mes {
  display: grid;
  grid-template-columns: auto auto;
  grid-template-areas: "nombre icono" "score score";
  align-items: center;
  column-gap: 6px;
  row-gap: 0;
  border: 0;
  border-radius: 10px;
  padding: 5px 12px;
  background: transparent;
  color: var(--tinta-2);
  min-width: 78px;
  text-align: left;
}
.mes:hover { background: var(--superficie); color: var(--tinta); }
.mes.activo { background: var(--superficie); color: var(--tinta); box-shadow: 0 1px 3px rgb(15 27 45 / 0.16), inset 0 -2px 0 var(--marca); }
.nombre { grid-area: nombre; font-weight: 700; text-transform: capitalize; font-size: 13px; }
.score { grid-area: score; font-size: 11.5px; color: var(--tenue); font-weight: 600; }
.icono { grid-area: icono; justify-self: end; }
.icono.bien { color: var(--bien); }
.icono.critico { color: var(--critico); }
</style>
