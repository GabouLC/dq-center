<script setup lang="ts">
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora } from '@/formato'
import { api } from '@/servicios/api'

type Evento = { fecha: string; accion: string; email: string | null; recurso: string; detalle: string }

const TONO: Record<string, string> = {
  ACCESO_DENEGADO: 'falla',
  ACCESO_RESTRINGIDO: 'sensible',
  RENDIMIENTO_LENTO: 'alerta',
  DESACTIVAR: 'alerta',
  CREAR: 'ok',
  ACTUALIZAR: 'acento',
  EJECUTAR: 'acento',
}
const { datos, cargando, error, recargar } = usarCarga(() => api<Evento[]>('/api/v1/admin/auditoria', { params: { limite: 500 } }))
const accion = ref('')
const acciones = computed(() => [...new Set((datos.value ?? []).map((e) => e.accion))].sort())
const eventos = computed(() => (datos.value ?? []).filter((e) => !accion.value || e.accion === accion.value))
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Auditoría</h1>
        <p class="muted">
          Quién cambió qué y cuándo, accesos denegados, campos sensibles ocultos y solicitudes que superaron los 8 segundos
          (HU-13, HU-15).
        </p>
      </div>
      <div class="fila">
        <select v-model="accion" aria-label="Acción">
          <option value="">Todas las acciones</option>
          <option v-for="a in acciones" :key="a" :value="a">{{ a }}</option>
        </select>
        <button type="button" @click="recargar">Actualizar</button>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="tarjeta tabla-envoltura">
        <p v-if="!eventos.length" class="muted">Sin eventos todavía.</p>
        <table v-else>
          <thead><tr><th>Fecha (Lima)</th><th>Acción</th><th>Usuario</th><th>Recurso</th><th>Detalle</th></tr></thead>
          <tbody>
            <tr v-for="(e, i) in eventos" :key="i">
              <td class="num fecha">{{ hora(e.fecha) }}</td>
              <td><span class="chip" :class="TONO[e.accion]">{{ e.accion }}</span></td>
              <td>{{ e.email ?? '—' }}</td>
              <td class="mono">{{ e.recurso }}</td>
              <td>{{ e.detalle }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.fecha { white-space: nowrap; }
</style>
