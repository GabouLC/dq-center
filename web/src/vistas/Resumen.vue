<script setup lang="ts">
import { Activity, ArrowDownRight, ArrowUpRight, BadgeCheck, CircleX, Gauge, ShieldCheck, TriangleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Anillo from '@/componentes/Anillo.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import GraficoTendencia from '@/componentes/GraficoTendencia.vue'
import Kpi from '@/componentes/Kpi.vue'
import MapaDias from '@/componentes/MapaDias.vue'
import Sello from '@/componentes/Sello.vue'
import { usarCarga } from '@/composables/usarCarga'
import { usarConteo } from '@/composables/usarConteo'
import {
  corte as nombreCorte, corteCorto, NOMBRE_CERTIFICACION, NOMBRE_DIMENSION, NOMBRE_TABLA, pct, relativo, signo, TABLAS,
} from '@/formato'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'
import { useVivo } from '@/stores/vivo'

type CorteResumen = {
  fecha_corte: string
  global: number | null
  pct_pass: number | null
  pct_pass_tabla: Record<string, number | null>
  por_tabla: Record<string, number | null>
  por_dimension: Record<string, Record<string, number | null>>
  estados: Record<string, number>
  certificacion: Record<string, string>
}

const cortes = useCortes()
const vivo = useVivo()
const router = useRouter()
const { datos, cargando, error, recargar } = usarCarga(() => api<{ cortes: CorteResumen[] }>('/api/v1/resumen'))
const tablaElegida = ref('persona')
const metrica = ref<'pass' | 'score'>('pass')

const lista = computed(() => datos.value?.cortes ?? [])
const actual = computed(() => lista.value.find((c) => c.fecha_corte === cortes.elegido) ?? lista.value.at(-1))
const anterior = computed(() => {
  const i = lista.value.findIndex((c) => c === actual.value)
  return i > 0 ? lista.value[i - 1] : null
})
const conDatos = computed(() =>
  Object.entries(actual.value?.estados ?? {}).reduce((n, [estado, k]) => (estado === 'SIN_DATOS' ? n : n + k), 0),
)
const noCertificadas = computed(() => TABLAS.filter((t) => actual.value?.certificacion[t] === 'NO_CERTIFICADO'))
const certificadas = computed(() => TABLAS.length - noCertificadas.value.length)
const nombresNoCertificadas = computed(() => noCertificadas.value.map((t) => NOMBRE_TABLA[t]).join(', '))
const diferencia = (a?: number | null, b?: number | null) => (a != null && b != null ? a - b : null)
const deltaPass = computed(() => diferencia(actual.value?.pct_pass, anterior.value?.pct_pass))
const deltaScore = computed(() => diferencia(actual.value?.global, anterior.value?.global))
const passAnimado = usarConteo(computed(() => actual.value?.pct_pass ?? null))
const tonoPass = (v: number | null | undefined) => (v == null ? undefined : v >= 85 ? 'bien' : v >= 70 ? 'aviso' : 'critico')
const tonoScore = (v: number | null | undefined) => (v == null ? undefined : v >= 99 ? 'bien' : v >= 97 ? 'aviso' : 'critico')

// Series en orden fijo (paleta validada): Global destacado y una por tabla.
const COLOR_TABLA: Record<string, string> = { persona: 'var(--s1)', poliza: 'var(--s2)', vehiculo: 'var(--s3)', siniestro: 'var(--s4)', pago: 'var(--s5)' }
const series = computed(() => {
  const global = (c: CorteResumen) => (metrica.value === 'pass' ? c.pct_pass : c.global)
  const tabla = (c: CorteResumen, t: string) => (metrica.value === 'pass' ? c.pct_pass_tabla?.[t] ?? null : c.por_tabla[t])
  return [
    { clave: 'global', nombre: 'Global', color: 'var(--s-global)', valores: lista.value.map(global), destacada: true },
    ...TABLAS.map((t) => ({ clave: t, nombre: NOMBRE_TABLA[t], color: COLOR_TABLA[t], valores: lista.value.map((c) => tabla(c, t)) })),
  ]
})
const alertas = computed(() => lista.value.map((c) => Object.values(c.certificacion).includes('NO_CERTIFICADO')))

const filasMapa = computed(() =>
  TABLAS.map((t) => ({
    clave: t,
    nombre: NOMBRE_TABLA[t],
    color: COLOR_TABLA[t],
    estados: Object.fromEntries(lista.value.map((c) => [c.fecha_corte, c.certificacion[t]])),
    detalle: (d: string) => `score ${pct(lista.value.find((c) => c.fecha_corte === d)?.por_tabla[t])}`,
  })),
)
function abrirValidaciones(fecha: string, tabla: string) {
  cortes.elegido = fecha
  router.push({ path: '/validaciones', query: { tabla } })
}
const DIMENSIONES = Object.keys(NOMBRE_DIMENSION)
const actividad = computed(() => vivo.eventos.slice(0, 6))
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Salud de los datos</h1>
        <p>Calidad, privacidad y certificación de cada tabla en el día elegido (HU-09).</p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="actual">
        <!-- Lo característico del sistema: el indicador del backlog y los sellos del Gate -->
        <section class="panel portada">
          <div class="score">
            <span class="etiqueta">Reglas en PASS · {{ nombreCorte(actual.fecha_corte) }}</span>
            <strong class="cifra" :class="tonoPass(actual.pct_pass)">{{ pct(passAnimado) }}</strong>
            <span v-if="deltaPass !== null && anterior" class="delta" :class="deltaPass >= 0 ? 'sube' : 'baja'">
              <component :is="deltaPass >= 0 ? ArrowUpRight : ArrowDownRight" :size="16" :stroke-width="2.6" />
              {{ signo(deltaPass, ' pts') }} vs. {{ corteCorto(anterior.fecha_corte) }}
            </span>
            <Anillo :parte="certificadas" :total="TABLAS.length" etiqueta="en BUSINESS" :tamano="132" />
          </div>
          <div class="sellos">
            <div class="fila entre">
              <h2>Sellos del Quality &amp; Privacy Gate</h2>
              <RouterLink to="/certificacion" class="enlace">Ver certificación</RouterLink>
            </div>
            <div class="grilla-sellos">
              <RouterLink v-for="t in TABLAS" :key="t" to="/certificacion" class="sin-subrayado">
                <Sello :estado="actual.certificacion[t] ?? ''" :tabla="NOMBRE_TABLA[t]" :detalle="pct(actual.por_tabla[t])" :tamano="104" />
              </RouterLink>
            </div>
            <p v-if="noCertificadas.length" class="aviso-caja error">
              <CircleX :size="18" />
              <span>
                {{ nombresNoCertificadas }} no
                {{ noCertificadas.length > 1 ? 'llegan' : 'llega' }} a BUSINESS este día.
              </span>
            </p>
            <p v-else class="aviso-caja bien">
              <ShieldCheck :size="18" />
              <span>Las {{ TABLAS.length }} tablas están certificadas y publicadas en BUSINESS.</span>
            </p>
          </div>
        </section>

        <section class="indicadores">
          <Kpi
            titulo="Score de calidad"
            :valor="pct(actual.global)"
            :detalle="deltaScore !== null ? `${signo(deltaScore, ' pts')} vs. día anterior · ponderado por severidad` : 'Ponderado por severidad'"
            :tono="tonoScore(actual.global)"
            :icono="Gauge"
          />
          <Kpi titulo="Reglas en alerta" :valor="String(actual.estados.ALERTA ?? 0)" :detalle="`De ${conDatos} con datos · hasta 2 puntos bajo el umbral`" :tono="actual.estados.ALERTA ? 'aviso' : 'bien'" :icono="TriangleAlert" />
          <Kpi titulo="Reglas en FAIL" :valor="String(actual.estados.FALLA ?? 0)" detalle="Más de 2 puntos bajo el umbral" :tono="actual.estados.FALLA ? 'critico' : 'bien'" :icono="CircleX" />
        </section>

        <div class="dos-columnas">
          <section class="panel pila tendencia">
            <div class="fila entre">
              <h2>Tendencia diaria</h2>
              <div class="segmentos" role="group" aria-label="Indicador">
                <button type="button" :class="{ activo: metrica === 'pass' }" @click="metrica = 'pass'">% reglas en PASS</button>
                <button type="button" :class="{ activo: metrica === 'score' }" @click="metrica = 'score'">Score</button>
              </div>
            </div>
            <GraficoTendencia
              :etiquetas="lista.map((c) => c.fecha_corte)"
              :series="series"
              :elegido="actual.fecha_corte"
              :alertas="alertas"
              :unidad="metrica === 'pass' ? '% de reglas en PASS' : 'score'"
              @elegir="(f) => (cortes.elegido = f)"
            />
            <p class="tenue pequeno">Puntos rojos: días con alguna tabla sin certificar. Franjas grises: fin de semana.</p>
          </section>

          <section v-if="vivo.estado?.activo" class="panel pila actividad">
            <div class="fila entre">
              <h2><Activity :size="18" class="marca-c" /> Actividad en vivo</h2>
              <button type="button" class="fantasma enlace" @click="vivo.panelAbierto = true">Ver todo</button>
            </div>
            <ol class="feed">
              <li v-for="e in actividad" :key="e.id" :class="e.tono">
                <span class="punto-feed" />
                <div>
                  <strong>{{ e.titulo }}</strong>
                  <span class="tenue">{{ e.detalle }}</span>
                  <span class="tenue cuando">{{ relativo(e.cuando) }}</span>
                </div>
              </li>
              <li v-if="!actividad.length" class="tenue">Esperando el próximo archivo…</li>
            </ol>
          </section>
        </div>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Mapa de certificación</h2>
            <span class="leyenda-mapa">
              <span class="cuadro bien" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO }}
              <span class="cuadro aviso" /> {{ NOMBRE_CERTIFICACION.CERTIFICADO_CON_OBSERVACIONES }}
              <span class="cuadro critico" /> {{ NOMBRE_CERTIFICACION.NO_CERTIFICADO }}
            </span>
          </div>
          <MapaDias
            :dias="lista.map((c) => c.fecha_corte)"
            :filas="filasMapa"
            :elegido="actual.fecha_corte"
            :seleccionada="tablaElegida"
            @elegir="abrirValidaciones"
            @seleccionar="(t) => (tablaElegida = t)"
          />
          <p class="tenue pequeno">Cada cuadro es un día. Clic para ver las validaciones de esa tabla ese día.</p>
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Dimensiones de {{ NOMBRE_TABLA[tablaElegida] }} · {{ corteCorto(actual.fecha_corte) }}</h2>
            <div class="segmentos" role="group" aria-label="Tabla">
              <button v-for="t in TABLAS" :key="t" type="button" :class="{ activo: t === tablaElegida }" @click="tablaElegida = t">
                {{ NOMBRE_TABLA[t] }}
              </button>
            </div>
          </div>
          <div class="dimensiones">
            <template v-for="d in DIMENSIONES" :key="d">
              <template v-if="actual.por_dimension[tablaElegida]?.[d] !== undefined">
                <span class="nombre-dim">{{ NOMBRE_DIMENSION[d] }}</span>
                <div class="barra alta" :title="`${NOMBRE_DIMENSION[d]}: ${pct(actual.por_dimension[tablaElegida][d])}`">
                  <span
                    :style="{
                      width: `${Math.max(2, ((actual.por_dimension[tablaElegida][d] ?? 0) - 80) / 20 * 100)}%`,
                      background: `var(--${tonoScore(actual.por_dimension[tablaElegida][d]) ?? 'tenue'})`,
                    }"
                  />
                </div>
                <strong class="num">{{ pct(actual.por_dimension[tablaElegida][d]) }}</strong>
              </template>
            </template>
          </div>
          <p class="tenue pequeno">Escala de 80 % a 100 %, ponderada por la severidad de cada regla.</p>
        </section>
      </template>
      <p v-else class="tenue">Todavía no hay ejecuciones. Corre el flujo para ver resultados.</p>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.portada { display: grid; grid-template-columns: minmax(230px, 280px) 1fr; gap: 28px; align-items: center; }
.score { display: grid; justify-items: start; gap: 4px; padding-right: 28px; border-right: 1px solid var(--linea); }
.etiqueta { font-size: 13px; font-weight: 700; color: var(--tinta-2); }
.cifra { font-size: 56px; font-weight: 800; letter-spacing: -0.04em; line-height: 1.05; }
.cifra.bien { color: var(--bien-texto); }
.cifra.aviso { color: var(--aviso-texto); }
.cifra.critico { color: var(--critico-texto); }
.delta { display: inline-flex; align-items: center; gap: 4px; font-size: 13px; font-weight: 700; margin-bottom: 10px; }
.delta.sube { color: var(--bien-texto); }
.delta.baja { color: var(--critico-texto); }
.sellos { display: grid; gap: 14px; }
.grilla-sellos { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px; }
.sin-subrayado { color: inherit; text-decoration: none !important; border-radius: 12px; }
.enlace { font-weight: 700; font-size: 13.5px; }
.indicadores { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.pequeno { font-size: 12.5px; }
.marca-c { color: var(--marca); }

.dos-columnas { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }
.dos-columnas > :only-child { grid-column: 1 / -1; }
.actividad h2 { display: inline-flex; align-items: center; gap: 8px; }
.feed { list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }
.feed li { display: grid; grid-template-columns: 12px 1fr; gap: 10px; animation: entra 0.4s ease; }
.feed li > div { display: grid; gap: 1px; font-size: 12.5px; min-width: 0; }
.feed strong { font-size: 13px; }
.cuando { font-size: 11.5px; }
.punto-feed { width: 9px; height: 9px; border-radius: 50%; margin-top: 4px; background: var(--marca); }
.feed .bien .punto-feed { background: var(--bien); }
.feed .aviso .punto-feed { background: var(--aviso); }
.feed .critico .punto-feed { background: var(--critico); }
@keyframes entra { from { opacity: 0; transform: translateY(-6px); } }

.leyenda-mapa { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--tinta-2); flex-wrap: wrap; }
.cuadro { width: 11px; height: 11px; border-radius: 3px; display: inline-block; margin-left: 8px; }
.cuadro.bien { background: var(--bien); }
.cuadro.aviso { background: color-mix(in srgb, var(--aviso) 70%, var(--superficie)); }
.cuadro.critico { background: var(--critico); }

.dimensiones { display: grid; grid-template-columns: 130px 1fr 72px; gap: 12px 16px; align-items: center; }
.nombre-dim { font-weight: 600; }
.barra.alta { height: 12px; }
.dimensiones strong { text-align: right; }

@media (max-width: 1250px) {
  .dos-columnas { grid-template-columns: 1fr; }
}
@media (max-width: 1100px) {
  .portada { grid-template-columns: 1fr; }
  .score { border-right: 0; padding-right: 0; border-bottom: 1px solid var(--linea); padding-bottom: 18px; grid-template-columns: 1fr auto; align-items: center; }
  .score :deep(.anillo) { grid-row: 1 / span 3; grid-column: 2; }
}
@media (max-width: 760px) {
  .grilla-sellos { grid-template-columns: repeat(3, minmax(0, 1fr)); row-gap: 16px; }
  .indicadores { grid-template-columns: 1fr; }
  .cifra { font-size: 44px; }
  .dimensiones { grid-template-columns: 100px 1fr 60px; }
}
</style>
