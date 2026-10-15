<script setup lang="ts">
import { CircleX, History, Play } from 'lucide-vue-next'
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
const ORIGEN: Record<string, string> = { simulacion: 'Simulación', programada: 'Programada' }
const origen = (o: string) => ORIGEN[o] ?? (o.startsWith('manual:') ? `Manual · ${o.slice(7)}` : o)
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Ejecuciones</h1>
        <p>Corridas del motor y del Quality &amp; Privacy Gate. Además de la corrida diaria, puedes reevaluar un corte, por ejemplo después de cambiar una regla.</p>
      </div>
    </div>

    <section class="panel lanzar">
      <div class="icono-grande"><Play :size="26" /></div>
      <div class="pila-chica">
        <h2>Evaluar un corte ahora</h2>
        <div class="fila">
          <select v-model="corteElegido" aria-label="Corte a evaluar">
            <option value="">El último cargado</option>
            <option v-for="c in cortes.lista" :key="c.fecha_corte" :value="c.fecha_corte">{{ nombreCorte(c.fecha_corte) }}</option>
          </select>
          <button type="button" class="primario" :disabled="lanzando" @click="lanzar">
            <Play :size="15" /> {{ lanzando ? 'Evaluando…' : 'Ejecutar' }}
          </button>
        </div>
      </div>
      <p v-if="errorLanzar" class="aviso-caja error"><CircleX :size="17" />{{ errorLanzar }}</p>
      <div v-if="resultado" class="resultado" role="status">
        <strong>{{ resultado.estado === 'terminada' ? 'Corrida terminada' : 'Corrida lanzada' }} · {{ nombreCorte(resultado.fecha_corte) }}</strong>
        <div class="fila">
          <span v-for="(estado, tabla) in resultado.certificaciones ?? {}" :key="tabla" class="fila par">
            <span class="secundario">{{ NOMBRE_TABLA[tabla] }}</span><EstadoChip :estado="estado" compacto />
          </span>
        </div>
      </div>
    </section>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="panel lista">
        <h2 class="fila titulo"><History :size="18" /> Historial</h2>
        <div class="tabla-envoltura">
          <table>
            <thead><tr><th>Corte</th><th>Origen</th><th>Inicio</th><th>Duración</th><th class="der">Reglas</th><th>Corrida</th></tr></thead>
            <tbody>
              <tr v-for="e in datos ?? []" :key="e.id_ejecucion">
                <td><strong>{{ nombreCorte(e.fecha_corte) }}</strong></td>
                <td><span class="chip" :class="{ marca: e.origen.startsWith('manual') }">{{ origen(e.origen) }}</span></td>
                <td>{{ hora(e.iniciada_en) }}</td>
                <td class="num">{{ duracion(e) }}</td>
                <td class="der num">{{ e.reglas }}</td>
                <td class="mono tenue">{{ e.id_ejecucion.slice(0, 12) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.lanzar { display: flex; gap: 18px; align-items: center; flex-wrap: wrap; }
.icono-grande { display: grid; place-items: center; width: 56px; height: 56px; border-radius: 16px; background: var(--marca-suave); color: var(--marca); }
.resultado { display: grid; gap: 6px; padding: 12px 14px; border-radius: 12px; background: var(--bien-suave); flex: 1; min-width: 260px; }
.par { gap: 4px; }
.lista { padding: 16px 12px 8px; }
.titulo { gap: 8px; padding: 0 8px 6px; }
.titulo svg { color: var(--marca); }
</style>
