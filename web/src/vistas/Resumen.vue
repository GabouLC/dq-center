<script setup lang="ts">
import { Activity, ArrowDownRight, ArrowUpRight, CalendarClock, CircleCheck, CircleX, Gauge, Minus, TriangleAlert } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import Anillo from '@/componentes/Anillo.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EncabezadoSeccion from '@/componentes/EncabezadoSeccion.vue'
import EstadoVacio from '@/componentes/EstadoVacio.vue'
import GraficoTendencia from '@/componentes/GraficoTendencia.vue'
import Kpi, { type Variacion } from '@/componentes/Kpi.vue'
import LecturaRapida from '@/componentes/LecturaRapida.vue'
import MapaDias from '@/componentes/MapaDias.vue'
import Sello from '@/componentes/Sello.vue'
import { usarCarga } from '@/composables/usarCarga'
import { usarConteo } from '@/composables/usarConteo'
import {
  corteCorto, NOMBRE_DIMENSION, NOMBRE_TABLA, pct, relativo, signo, TABLAS,
} from '@/formato'
import type { Clave } from '@/navegacion'
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
const diferencia = (a?: number | null, b?: number | null) => (a != null && b != null ? a - b : null)
const deltaPass = computed(() => diferencia(actual.value?.pct_pass, anterior.value?.pct_pass))
const deltaScore = computed(() => diferencia(actual.value?.global, anterior.value?.global))
// Lo que redondea a 0,0 no sube ni baja: se muestra como "sin cambio".
const sentido = (d: number | null) => (d === null ? null : Math.abs(d) < 0.05 ? 'igual' : d > 0 ? 'sube' : 'baja')

// Cifras principales: suben hasta su valor al cargar y al cambiar de día.
const passAnimado = usarConteo(computed(() => actual.value?.pct_pass ?? null))
const puntajeAnimado = usarConteo(computed(() => actual.value?.global ?? null), 700)
const cumplenAnimadas = usarConteo(computed(() => actual.value?.estados.OK ?? 0), 700)
const alertasAnimadas = usarConteo(computed(() => actual.value?.estados.ALERTA ?? 0), 700)
const fallasAnimadas = usarConteo(computed(() => actual.value?.estados.FALLA ?? 0), 700)
const tonoPass = (v: number | null | undefined) => (v == null ? undefined : v >= 85 ? 'bien' : v >= 70 ? 'aviso' : 'critico')
const tonoScore = (v: number | null | undefined) => (v == null ? undefined : v >= 99 ? 'bien' : v >= 97 ? 'aviso' : 'critico')

/** Variación frente al día anterior para las tarjetas: `subirEsBueno` decide el color. */
function variacion(d: number | null, subirEsBueno: boolean, sufijo: string): Variacion | null {
  if (d === null || !anterior.value) return null
  const direccion = sentido(d) ?? 'igual'
  const contra = `vs. ${corteCorto(anterior.value.fecha_corte)}`
  if (direccion === 'igual') return { texto: `Sin cambio ${contra}`, direccion, tono: 'neutro' }
  const bueno = (direccion === 'sube') === subirEsBueno
  return { texto: `${sufijo ? signo(d, sufijo) : (d > 0 ? '+' : '−') + Math.abs(d)} ${contra}`, direccion, tono: bueno ? 'bien' : 'critico' }
}
const delta = (estado: string) => diferencia(actual.value?.estados[estado] ?? 0, anterior.value ? anterior.value.estados[estado] ?? 0 : null)

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
// Tablas no certificadas por día: marcan el gráfico y van como columna en su vista de tabla.
const alertas = computed(() => lista.value.map((c) => Object.values(c.certificacion).filter((e) => e === 'NO_CERTIFICADO').length))

const filasMapa = computed(() =>
  TABLAS.map((t) => ({
    clave: t,
    nombre: NOMBRE_TABLA[t],
    color: COLOR_TABLA[t],
    estados: Object.fromEntries(lista.value.map((c) => [c.fecha_corte, c.certificacion[t]])),
    detalle: (d: string) => `puntaje de calidad ${pct(lista.value.find((c) => c.fecha_corte === d)?.por_tabla[t])}`,
  })),
)
function abrirValidaciones(fecha: string, tabla: string) {
  cortes.elegido = fecha
  router.push({ path: '/validaciones', query: { tabla } })
}
const DIMENSIONES = Object.keys(NOMBRE_DIMENSION)
const nombreEstado = (estado?: string) => ({ CERTIFICADO: 'bien', CERTIFICADO_CON_OBSERVACIONES: 'aviso', NO_CERTIFICADO: 'critico' } as Record<string, string>)[estado ?? ''] ?? 'neutro'
const actividad = computed(() => vivo.eventos.slice(0, 6))

const LECTURA: Clave[] = [
  { muestras: ['bien', 'aviso', 'critico'], texto: 'Cada sello es una tabla en el día elegido: Certificada, Con observaciones o No certificada. Las no certificadas no llegan a negocio (BUSINESS).' },
  { texto: '% de reglas que cumplen: de las reglas con datos, cuántas alcanzan su umbral. El puntaje de calidad, en cambio, pondera cada regla por su severidad.' },
  { muestras: ['punto', 'finde'], texto: 'En la tendencia, un punto rojo bajo el eje marca un día con alguna tabla no certificada; las franjas grises son fines de semana.' },
  { muestras: ['critico'], texto: 'En el mapa, cada cuadro es una tabla en un día; los no certificados llevan además un borde oscuro. Pasa el puntero por un cuadro para ver su detalle y haz clic para ver sus validaciones.' },
]
</script>

<template>
  <div class="pila">
    <EncabezadoSeccion
      modulo="resumen"
      titulo="Resumen"
      subtitulo="Calidad, privacidad y certificación de cada tabla en el día elegido."
      :lectura="LECTURA"
    />

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" forma="resumen" @reintentar="recargar">
      <template v-if="actual">
        <!-- Banda héroe: la respuesta del día, el indicador del backlog (PASS) y el sello de cada tabla -->
        <section class="hero" aria-label="El día en un vistazo">
          <div class="hero-arriba">
            <LecturaRapida :dia="actual.fecha_corte" :anterior="anterior?.fecha_corte ?? null" :certificacion="actual.certificacion" />
            <div class="instrumento">
              <div class="pass">
                <span class="etiqueta">% de reglas que cumplen (PASS)</span>
                <strong class="cifra" :class="tonoPass(actual.pct_pass)">{{ pct(passAnimado) }}</strong>
                <span v-if="deltaPass !== null && anterior" class="delta" :class="sentido(deltaPass)">
                  <component :is="{ sube: ArrowUpRight, baja: ArrowDownRight, igual: Minus }[sentido(deltaPass) ?? 'igual']" :size="15" :stroke-width="2.6" aria-hidden="true" />
                  <template v-if="sentido(deltaPass) === 'igual'">Sin cambio vs. {{ corteCorto(anterior.fecha_corte) }}</template>
                  <template v-else>{{ signo(deltaPass, ' pts') }} vs. {{ corteCorto(anterior.fecha_corte) }}</template>
                </span>
              </div>
              <Anillo :parte="certificadas" :total="TABLAS.length" etiqueta="tablas publicadas" :tamano="128" class="anillo-hero" />
            </div>
          </div>

          <div class="hero-sellos" data-recorrido="sellos">
            <div class="fila entre">
              <h2>Certificación de cada tabla</h2>
              <RouterLink to="/certificacion" class="enlace">Ver certificación</RouterLink>
            </div>
            <ul class="grilla-sellos">
              <li v-for="t in TABLAS" :key="t">
                <RouterLink to="/certificacion" class="sin-subrayado" :class="nombreEstado(actual.certificacion[t])">
                  <span class="disco" aria-hidden="true" />
                  <Sello :estado="actual.certificacion[t] ?? ''" :tabla="NOMBRE_TABLA[t]" :detalle="pct(actual.por_tabla[t])" :tamano="104" />
                </RouterLink>
              </li>
            </ul>
          </div>
        </section>

        <section class="indicadores" aria-label="Indicadores del día">
          <Kpi
            titulo="Puntaje de calidad"
            :valor="pct(puntajeAnimado)"
            :variacion="variacion(deltaScore, true, ' pts')"
            detalle="Ponderado por la severidad de cada regla"
            :tono="tonoScore(actual.global)"
            :icono="Gauge"
          />
          <Kpi
            titulo="Reglas que cumplen"
            :valor="String(Math.round(cumplenAnimadas ?? 0))"
            :variacion="variacion(delta('OK'), true, '')"
            :detalle="`De ${conDatos} con datos · llegan a su umbral`"
            tono="bien"
            :icono="CircleCheck"
          />
          <Kpi
            titulo="Reglas en alerta"
            :valor="String(Math.round(alertasAnimadas ?? 0))"
            :variacion="variacion(delta('ALERTA'), false, '')"
            detalle="Hasta 2 puntos bajo el umbral"
            :tono="actual.estados.ALERTA ? 'aviso' : 'bien'"
            :icono="TriangleAlert"
          />
          <Kpi
            titulo="Reglas que fallan"
            :valor="String(Math.round(fallasAnimadas ?? 0))"
            :variacion="variacion(delta('FALLA'), false, '')"
            detalle="Más de 2 puntos bajo el umbral"
            :tono="actual.estados.FALLA ? 'critico' : 'bien'"
            :icono="CircleX"
          />
        </section>

        <div class="dos-columnas">
          <section class="panel pila tendencia">
            <div class="fila entre">
              <h2>Tendencia diaria</h2>
              <div class="segmentos" role="group" aria-label="Indicador">
                <button type="button" :class="{ activo: metrica === 'pass' }" :aria-pressed="metrica === 'pass'" @click="metrica = 'pass'">% que cumple</button>
                <button type="button" :class="{ activo: metrica === 'score' }" :aria-pressed="metrica === 'score'" @click="metrica = 'score'">Puntaje</button>
              </div>
            </div>
            <GraficoTendencia
              :etiquetas="lista.map((c) => c.fecha_corte)"
              :series="series"
              :elegido="actual.fecha_corte"
              :alertas="alertas"
              :unidad="metrica === 'pass' ? '% de reglas que cumplen' : 'puntaje de calidad'"
              @elegir="(f) => (cortes.elegido = f)"
            />
            <p class="tenue pequeno">Puntos rojos: días con alguna tabla no certificada. Franjas grises: fin de semana.</p>
          </section>

          <section v-if="vivo.estado?.activo" class="panel pila actividad">
            <div class="fila entre">
              <h2><span class="icono-vivo" aria-hidden="true"><Activity :size="16" /></span> Actividad en vivo</h2>
              <button type="button" class="fantasma enlace" @click="vivo.panelAbierto = true">Ver todo</button>
            </div>
            <TransitionGroup v-if="actividad.length" tag="ol" name="evento" class="feed">
              <li v-for="e in actividad" :key="e.id" :class="e.tono">
                <span class="punto-feed" aria-hidden="true" />
                <div>
                  <strong>{{ e.titulo }}</strong>
                  <span class="tenue">{{ e.detalle }}</span>
                  <span class="tenue cuando">{{ relativo(e.cuando) }}</span>
                </div>
              </li>
            </TransitionGroup>
            <EstadoVacio
              v-else
              :icono="CalendarClock"
              titulo="Esperando el próximo archivo"
              texto="Aquí aparece cada archivo que llega, cada día que se evalúa y cada tabla que se certifica o se retiene."
            />
          </section>
        </div>

        <section class="panel pila mapa-panel">
          <div class="pila-chica">
            <h2>Mapa de certificación</h2>
            <p class="secundario pequeno">El sello de cada tabla, día por día, en todo el período.</p>
          </div>
          <MapaDias
            :dias="lista.map((c) => c.fecha_corte)"
            :filas="filasMapa"
            :elegido="actual.fecha_corte"
            :seleccionada="tablaElegida"
            seleccionable
            @elegir="abrirValidaciones"
            @seleccionar="(t) => (tablaElegida = t)"
          />
          <p class="tenue pequeno">Cada cuadro es un día: pasa el puntero (o llega con el teclado) para ver su detalle y haz clic para ver las validaciones de esa tabla ese día.</p>
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Dimensiones de {{ NOMBRE_TABLA[tablaElegida] }} · {{ corteCorto(actual.fecha_corte) }}</h2>
            <div class="segmentos" role="group" aria-label="Tabla">
              <button v-for="t in TABLAS" :key="t" type="button" :class="{ activo: t === tablaElegida }" :aria-pressed="t === tablaElegida" @click="tablaElegida = t">
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
          <p class="tenue pequeno">
            Escala de 80 % a 100 %, ponderada por la severidad de cada regla. Colores: verde desde 99 %, ámbar desde 97 % y
            rojo por debajo, igual que el puntaje de calidad. El % de reglas que cumplen usa otros límites: verde desde 85 % y
            ámbar desde 70 %.
          </p>
        </section>
      </template>
      <section v-else class="panel">
        <EstadoVacio
          :icono="CalendarClock"
          titulo="Todavía no hay días evaluados"
          texto="El resumen aparece cuando llegan los cinco archivos de un día y el motor termina de evaluarlo y certificarlo."
        />
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
/* ── banda héroe ─────────────────────────────────────────────────────────────── */
.hero {
  position: relative; isolation: isolate; overflow: hidden; display: grid; gap: 26px;
  padding: 30px 32px 28px; border-radius: var(--radio-grande);
  background: var(--degradado-hero); color: var(--hero-tinta);
  border: 1px solid var(--hero-borde);
  box-shadow: var(--elev-2);
  /* El anillo sobre el azul. */
  --anillo-pista: rgb(255 255 255 / 0.14);
  --anillo-arco: #7cb8ff;
  --anillo-tinta: #fff;
  --anillo-tinta-2: var(--hero-tinta-2);
}
/* Trama de puntos de tablero de control, que se apaga hacia la izquierda (solo decoración). */
.hero::before {
  content: ''; position: absolute; inset: 0; z-index: -1; pointer-events: none;
  background-image: radial-gradient(rgb(255 255 255 / 0.10) 1px, transparent 1.4px);
  background-size: 20px 20px;
  mask-image: linear-gradient(105deg, transparent 35%, #000 100%);
}
.hero :is(a, button, [tabindex]):focus-visible { outline-color: var(--hero-foco); }
.hero-arriba { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 28px 40px; align-items: start; }
/* El instrumento: un panel de vidrio oscuro, como el tablero de un control. */
.instrumento {
  display: flex; align-items: center; gap: 22px; padding: 20px 22px; border-radius: var(--radio);
  background: var(--hero-vidrio); border: 1px solid var(--hero-borde);
  box-shadow: inset 0 1px 0 rgb(255 255 255 / 0.06);
}
.pass { display: grid; justify-items: start; gap: 6px; }
.etiqueta { font-size: 13px; font-weight: 700; color: var(--hero-tinta-2); }
.cifra { font-size: var(--cifra-xl); font-weight: 800; letter-spacing: -0.05em; line-height: 0.95; font-variant-numeric: tabular-nums; color: #fff; }
.cifra.bien { color: var(--hero-bien); }
.cifra.aviso { color: var(--hero-aviso); }
.cifra.critico { color: var(--hero-critico); }
.delta {
  display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px 3px 7px; border-radius: 999px;
  font-size: 12.5px; font-weight: 700; background: rgb(0 0 0 / 0.22); color: var(--hero-tinta);
  font-variant-numeric: tabular-nums;
}
.delta.sube { color: var(--hero-bien); }
.delta.baja { color: var(--hero-critico); }

.hero-sellos { display: grid; gap: 16px; padding-top: 22px; border-top: 1px solid var(--hero-borde); }
.hero-sellos h2 { color: var(--hero-tinta); font-size: 16px; }
.enlace { font-weight: 700; font-size: 13.5px; }
.hero .enlace { color: var(--hero-tinta); text-decoration: underline; text-decoration-color: rgb(255 255 255 / 0.4); text-underline-offset: 3px; }
.hero .enlace:hover { text-decoration-color: #fff; }
.grilla-sellos { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px; }
.grilla-sellos li { display: grid; justify-items: center; align-items: start; }
.sin-subrayado {
  position: relative; display: grid; justify-items: center; align-content: start; width: 100%; color: inherit; text-decoration: none !important;
  border-radius: 16px; padding: 6px 4px; transition: transform 0.14s var(--ease-out);
}
.sin-subrayado:active { transform: scale(0.97); }
/* Disco claro detrás de cada sello: el timbre se lee como sobre papel. */
.disco {
  position: absolute; top: -6px; left: 50%; width: 128px; height: 128px; margin-left: -64px; border-radius: 50%; z-index: 0;
  background: radial-gradient(circle at 35% 30%, #ffffff 0%, #eef3fa 70%, #dfe7f3 100%);
  box-shadow: 0 10px 24px -12px rgb(0 0 0 / 0.55), inset 0 -2px 0 rgb(13 31 60 / 0.06);
}
.sin-subrayado :deep(.sello) { position: relative; z-index: 1; gap: 18px; width: 100% !important; align-content: start; }
/* El timbre usa los colores del tema claro (está sobre el disco claro) en los dos temas. */
.sin-subrayado :deep(.sello svg) {
  --bien-suave: #e3f5e3; --bien-texto: #006300; --aviso-suave: #fff3d4; --aviso-texto: #7a5200;
  --critico-suave: #fde8e8; --critico-texto: #a32020; --neutro-suave: #edf0f4; --tenue: #5f6b80;
  --bien: #0ca30c; --aviso: #fab219; --critico: #d03b3b;
  filter: none;
}
.sin-subrayado :deep(figcaption strong) { color: #fff; font-size: 15.5px; }
.sin-subrayado :deep(figcaption .tenue) { color: var(--hero-tinta-2); }
.sin-subrayado :deep(.leyenda.bien) { color: var(--hero-bien); }
.sin-subrayado :deep(.leyenda.aviso) { color: var(--hero-aviso); }
.sin-subrayado :deep(.leyenda.critico) { color: var(--hero-critico); }
.sin-subrayado :deep(.leyenda.neutro) { color: var(--hero-tinta-2); }

/* ── indicadores ─────────────────────────────────────────────────────────────── */
.indicadores { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }
.pequeno { font-size: 12.5px; }
.marca-c { color: var(--marca); }

.dos-columnas { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 16px; align-items: start; }
.dos-columnas > :only-child { grid-column: 1 / -1; }

/* ── actividad en vivo: línea de tiempo ──────────────────────────────────────── */
.actividad h2 { display: inline-flex; align-items: center; gap: 9px; }
.icono-vivo { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 9px; background: var(--bien-suave); color: var(--bien-texto); }
.actividad :deep(.estado-vacio) { padding: 20px 6px; }
.feed { position: relative; list-style: none; margin: 0; padding: 0; display: grid; gap: 14px; }
/* El hilo que une los eventos. */
.feed::before { content: ''; position: absolute; left: 5px; top: 8px; bottom: 8px; width: 2px; border-radius: 2px; background: var(--linea); }
.feed li { position: relative; display: grid; grid-template-columns: 12px 1fr; gap: 12px; }
.feed li > div { display: grid; gap: 1px; font-size: 12.5px; min-width: 0; }
.feed strong { font-size: 13px; }
.cuando { font-size: 11.5px; }
.punto-feed {
  --halo: var(--marca-suave);
  width: 12px; height: 12px; border-radius: 50%; margin-top: 3px; background: var(--marca);
  box-shadow: 0 0 0 3px var(--superficie);
}
.feed .bien .punto-feed { background: var(--bien); --halo: var(--bien-suave); }
.feed .aviso .punto-feed { background: var(--aviso); --halo: var(--aviso-suave); }
.feed .critico .punto-feed { background: var(--critico); --halo: var(--critico-suave); }
/* El evento más reciente lleva un halo de su color. */
.feed li:first-child .punto-feed { box-shadow: 0 0 0 3px var(--superficie), 0 0 0 6px var(--halo); }
/* Evento nuevo: entra desde arriba; los demás bajan para hacerle sitio. */
.evento-enter-active { transition: opacity 0.26s var(--ease-out), transform 0.26s var(--ease-out); }
.evento-enter-from { opacity: 0; transform: translateY(-10px); }
.evento-move { transition: transform 0.26s var(--ease-out); }

/* ── dimensiones ─────────────────────────────────────────────────────────────── */
.dimensiones { display: grid; grid-template-columns: 130px 1fr 72px; gap: 14px 16px; align-items: center; }
.nombre-dim { font-weight: 600; }
.barra.alta { height: 12px; }
.dimensiones strong { text-align: right; }

@media (max-width: 1250px) {
  .dos-columnas { grid-template-columns: 1fr; }
  .indicadores { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 1100px) {
  .hero-arriba { grid-template-columns: 1fr; }
  .instrumento { justify-content: space-between; }
}
@media (max-width: 760px) {
  .hero { padding: 22px 18px 20px; border-radius: var(--radio); gap: 20px; }
  .hero-arriba { gap: 20px; }
  .instrumento { padding: 16px; gap: 12px; }
  .cifra { font-size: 50px; }
  .instrumento :deep(.anillo-hero) { width: 96px !important; }
  .instrumento :deep(.anillo-hero svg) { width: 96px; height: 96px; }
  .hero-sellos { padding-top: 18px; }
  /* 3 + 2 sellos, la segunda fila centrada. */
  .grilla-sellos { grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 18px 6px; }
  .grilla-sellos li { grid-column: span 2; }
  .grilla-sellos li:nth-child(4) { grid-column: 2 / span 2; }
  .disco { width: 96px; height: 96px; margin-left: -48px; top: -2px; }
  .sin-subrayado :deep(.sello) { gap: 12px; }
  .sin-subrayado :deep(.sello svg) { width: 80px; height: 80px; }
  .sin-subrayado :deep(figcaption strong) { font-size: 14px; }
  .indicadores { gap: 10px; }
  .indicadores :deep(.kpi) { padding: 14px 13px 13px; }
  .indicadores :deep(.kpi .valor) { font-size: 30px; }
  .indicadores :deep(.kpi .titulo) { font-size: 12.5px; align-items: flex-start; }
  .indicadores :deep(.kpi .icono-kpi) { width: 26px; height: 26px; border-radius: 8px; }
  .dimensiones { grid-template-columns: 100px 1fr 60px; }
}
</style>
