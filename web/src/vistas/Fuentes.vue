<script setup lang="ts">
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, hora, NOMBRE_TABLA, num, signo } from '@/formato'
import { api } from '@/servicios/api'

type Carga = {
  fecha_corte: string
  archivo: string
  cargado_en: string
  filas: number
  estado: string
  detalle: string | null
  variacion_pct: number | null
  incidencias: number | null
}
type Fuente = { tabla: string; dominio: string; descripcion: string | null; dueno: string | null; cargas: Carga[] }
type Estructura = {
  cortes: { fecha_corte: string; columnas: { columna: string; tipo: string }[]; agregadas: string[]; eliminadas: string[] }[]
}

const tabla = ref('persona')
const { datos, cargando, error, recargar } = usarCarga(() => api<Fuente[]>('/api/v1/fuentes'))
const fuente = computed(() => datos.value?.find((f) => f.tabla === tabla.value))
const estructura = usarCarga(() => api<Estructura>(`/api/v1/fuentes/${tabla.value}/estructura`), [tabla])

// Todas las columnas que alguna vez tuvo la tabla, en orden de aparición.
const columnas = computed(() => {
  const vistas = new Map<string, string>()
  for (const c of estructura.datos.value?.cortes ?? []) for (const col of c.columnas) vistas.set(col.columna, col.tipo)
  return [...vistas.entries()]
})
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Fuentes</h1>
        <p class="muted">
          Cada archivo que llegó a RAW: hora de llegada (Lima), filas, variación de volumen, rechazos de la ingesta e
          incidencias de homologación. Abajo, la estructura de la tabla en cada corte.
        </p>
      </div>
      <div class="fila pestañas" role="tablist">
        <button
          v-for="f in datos ?? []"
          :key="f.tabla"
          type="button"
          role="tab"
          :aria-selected="f.tabla === tabla"
          :class="{ primario: f.tabla === tabla }"
          @click="tabla = f.tabla"
        >{{ NOMBRE_TABLA[f.tabla] }}</button>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section v-if="fuente" class="tarjeta pila">
        <div>
          <h2>{{ NOMBRE_TABLA[fuente.tabla] }} <span class="muted">· {{ fuente.dominio }}</span></h2>
          <p class="muted">{{ fuente.descripcion }} Dueño: {{ fuente.dueno }}.</p>
        </div>
        <div class="tabla-envoltura">
          <table>
            <thead>
              <tr>
                <th>Corte</th><th>Archivo</th><th>Llegada</th><th class="der">Filas</th><th class="der">Variación</th>
                <th>Estado</th><th class="der">Incidencias</th><th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in fuente.cargas" :key="c.archivo" :class="{ rechazada: c.estado === 'RECHAZADA' }">
                <td>{{ nombreCorte(c.fecha_corte) }}</td>
                <td class="mono">{{ c.archivo }}</td>
                <td>{{ hora(c.cargado_en) }}</td>
                <td class="der num">{{ num(c.filas) }}</td>
                <td class="der num" :class="{ fuerte: Math.abs(c.variacion_pct ?? 0) > 15 }">{{ signo(c.variacion_pct) }}</td>
                <td><EstadoChip :estado="c.estado" /></td>
                <td class="der num">{{ c.incidencias === null ? '—' : num(c.incidencias) }}</td>
                <td class="pequeno">{{ c.detalle ?? '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted pequeno">
          Una carga rechazada no llega a RAW. Las incidencias son registros con un valor que no se pudo convertir: quedan
          fuera de MASTER.
        </p>
      </section>

      <section class="tarjeta pila">
        <h2>Estructura en MASTER por corte</h2>
        <BloqueCarga :cargando="estructura.cargando.value" :error="estructura.error.value" :vacio="!estructura.datos.value" @reintentar="estructura.recargar">
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr>
                  <th>Columna</th><th>Tipo</th>
                  <th v-for="c in estructura.datos.value?.cortes ?? []" :key="c.fecha_corte" class="centro">{{ nombreCorte(c.fecha_corte) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="[col, tipo] in columnas" :key="col">
                  <td class="mono">{{ col }}</td>
                  <td class="mono muted">{{ tipo }}</td>
                  <td v-for="c in estructura.datos.value?.cortes ?? []" :key="c.fecha_corte" class="centro">
                    <span v-if="c.agregadas.includes(col)" class="chip alerta">nueva</span>
                    <span v-else-if="c.columnas.some((x) => x.columna === col)" class="ok">●</span>
                    <span v-else class="muted">·</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </BloqueCarga>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.pestañas { gap: 6px; }
.der { text-align: right; }
.centro { text-align: center; }
.rechazada { background: var(--falla-soft); }
.fuerte { color: var(--falla); font-weight: 600; }
.pequeno { font-size: 12.5px; }
.ok { color: var(--ok); }
</style>
