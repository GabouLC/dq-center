<script setup lang="ts">
import { ArrowDownRight, ArrowUpRight, CircleX, ShieldCheck, TriangleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Anillo from '@/componentes/Anillo.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import GraficoTendencia from '@/componentes/GraficoTendencia.vue'
import Kpi from '@/componentes/Kpi.vue'
import Sello from '@/componentes/Sello.vue'
import { usarCarga } from '@/composables/usarCarga'
import { usarConteo } from '@/composables/usarConteo'
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
const router = useRouter()
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
const noCertificadas = computed(() => TABLAS.filter((t) => actual.value?.certificacion[t] === 'NO_CERTIFICADO'))
const nombresNoCertificadas = computed(() => noCertificadas.value.map((t) => NOMBRE_TABLA[t]).join(', '))
const delta = computed(() =>
  actual.value?.global != null && anterior.value?.global != null ? actual.value.global - anterior.value.global : null,
)
const scoreAnimado = usarConteo(computed(() => actual.value?.global ?? null))
const tono = (v: number | null | undefined) => (v == null ? undefined : v >= 99 ? 'bien' : v >= 97 ? 'aviso' : 'critico')

// Series en orden fijo (paleta validada): Global destacado y una por tabla.
const COLOR_TABLA: Record<string, string> = { persona: 'var(--s1)', poliza: 'var(--s2)', vehiculo: 'var(--s3)', siniestro: 'var(--s4)', pago: 'var(--s5)' }
const series = computed(() => [
  { clave: 'global', nombre: 'Global', color: 'var(--s-global)', valores: lista.value.map((c) => c.global), destacada: true },
  ...TABLAS.map((t) => ({ clave: t, nombre: NOMBRE_TABLA[t], color: COLOR_TABLA[t], valores: lista.value.map((c) => c.por_tabla[t]) })),
])

const TONO_CELDA: Record<string, string> = { CERTIFICADO: 'bien', CERTIFICADO_CON_OBSERVACIONES: 'aviso', NO_CERTIFICADO: 'critico' }
function abrirValidaciones(tabla: string, fecha: string) {
  cortes.elegido = fecha
  router.push({ path: '/validaciones', query: { tabla } })
}
const DIMENSIONES = Object.keys(NOMBRE_DIMENSION)
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Salud de los datos</h1>
        <p>Calidad, privacidad y certificación de cada tabla en la fecha de corte elegida (HU-09).</p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="actual">
        <!-- Lo característico del sistema: el score y los sellos del Gate -->
        <section class="panel portada">
          <div class="score">
            <span class="etiqueta">Score global · {{ nombreCorte(actual.fecha_corte) }}</span>
            <strong class="cifra" :class="tono(actual.global)">{{ pct(scoreAnimado) }}</strong>
            <span v-if="delta !== null" class="delta" :class="delta >= 0 ? 'sube' : 'baja'">
              <component :is="delta >= 0 ? ArrowUpRight : ArrowDownRight" :size="16" :stroke-width="2.6" />
              {{ signo(delta, ' pts') }} vs. {{ nombreCorte(anterior!.fecha_corte) }}
            </span>
            <Anillo :parte="actual.estados.OK ?? 0" :total="conDatos" etiqueta="reglas en PASS" :tamano="138" />
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
                {{ noCertificadas.length > 1 ? 'llegan' : 'llega' }} a BUSINESS en este corte.
              </span>
            </p>
            <p v-else class="aviso-caja bien">
              <ShieldCheck :size="18" />
              <span>Las {{ TABLAS.length }} tablas están certificadas y publicadas en BUSINESS.</span>
            </p>
          </div>
        </section>

        <section class="indicadores">
          <Kpi titulo="Reglas en PASS" :valor="pct(actual.pct_pass)" :detalle="`${actual.estados.OK ?? 0} de ${conDatos} con datos`" :icono="ShieldCheck" />
          <Kpi titulo="Reglas en alerta" :valor="String(actual.estados.ALERTA ?? 0)" detalle="Hasta 2 puntos bajo el umbral" :tono="actual.estados.ALERTA ? 'aviso' : 'bien'" :icono="TriangleAlert" />
          <Kpi titulo="Reglas en FAIL" :valor="String(actual.estados.FALLA ?? 0)" detalle="Más de 2 puntos bajo el umbral" :tono="actual.estados.FALLA ? 'critico' : 'bien'" :icono="CircleX" />
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Tendencia del score</h2>
            <span class="tenue pequeno">Pasa el cursor para comparar · clic para elegir el corte</span>
          </div>
          <GraficoTendencia
            :etiquetas="lista.map((c) => c.fecha_corte)"
            :series="series"
            :elegido="actual.fecha_corte"
            @elegir="(f) => (cortes.elegido = f)"
          />
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Mapa de certificación</h2>
            <span class="tenue pequeno">Clic en una celda para ver sus validaciones</span>
          </div>
          <div class="tabla-envoltura">
            <table class="mapa">
              <thead>
                <tr>
                  <th>Tabla</th>
                  <th v-for="c in lista" :key="c.fecha_corte" class="centro" :class="{ actual: c === actual }">{{ nombreCorte(c.fecha_corte) }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in TABLAS" :key="t" :class="{ seleccionada: t === tablaElegida }">
                  <th scope="row">
                    <button type="button" class="fantasma nombre-tabla" @click="tablaElegida = t">
                      <span class="clave" :style="{ background: COLOR_TABLA[t] }" />{{ NOMBRE_TABLA[t] }}
                    </button>
                  </th>
                  <td v-for="c in lista" :key="c.fecha_corte" class="celda-mapa">
                    <button
                      type="button"
                      class="celda"
                      :class="[TONO_CELDA[c.certificacion[t]], { actual: c === actual }]"
                      :title="`${NOMBRE_TABLA[t]} · ${nombreCorte(c.fecha_corte)}: ${pct(c.por_tabla[t])}`"
                      @click="abrirValidaciones(t, c.fecha_corte)"
                    >
                      <span class="num">{{ pct(c.por_tabla[t]) }}</span>
                      <EstadoChip :estado="c.certificacion[t] ?? 'SIN_DATOS'" compacto />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Dimensiones de {{ NOMBRE_TABLA[tablaElegida] }} · {{ nombreCorte(actual.fecha_corte) }}</h2>
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
                      background: `var(--${tono(actual.por_dimension[tablaElegida][d]) ?? 'tenue'})`,
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

.mapa th, .mapa td { border-bottom: 0; padding: 4px; }
.mapa thead th { padding: 6px 4px 10px; }
.mapa thead th.actual { color: var(--marca); }
.nombre-tabla { border: 0; padding: 6px 10px; font-size: 14px; color: var(--tinta); gap: 8px; }
.clave { display: inline-block; width: 14px; height: 4px; border-radius: 2px; }
.celda {
  width: 100%;
  min-width: 112px;
  justify-content: space-between;
  border-radius: 10px;
  padding: 9px 10px;
  border: 1px solid transparent;
  background: var(--superficie-2);
  color: var(--tinta);
  font-weight: 700;
}
.celda.bien { background: var(--bien-suave); }
.celda.aviso { background: var(--aviso-suave); }
.celda.critico { background: var(--critico-suave); }
.celda:hover { border-color: var(--tinta-2); color: var(--tinta); transform: translateY(-1px); box-shadow: var(--sombra); }
.celda.actual { border-color: var(--marca); }
.celda .num { white-space: nowrap; }
.celda :deep(.chip) { background: color-mix(in srgb, var(--superficie) 70%, transparent); }

.dimensiones { display: grid; grid-template-columns: 130px 1fr 72px; gap: 12px 16px; align-items: center; }
.nombre-dim { font-weight: 600; }
.barra.alta { height: 12px; }
.dimensiones strong { text-align: right; }

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
