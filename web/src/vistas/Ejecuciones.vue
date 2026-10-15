<script setup lang="ts">
import { ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, hora, NOMBRE_TABLA } from '@/formato'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'

type Ejecucion = { id_ejecucion: string; fecha_corte: string; origen: string; iniciada_en: string; terminada_en: string; reglas: number }
type Lanzada = { estado: string; id_ejecucion?: string; fecha_corte: string; certificaciones?: Record<string, string>; operacion?: string }

const cortes = useCortes()
const { datos, cargando, error, recargar } = usarCarga(() => api<Ejecucion[]>('/api/v1/ejecuciones'))
const corteElegido = ref('')
const lanzando = ref(false)
const resultado = ref<Lanzada | null>(null)
const errorLanzar = ref<string | null>(null)

async function lanzar() {
  lanzando.value = true
  errorLanzar.value = null
  resultado.value = null
  try {
    resultado.value = await api<Lanzada>('/api/v1/ejecuciones', { metodo: 'POST', cuerpo: { fecha_corte: corteElegido.value || null } })
    await Promise.all([recargar(), cortes.cargar(true)])
  } catch (e) {
    errorLanzar.value = e instanceof Error ? e.message : String(e)
  } finally {
    lanzando.value = false
  }
}
const duracion = (e: Ejecucion) => `${Math.round((Date.parse(e.terminada_en) - Date.parse(e.iniciada_en)) / 1000)} s`
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Ejecuciones</h1>
        <p class="muted">
          Corridas del motor y del Quality &amp; Privacy Gate. Además de la corrida diaria programada, un administrador puede
          reevaluar un corte, por ejemplo después de cambiar una regla.
        </p>
      </div>
    </div>

    <section class="tarjeta fila">
      <label class="campo">Corte a evaluar
        <select v-model="corteElegido">
          <option value="">El último cargado</option>
          <option v-for="c in cortes.lista" :key="c.fecha_corte" :value="c.fecha_corte">{{ nombreCorte(c.fecha_corte) }}</option>
        </select>
      </label>
      <button type="button" class="primario" :disabled="lanzando" @click="lanzar">{{ lanzando ? 'Evaluando…' : 'Ejecutar ahora' }}</button>
      <p v-if="errorLanzar" class="aviso error">{{ errorLanzar }}</p>
      <div v-if="resultado" class="fila resultado" role="status">
        <span class="chip ok">{{ resultado.estado === 'terminada' ? 'Terminada' : 'Lanzada' }}</span>
        <span>{{ nombreCorte(resultado.fecha_corte) }}</span>
        <template v-for="(estado, tabla) in resultado.certificaciones ?? {}" :key="tabla">
          <span class="muted">{{ NOMBRE_TABLA[tabla] }}</span><EstadoChip :estado="estado" />
        </template>
      </div>
    </section>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="tarjeta tabla-envoltura">
        <table>
          <thead><tr><th>Corte</th><th>Origen</th><th>Inicio</th><th>Duración</th><th class="der">Reglas</th><th>Corrida</th></tr></thead>
          <tbody>
            <tr v-for="e in datos ?? []" :key="e.id_ejecucion">
              <td>{{ nombreCorte(e.fecha_corte) }}</td>
              <td>{{ e.origen }}</td>
              <td>{{ hora(e.iniciada_en) }}</td>
              <td class="num">{{ duracion(e) }}</td>
              <td class="der num">{{ e.reglas }}</td>
              <td class="mono muted">{{ e.id_ejecucion.slice(0, 12) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.der { text-align: right; }
.resultado { gap: 6px; }
</style>
