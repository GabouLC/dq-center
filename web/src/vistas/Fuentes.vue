<script setup lang="ts">
import { Clock, FileCheck2, FileX2, Rows3, ShieldCheck, Timer } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EncabezadoSeccion from '@/componentes/EncabezadoSeccion.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import EstadoVacio from '@/componentes/EstadoVacio.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, corteCorto, esFinDeSemana, hora, NOMBRE_TABLA, num, signo, TABLAS } from '@/formato'
import type { Clave } from '@/navegacion'
import { api } from '@/servicios/api'
import { useVivo } from '@/stores/vivo'

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

const vivo = useVivo()
const tabla = ref('persona')
const verTodo = ref(false)
const soloProblemas = ref(false)
const { datos, cargando, error, recargar } = usarCarga(() => api<Fuente[]>('/api/v1/fuentes'))
const fuente = computed(() => datos.value?.find((f) => f.tabla === tabla.value))
const exitosas = computed(() => fuente.value?.cargas.filter((c) => c.estado === 'EXITOSA') ?? [])
const rechazos = computed(() => fuente.value?.cargas.filter((c) => c.estado === 'RECHAZADA').length ?? 0)
const estructura = usarCarga(() => api<Estructura>(`/api/v1/fuentes/${tabla.value}/estructura`), [tabla])

// Límite de llegada: corte + 2 días a las 09:00 de Lima (14:00 UTC).
const limite = (fecha: string) => Date.parse(`${fecha}T14:00:00Z`) + 2 * 86400000
const horasDeHolgura = (c: Carga) => (limite(c.fecha_corte) - Date.parse(c.cargado_en)) / 3600000
const tarde = (c: Carga) => horasDeHolgura(c) < 0
// Lo normal es que llegue de madrugada el día siguiente; después de las 09:00 ya va con retraso.
const conRetraso = (c: Carga) => !tarde(c) && horasDeHolgura(c) < 24
const fueraDeRango = (c: Carga) => Math.abs(c.variacion_pct ?? 0) > 15
// Las incidencias de homologación son parte de la operación diaria; aquí cuentan rechazos, demoras y saltos de volumen.
const conProblema = (c: Carga) => c.estado !== 'EXITOSA' || tarde(c) || conRetraso(c) || fueraDeRango(c)

// Volumen diario: la escala arranca cerca del mínimo para que se vea el crecimiento.
const escalaVolumen = computed(() => {
  const filas = exitosas.value.map((c) => c.filas)
  const menor = Math.min(...filas, Infinity)
  const mayor = Math.max(...filas, 1)
  return { base: Math.max(0, menor - (mayor - menor) * 0.6 - 1), mayor }
})
const alturaVolumen = (c: Carga) => 8 + ((c.filas - escalaVolumen.value.base) / (escalaVolumen.value.mayor - escalaVolumen.value.base)) * 92

// Puntualidad: horas después de la medianoche del corte. El eje va de la madrugada
// del día siguiente (24 h) a las 64 h; el límite está en las 57 h.
const LIMITE_HORAS = 57
const horasTras = (c: Carga) => (Date.parse(c.cargado_en) - Date.parse(`${c.fecha_corte}T05:00:00Z`)) / 3600000
const alturaEje = (horas: number) => Math.min(100, Math.max(0, ((horas - 24) / 40) * 100))
const alturaLlegada = (c: Carga) => alturaEje(horasTras(c))

const cargasVisibles = computed(() => {
  const todas = [...(fuente.value?.cargas ?? [])].reverse().filter((c) => !soloProblemas.value || conProblema(c))
  return verTodo.value ? todas : todas.slice(0, 14)
})
const columnas = computed(() => {
  const cortes = estructura.datos.value?.cortes ?? []
  const desde = new Map<string, { tipo: string; desde: string }>()
  for (const c of cortes) for (const col of c.columnas) if (!desde.has(col.columna)) desde.set(col.columna, { tipo: col.tipo, desde: c.fecha_corte })
  return [...desde.entries()].map(([columna, v]) => ({ columna, ...v, nueva: v.desde !== cortes[0]?.fecha_corte }))
})

const LECTURA: Clave[] = [
  { muestras: ['marca', 'critico'], texto: 'Volumen diario: cada barra es un día; en rojo, una variación de más de ±15 % frente al día anterior. Las más claras son fines de semana.' },
  { muestras: ['limite'], texto: 'Hora de llegada: cada punto es un archivo; más arriba, más tarde. La línea roja punteada es el límite: dos días después del día de datos, a las 09:00.' },
  { muestras: ['bien', 'aviso', 'critico'], texto: 'Puntualidad: a tiempo, con retraso (menos de 24 h antes del límite) o tarde (después del límite).' },
  { texto: 'En Cargas, una fila roja es un archivo rechazado en la ingesta; una verde, el día que está llegando ahora.' },
]
</script>

<template>
  <div class="pila">
    <EncabezadoSeccion
      modulo="fuentes"
      titulo="Fuentes"
      subtitulo="Cada archivo que llegó a RAW: a qué hora, cuántas filas, si se rechazó y cuántos registros no se pudieron homologar."
      :lectura="LECTURA"
    >
      <div class="segmentos" role="group" aria-label="Tabla">
        <button v-for="t in TABLAS" :key="t" type="button" :aria-pressed="t === tabla" :class="{ activo: t === tabla }" @click="tabla = t">
          {{ NOMBRE_TABLA[t] }}
        </button>
      </div>
    </EncabezadoSeccion>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="fuente">
        <section class="panel resumen-fuente">
          <div>
            <h2>{{ NOMBRE_TABLA[fuente.tabla] }}</h2>
            <p class="secundario">{{ fuente.descripcion }}</p>
            <p class="tenue pequeno">Dueño: {{ fuente.dueno }} · dominio {{ fuente.dominio }}</p>
          </div>
          <div class="cifras">
            <span class="cifra-fuente estado-bien"><i class="icono-cifra" aria-hidden="true"><FileCheck2 :size="17" /></i><strong>{{ exitosas.length }}</strong> cargas exitosas</span>
            <span class="cifra-fuente" :class="rechazos ? 'estado-critico' : 'neutra'"><i class="icono-cifra" aria-hidden="true"><FileX2 :size="17" /></i><strong>{{ rechazos }}</strong> rechazadas</span>
            <span class="cifra-fuente" :class="exitosas.some(tarde) ? 'estado-critico' : 'estado-bien'"><i class="icono-cifra" aria-hidden="true"><Clock :size="17" /></i><strong>{{ exitosas.filter(tarde).length }}</strong> tarde</span>
          </div>
        </section>

        <div class="dos">
          <section class="panel pila">
            <div class="fila entre">
              <h2 class="fila"><Rows3 :size="18" class="marca-c" /> Volumen diario</h2>
              <span class="tenue pequeno">Rojo: variación de más de ±15 % contra el día anterior</span>
            </div>
            <p class="visualmente-oculto">El detalle de cada día está en la tabla Cargas.</p>
            <div class="mini" aria-hidden="true">
              <span
                v-for="c in exitosas"
                :key="c.archivo"
                class="barra-dia"
                :class="{ fuera: fueraDeRango(c), finde: esFinDeSemana(c.fecha_corte) }"
                :style="{ height: `${alturaVolumen(c)}%` }"
                :title="`${nombreCorte(c.fecha_corte)}: ${num(c.filas)} filas (${signo(c.variacion_pct)})`"
              />
            </div>
            <div class="eje-mini tenue">
              <span>{{ exitosas[0] ? corteCorto(exitosas[0].fecha_corte) : '' }} · {{ num(exitosas[0]?.filas) }} filas</span>
              <span>{{ exitosas.at(-1) ? corteCorto(exitosas.at(-1)!.fecha_corte) : '' }} · {{ num(exitosas.at(-1)?.filas) }} filas</span>
            </div>
          </section>

          <section class="panel pila">
            <div class="fila entre">
              <h2 class="fila"><Timer :size="18" class="marca-c" /> Hora de llegada</h2>
              <span class="tenue pequeno">Límite: dos días después del día de datos, 09:00</span>
            </div>
            <p class="visualmente-oculto">El detalle de cada día está en la tabla Cargas.</p>
            <div class="mini llegadas" aria-hidden="true">
              <span class="linea-limite" :style="{ bottom: `${alturaEje(LIMITE_HORAS)}%` }"><span>límite</span></span>
              <span
                v-for="(c, i) in exitosas"
                :key="c.archivo"
                class="punto-llegada"
                :class="{ tarde: tarde(c), justo: conRetraso(c) }"
                :style="{ bottom: `${alturaLlegada(c)}%`, left: `${((i + 0.5) / exitosas.length) * 100}%` }"
                :title="`${nombreCorte(c.fecha_corte)}: llegó ${hora(c.cargado_en)}${tarde(c) ? ` · ${Math.round(-horasDeHolgura(c))} h tarde` : ''}`"
              />
            </div>
            <div class="eje-mini tenue"><span>Día siguiente, madrugada</span><span>Más arriba, más tarde</span></div>
            <p class="leyenda-llegada">
              <span><i class="a-tiempo" /> A tiempo: antes de las 09:00 del día siguiente</span>
              <span><i class="justo" /> Con retraso: menos de 24 h antes del límite</span>
              <span><i class="tarde" /> Tarde: después del límite</span>
            </p>
          </section>
        </div>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Cargas</h2>
            <div class="fila filtros">
              <label class="interruptor"><input v-model="soloProblemas" type="checkbox" /> Solo con problemas</label>
              <button type="button" class="fantasma" @click="verTodo = !verTodo">{{ verTodo ? 'Ver las últimas 14' : 'Ver todas' }}</button>
            </div>
          </div>
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr><th>Día</th><th>Archivo</th><th>Llegada (Lima)</th><th>Puntualidad</th><th class="der">Filas</th><th class="der">Variación</th><th>Estado</th><th class="der">Incidencias</th><th>Detalle</th></tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in cargasVisibles"
                  :key="c.archivo"
                  class="con-acento"
                  :class="{
                    rechazada: c.estado === 'RECHAZADA',
                    llegando: c.fecha_corte === vivo.estado?.corte_en_curso,
                    'estado-critico': c.estado === 'RECHAZADA' || (c.estado === 'EXITOSA' && tarde(c)),
                    'estado-aviso': c.estado === 'EXITOSA' && !tarde(c) && (conRetraso(c) || fueraDeRango(c)),
                    'estado-bien': c.fecha_corte === vivo.estado?.corte_en_curso && c.estado === 'EXITOSA',
                  }"
                >
                  <td><strong>{{ corteCorto(c.fecha_corte) }}</strong></td>
                  <td class="mono">{{ c.archivo }}</td>
                  <td>{{ hora(c.cargado_en) }}</td>
                  <td>
                    <span v-if="c.estado !== 'EXITOSA'" class="tenue">—</span>
                    <span v-else-if="tarde(c)" class="chip critico"><Clock :size="12" /> {{ Math.round(-horasDeHolgura(c)) }} h tarde</span>
                    <span v-else-if="conRetraso(c)" class="chip aviso"><Clock :size="12" /> con retraso</span>
                    <span v-else class="chip bien"><Clock :size="12" /> a tiempo</span>
                  </td>
                  <td class="der num">{{ num(c.filas) }}</td>
                  <td class="der num" :class="{ 'texto-critico': fueraDeRango(c) }">{{ c.variacion_pct === null ? '—' : signo(c.variacion_pct) }}</td>
                  <td><EstadoChip :estado="c.estado" /></td>
                  <td class="der num">{{ c.incidencias === null ? '—' : num(c.incidencias) }}</td>
                  <td class="pequeno">{{ c.detalle ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <EstadoVacio
            v-if="!cargasVisibles.length"
            :tono="soloProblemas ? 'bien' : 'neutro'"
            :icono="soloProblemas ? ShieldCheck : FileCheck2"
            :titulo="soloProblemas ? 'Ninguna carga con problemas' : 'Todavía no llegó ningún archivo'"
            :texto="soloProblemas
              ? 'Todos los archivos de esta tabla llegaron a tiempo, completos y sin saltos de volumen. Quita el filtro para verlos.'
              : 'Cada archivo que llegue a RAW aparecerá aquí con su hora, sus filas y su estado.'"
          />
        </section>
      </template>

      <section class="panel pila">
        <h2>Estructura en MASTER</h2>
        <BloqueCarga :cargando="estructura.cargando.value" :error="estructura.error.value" :vacio="!estructura.datos.value" @reintentar="estructura.recargar">
          <div class="tabla-envoltura">
            <table>
              <thead><tr><th>Columna</th><th>Tipo</th><th>Presente desde</th></tr></thead>
              <tbody>
                <tr v-for="c in columnas" :key="c.columna">
                  <td><strong>{{ c.columna }}</strong></td>
                  <td><span class="chip" :class="{ sello: c.tipo === 'BYTES' }">{{ c.tipo === 'BYTES' ? 'BYTES · cifrado' : c.tipo }}</span></td>
                  <td>
                    <span v-if="c.nueva" class="chip aviso">nueva desde el {{ corteCorto(c.desde) }}</span>
                    <span v-else class="tenue">todo el período</span>
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
.cifras { display: flex; gap: 12px; flex-wrap: wrap; }
/* Cada cifra en su baldosa: mosaico del ícono teñido por su estado y el número grande. */
.cifra-fuente {
  display: flex; align-items: center; gap: 9px; padding: 10px 16px 10px 10px; border-radius: 14px;
  background: var(--superficie-2); border: 1px solid var(--linea); font-size: 13px; color: var(--tinta-2);
}
.icono-cifra { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 10px; background: var(--acento-suave, var(--neutro-suave)); color: var(--acento, var(--tenue)); font-style: normal; }
.cifra-fuente.estado-bien .icono-cifra { color: var(--bien-texto); }
.cifra-fuente.estado-critico .icono-cifra { color: var(--critico-texto); }
.cifra-fuente strong { font-size: 22px; font-weight: 800; color: var(--tinta); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
.bien { color: var(--bien); }
.critico { color: var(--critico); }
.texto-critico { color: var(--critico-texto); font-weight: 800; }
.marca-c { color: var(--marca); }
.pequeno { font-size: 12.5px; }
.dos { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.mini { position: relative; display: flex; align-items: flex-end; gap: 1px; height: 140px; padding: 6px; border-radius: 10px; background: var(--superficie-2); }
.barra-dia { flex: 1; min-width: 1px; border-radius: 2px 2px 0 0; background: var(--s1); transition: height 0.5s ease; }
.barra-dia.finde { opacity: 0.55; }
.barra-dia.fuera { background: var(--critico); opacity: 1; }
.barra-dia:hover { filter: brightness(1.2); }
.eje-mini { display: flex; justify-content: space-between; font-size: 11.5px; }
.llegadas { display: block; }
.punto-llegada { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: var(--s1); transform: translate(-50%, 50%); }
.punto-llegada.justo { background: var(--aviso); }
.punto-llegada.tarde { background: var(--critico); width: 9px; height: 9px; }
.linea-limite { position: absolute; left: 6px; right: 6px; border-top: 2px dashed var(--critico); }
.linea-limite span { position: absolute; right: 0; top: -18px; font-size: 11px; font-weight: 700; color: var(--critico-texto); }
.filtros { gap: 10px; }
.interruptor { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--tinta-2); }
.leyenda-llegada { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--tinta-2); }
.leyenda-llegada span { display: inline-flex; align-items: center; gap: 6px; }
.leyenda-llegada i { width: 8px; height: 8px; border-radius: 50%; background: var(--s1); }
.leyenda-llegada i.justo { background: var(--aviso); }
.leyenda-llegada i.tarde { background: var(--critico); }
.rechazada { background: var(--critico-suave); }
.llegando { background: var(--bien-suave); }
.resumen-fuente { background: linear-gradient(100deg, color-mix(in srgb, var(--grupo-origen) 6%, var(--superficie)) 0, var(--superficie) 60%); }
.mini { border: 1px solid var(--linea); }
@media (max-width: 1000px) { .dos { grid-template-columns: 1fr; } }
</style>
