<script setup lang="ts">
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import GraficoTendencia from '@/componentes/GraficoTendencia.vue'
import Kpi from '@/componentes/Kpi.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, NOMBRE_DIMENSION, NOMBRE_TABLA, pct, signo, TABLAS } from '@/formato'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'

type CorteResumen = {
  fecha_corte: string
  global: number | null
  pct_pass: number | null
  por_tabla: Record<string, number | null>
  por_dimension: Record<string, Record<string, number | null>>
  estados: Record<string, number>
  certificacion: Record<string, string>
}

const cortes = useCortes()
const { datos, cargando, error, recargar } = usarCarga(() => api<{ cortes: CorteResumen[] }>('/api/v1/resumen'))
const tablaElegida = ref('persona')

const lista = computed(() => datos.value?.cortes ?? [])
const actual = computed(() => lista.value.find((c) => c.fecha_corte === cortes.elegido) ?? lista.value.at(-1))
const anterior = computed(() => {
  const i = lista.value.findIndex((c) => c === actual.value)
  return i > 0 ? lista.value[i - 1] : null
})
const conDatos = computed(() =>
  Object.entries(actual.value?.estados ?? {}).reduce((n, [estado, k]) => (estado === 'SIN_DATOS' ? n : n + k), 0),
)
const certificadas = computed(
  () => Object.values(actual.value?.certificacion ?? {}).filter((e) => e !== 'NO_CERTIFICADO').length,
)
const series = computed(() => [
  { nombre: 'Global', valores: lista.value.map((c) => c.global), destacada: true },
  ...TABLAS.map((t) => ({ nombre: NOMBRE_TABLA[t], valores: lista.value.map((c) => c.por_tabla[t]) })),
])
const variacion = computed(() => {
  if (!actual.value?.global || !anterior.value?.global) return undefined
  return `${signo(actual.value.global - anterior.value.global, ' pts')} vs. ${nombreCorte(anterior.value.fecha_corte)}`
})
const tonoScore = (v: number | null | undefined) => (v === null || v === undefined ? undefined : v >= 99 ? 'ok' : v >= 97 ? 'alerta' : 'falla')
const DIMENSIONES = ['completitud', 'unicidad', 'validez', 'consistencia', 'integridad', 'oportunidad', 'volumetria']
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Resumen de calidad</h1>
        <p class="muted">Salud y certificación de los datos en cada fecha de corte (HU-09).</p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="actual">
        <section class="grilla-kpi" aria-label="Indicadores del corte">
          <Kpi titulo="Score global" :valor="pct(actual.global)" :detalle="variacion" :tono="tonoScore(actual.global)" />
          <Kpi
            titulo="Reglas en PASS"
            :valor="pct(actual.pct_pass)"
            :detalle="`${actual.estados.OK ?? 0} de ${conDatos} reglas con datos`"
          />
          <Kpi
            titulo="Tablas certificadas"
            :valor="`${certificadas} de ${TABLAS.length}`"
            :tono="certificadas === TABLAS.length ? 'ok' : 'falla'"
            detalle="Solo lo certificado llega a BUSINESS"
          />
          <Kpi
            titulo="Reglas en FAIL"
            :valor="String(actual.estados.FALLA ?? 0)"
            :tono="actual.estados.FALLA ? 'falla' : 'ok'"
            :detalle="`${actual.estados.ALERTA ?? 0} en alerta`"
          />
        </section>

        <section class="tarjeta pila">
          <div class="fila entre">
            <h2>Tendencia del score</h2>
            <span class="muted">Promedio de cumplimiento ponderado por severidad</span>
          </div>
          <GraficoTendencia :etiquetas="lista.map((c) => c.fecha_corte)" :series="series" />
        </section>

        <section class="tarjeta pila">
          <h2>Score y certificación por tabla</h2>
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr>
                  <th>Tabla</th>
                  <th v-for="c in lista" :key="c.fecha_corte" class="der">{{ nombreCorte(c.fecha_corte) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="t in TABLAS"
                  :key="t"
                  class="clicable"
                  :class="{ seleccionada: t === tablaElegida }"
                  @click="tablaElegida = t"
                >
                  <td><strong>{{ NOMBRE_TABLA[t] }}</strong></td>
                  <td v-for="c in lista" :key="c.fecha_corte" class="der celda" :class="{ actual: c === actual }">
                    <span class="num">{{ pct(c.por_tabla[t]) }}</span>
                    <EstadoChip :estado="c.certificacion[t] ?? 'SIN_DATOS'" compacto />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="tarjeta pila">
          <div class="fila entre">
            <h2>Dimensiones de {{ NOMBRE_TABLA[tablaElegida] }} · {{ nombreCorte(actual.fecha_corte) }}</h2>
            <span class="muted">Elige otra tabla en la matriz de arriba</span>
          </div>
          <div class="dimensiones">
            <template v-for="d in DIMENSIONES" :key="d">
              <template v-if="actual.por_dimension[tablaElegida]?.[d] !== undefined">
                <span>{{ NOMBRE_DIMENSION[d] }}</span>
                <div class="barra">
                  <span
                    :style="{
                      width: `${Math.max(0, ((actual.por_dimension[tablaElegida][d] ?? 0) - 80) / 20) * 100}%`,
                      background: `var(--${tonoScore(actual.por_dimension[tablaElegida][d]) ?? 'neutro'})`,
                    }"
                  />
                </div>
                <span class="num der">{{ pct(actual.por_dimension[tablaElegida][d]) }}</span>
              </template>
            </template>
          </div>
          <p class="muted nota">La escala de las barras va de 80 % a 100 %.</p>
        </section>
      </template>
      <p v-else class="muted">Todavía no hay ejecuciones. Corre el flujo para ver resultados.</p>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.celda { white-space: nowrap; }
.celda .num { margin-right: 6px; }
.celda.actual { background: var(--accent-soft); }
.dimensiones { display: grid; grid-template-columns: 120px 1fr 72px; gap: 10px 14px; align-items: center; }
.der { text-align: right; }
.nota { font-size: 12px; }
</style>
