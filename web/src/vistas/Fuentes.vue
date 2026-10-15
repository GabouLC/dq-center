<script setup lang="ts">
import { Clock, FileCheck2, FileX2, Rows3 } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, hora, NOMBRE_TABLA, num, signo, TABLAS } from '@/formato'
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
const exitosas = computed(() => fuente.value?.cargas.filter((c) => c.estado === 'EXITOSA') ?? [])
const rechazos = computed(() => fuente.value?.cargas.filter((c) => c.estado === 'RECHAZADA').length ?? 0)
const estructura = usarCarga(() => api<Estructura>(`/api/v1/fuentes/${tabla.value}/estructura`), [tabla])

// Límite de llegada: corte + 2 días a las 09:00 de Lima (14:00 UTC).
const limite = (fecha: string) => Date.parse(`${fecha}T14:00:00Z`) + 2 * 86400000
const horasDeHolgura = (c: Carga) => (limite(c.fecha_corte) - Date.parse(c.cargado_en)) / 3600000
const tarde = (c: Carga) => horasDeHolgura(c) < 0

// Volumen por corte: una serie, un color; la variación fuera de ±15 % se marca.
const maxFilas = computed(() => Math.max(1, ...exitosas.value.map((c) => c.filas)))
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
        <p>Cada archivo que llegó a RAW: a qué hora, cuántas filas, si se rechazó y cuántos registros no se pudieron homologar.</p>
      </div>
      <div class="segmentos" role="tablist" aria-label="Tabla">
        <button v-for="t in TABLAS" :key="t" type="button" role="tab" :aria-selected="t === tabla" :class="{ activo: t === tabla }" @click="tabla = t">
          {{ NOMBRE_TABLA[t] }}
        </button>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="fuente">
        <section class="panel resumen-fuente">
          <div>
            <h2>{{ NOMBRE_TABLA[fuente.tabla] }}</h2>
            <p class="secundario">{{ fuente.descripcion }}</p>
            <p class="tenue pequeno">Dueño: {{ fuente.dueno }} · dominio {{ fuente.dominio }}</p>
          </div>
          <div class="cifras">
            <span><FileCheck2 :size="18" class="bien" /><strong>{{ exitosas.length }}</strong> cargas</span>
            <span><FileX2 :size="18" :class="rechazos ? 'critico' : 'tenue'" /><strong>{{ rechazos }}</strong> rechazadas</span>
            <span><Clock :size="18" :class="exitosas.some(tarde) ? 'critico' : 'bien'" /><strong>{{ exitosas.filter(tarde).length }}</strong> tarde</span>
          </div>
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2 class="fila"><Rows3 :size="18" class="marca-c" /> Volumen por corte</h2>
            <span class="tenue pequeno">La variación de más de ±15 % entre cortes falla la regla de volumetría</span>
          </div>
          <div class="barras">
            <div v-for="c in exitosas" :key="c.archivo" class="columna" :title="`${nombreCorte(c.fecha_corte)}: ${num(c.filas)} filas (${signo(c.variacion_pct)})`">
              <span class="variacion" :class="{ fuera: Math.abs(c.variacion_pct ?? 0) > 15 }">{{ c.variacion_pct === null ? '' : signo(c.variacion_pct) }}</span>
              <div class="barra-v"><span :style="{ height: `${(c.filas / maxFilas) * 100}%` }" /></div>
              <strong class="num">{{ num(c.filas) }}</strong>
              <span class="tenue">{{ nombreCorte(c.fecha_corte) }}</span>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr><th>Corte</th><th>Archivo</th><th>Llegada (Lima)</th><th>Puntualidad</th><th class="der">Filas</th><th>Estado</th><th class="der">Incidencias</th><th>Detalle</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in fuente.cargas" :key="c.archivo" :class="{ rechazada: c.estado === 'RECHAZADA' }">
                  <td><strong>{{ nombreCorte(c.fecha_corte) }}</strong></td>
                  <td class="mono">{{ c.archivo }}</td>
                  <td>{{ hora(c.cargado_en) }}</td>
                  <td>
                    <span v-if="c.estado !== 'EXITOSA'" class="tenue">—</span>
                    <span v-else-if="tarde(c)" class="chip critico"><Clock :size="12" /> {{ Math.round(-horasDeHolgura(c)) }} h tarde</span>
                    <span v-else class="chip bien"><Clock :size="12" /> a tiempo</span>
                  </td>
                  <td class="der num">{{ num(c.filas) }}</td>
                  <td><EstadoChip :estado="c.estado" /></td>
                  <td class="der num">{{ c.incidencias === null ? '—' : num(c.incidencias) }}</td>
                  <td class="pequeno">{{ c.detalle ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>

      <section class="panel pila">
        <h2>Estructura en MASTER, corte a corte</h2>
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
                  <td><strong>{{ col }}</strong></td>
                  <td><span class="chip" :class="{ sello: tipo === 'BYTES' }">{{ tipo === 'BYTES' ? 'BYTES · cifrado' : tipo }}</span></td>
                  <td v-for="c in estructura.datos.value?.cortes ?? []" :key="c.fecha_corte" class="centro">
                    <span v-if="c.agregadas.includes(col)" class="chip aviso">nueva</span>
                    <span v-else-if="c.columnas.some((x) => x.columna === col)" class="punto-ok" title="presente" />
                    <span v-else class="tenue">·</span>
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
.resumen-fuente { display: flex; justify-content: space-between; gap: 18px; flex-wrap: wrap; align-items: center; }
.cifras { display: flex; gap: 18px; flex-wrap: wrap; }
.cifras span { display: flex; align-items: center; gap: 6px; padding: 10px 14px; border-radius: 12px; background: var(--superficie-2); }
.cifras strong { font-size: 20px; font-weight: 800; }
.bien { color: var(--bien); }
.critico { color: var(--critico); }
.marca-c { color: var(--marca); }
.pequeno { font-size: 12.5px; }
.barras { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 14px; align-items: end; }
.columna { display: grid; justify-items: center; gap: 4px; font-size: 12.5px; }
.variacion { font-weight: 800; font-size: 12px; color: var(--tinta-2); min-height: 18px; }
.variacion.fuera { color: var(--critico-texto); background: var(--critico-suave); padding: 0 8px; border-radius: 999px; }
.barra-v { width: 46px; height: 140px; border-radius: 10px; background: var(--superficie-2); display: flex; align-items: flex-end; overflow: hidden; }
.barra-v span { width: 100%; background: var(--s1); border-radius: 10px 10px 4px 4px; transition: height 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); }
.columna:hover .barra-v span { filter: brightness(1.1); }
.rechazada { background: var(--critico-suave); }
.punto-ok { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--bien); }
</style>
