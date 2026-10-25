<script setup lang="ts">
import { ArrowDownRight, ArrowUpRight, ListChecks, Minus } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import Sello from '@/componentes/Sello.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corteCorto, diaDeSemana, diaEnFrase, NOMBRE_TABLA, TABLAS } from '@/formato'
import { api } from '@/servicios/api'

/**
 * Lectura rápida del día: la respuesta, en lenguaje claro, a «¿puedo confiar en los datos de
 * este día?». Qué tablas llegaron a negocio, cuál se retuvo y por qué, y qué cambió frente al
 * día anterior. La primera frase sale del resumen; el motivo y los cambios, de la
 * certificación y la comparación del día (se piden aquí, sin cambiar la API).
 */
const props = defineProps<{ dia: string; anterior: string | null; certificacion: Record<string, string> }>()

type FichaTabla = {
  tabla: string
  calidad: { reglas_bloqueantes: string[] }
  privacidad: { hallazgos: { tipo: string; columna: string; bloqueante: boolean }[] }
}
type Regla = { id_regla: string; dimension: string; estado_a?: string; estado_b?: string }

const detalle = usarCarga(async () => {
  const dia = props.dia
  const [cert, comparacion] = await Promise.all([
    api<{ tablas: FichaTabla[] }>('/api/v1/certificacion', { params: { corte: dia } }),
    props.anterior
      ? api<{ reglas: Regla[] }>('/api/v1/validaciones/comparar', { params: { a: props.anterior, b: dia } })
      : Promise.resolve(null),
  ])
  return { dia, cert, comparacion }
}, [() => props.dia])
// Solo vale si es del día que se mira (al cambiar rápido de día puede llegar una respuesta vieja).
const delDia = computed(() => (detalle.datos.value?.dia === props.dia ? detalle.datos.value : null))

const estado = (t: string) => props.certificacion[t]
const retenidas = computed(() => TABLAS.filter((t) => estado(t) === 'NO_CERTIFICADO'))
const publicadas = computed(() => TABLAS.filter((t) => estado(t) && estado(t) !== 'NO_CERTIFICADO'))
const observadas = computed(() => TABLAS.filter((t) => estado(t) === 'CERTIFICADO_CON_OBSERVACIONES'))
const veredicto = computed(() =>
  retenidas.value.length ? 'NO_CERTIFICADO' : observadas.value.length ? 'CERTIFICADO_CON_OBSERVACIONES' : 'CERTIFICADO',
)

const lista = (nombres: string[]) =>
  nombres.length <= 1 ? (nombres[0] ?? '') : `${nombres.slice(0, -1).join(', ')} y ${nombres.at(-1)}`

const frase = computed(() => {
  const total = TABLAS.length
  const n = publicadas.value.length
  const que =
    n === total
      ? `las ${total} tablas llegaron a negocio${observadas.value.length ? '' : ' sin observaciones'}.`
      : n === 0
        ? 'ninguna tabla llegó a negocio.'
        : `${n} de ${total} tablas llegaron a negocio.`
  return `${diaEnFrase(props.dia)}: ${que}`
})

// Por qué se retuvo: en palabras de negocio según la dimensión de la regla que bloqueó.
const POR_QUE: Record<string, string> = {
  oportunidad: 'su archivo llegó tarde',
  volumetria: 'su volumen cambió fuera de lo normal',
  completitud: 'le faltan datos obligatorios',
  unicidad: 'tiene registros duplicados',
  validez: 'tiene valores con formato no válido',
  consistencia: 'tiene datos que no cuadran entre sí',
  integridad: 'tiene referencias a registros que no existen',
}
// Respaldo si la regla no viene en la comparación (primer día): el código va en su id (PER-COM-01).
const POR_CODIGO: Record<string, string> = {
  OPO: 'oportunidad', VOL: 'volumetria', COM: 'completitud', UNI: 'unicidad', VAL: 'validez', CON: 'consistencia', INT: 'integridad',
}
const MASCULINO = new Set(['vehiculo', 'siniestro', 'pago'])

function motivo(tabla: string): string | null {
  const ficha = delDia.value?.cert.tablas.find((f) => f.tabla === tabla)
  if (!ficha) return null
  const partes: string[] = []
  const fuga = ficha.privacidad.hallazgos.find((h) => h.bloqueante)
  if (fuga) {
    partes.push(fuga.tipo === 'PII_EN_CLARO' ? `aparecieron datos personales sin cifrar en ${fuga.columna}` : `${fuga.columna} llegó sin cifrar`)
  }
  const reglas = ficha.calidad.reglas_bloqueantes.filter((r) => r !== 'SIN_DATOS')
  if (reglas.length) {
    const dimensiones = [
      ...new Set(
        reglas.map(
          (id) => delDia.value?.comparacion?.reglas.find((r) => r.id_regla === id)?.dimension ?? POR_CODIGO[id.split('-')[1]] ?? '',
        ),
      ),
    ]
    const porque = dimensiones.slice(0, 2).map((d) => POR_QUE[d] ?? 'falló una regla grave')
    partes.push(`${lista(porque)} (${reglas.join(', ')})`)
  } else if (ficha.calidad.reglas_bloqueantes.includes('SIN_DATOS')) {
    partes.push('ninguna de sus reglas pudo evaluarse')
  }
  const retenida = MASCULINO.has(tabla) ? 'retenido' : 'retenida'
  return `${NOMBRE_TABLA[tabla]} quedó ${retenida} porque ${partes.length ? lista(partes) : 'no pasó el control'}.`
}

const explicacion = computed(() => {
  if (retenidas.value.length) {
    const frases = retenidas.value.slice(0, 3).map(motivo)
    if (frases.some((f) => f === null)) return null // todavía cargando el motivo
    const resto = retenidas.value.length - 3
    return frases.join(' ') + (resto > 0 ? ` Y ${resto} más: mira Certificación.` : '')
  }
  if (!observadas.value.length) return 'Todas pasaron el control de calidad y privacidad sin observaciones.'
  if (observadas.value.length === TABLAS.length) return 'Todas tienen observaciones que no impiden publicarlas.'
  const nombres = observadas.value.map((t) => NOMBRE_TABLA[t])
  return nombres.length === 1
    ? `${nombres[0]} tiene observaciones que no impiden publicarla.`
    : `${lista(nombres)} tienen observaciones que no impiden publicarlas.`
})

// Qué cambió frente al día anterior: reglas que subieron o bajaron de estado (Cumple < Alerta < Falla).
const RANGO: Record<string, number> = { OK: 0, ALERTA: 1, FALLA: 2 }
const cambios = computed(() => {
  const reglas = delDia.value?.comparacion?.reglas
  if (!reglas) return null
  let peor = 0
  let mejor = 0
  for (const r of reglas) {
    const a = RANGO[r.estado_a ?? '']
    const b = RANGO[r.estado_b ?? '']
    if (a === undefined || b === undefined) continue
    if (b > a) peor++
    else if (b < a) mejor++
  }
  return { peor, mejor }
})
const plural = (n: number, uno: string, varios: string) => `${n} ${n === 1 ? uno : varios}`
// Siguiente paso: las reglas que fallaron o, si la retuvo la privacidad, su ficha de certificación.
const accion = computed(() => {
  if (retenidas.value.length !== 1) {
    return retenidas.value.length
      ? { texto: 'Ver la certificación del día', a: { path: '/certificacion' } }
      : { texto: 'Ver las reglas del día', a: { path: '/validaciones' } }
  }
  const tabla = retenidas.value[0]
  const ficha = delDia.value?.cert.tablas.find((f) => f.tabla === tabla)
  const porPrivacidad = !!ficha && !ficha.calidad.reglas_bloqueantes.length
  return porPrivacidad
    ? { texto: `Ver la certificación de ${NOMBRE_TABLA[tabla]}`, a: { path: '/certificacion' } }
    : { texto: `Ver qué falló en ${NOMBRE_TABLA[tabla]}`, a: { path: '/validaciones', query: { tabla } } }
})
</script>

<template>
  <section class="panel lectura" :class="veredicto" aria-labelledby="lectura-titulo" data-recorrido="lectura">
    <Sello :estado="veredicto" :tabla="corteCorto(dia)" :tamano="88" decorativo class="sello-dia" />
    <div class="texto">
      <h2 id="lectura-titulo" class="rotulo">Lectura rápida</h2>
      <p class="frase">{{ frase }}</p>
      <p v-if="explicacion" class="explicacion">{{ explicacion }}</p>
      <span v-else class="esqueleto" style="width: min(460px, 90%); height: 15px; margin: 4px 0" aria-hidden="true" />
      <p v-if="anterior && cambios" class="cambios">
        <template v-if="cambios.peor || cambios.mejor">
          <RouterLink v-if="cambios.peor" :to="{ path: '/validaciones', query: { comparar: anterior } }" class="chip critico">
            <ArrowDownRight :size="14" :stroke-width="2.6" aria-hidden="true" />{{ plural(cambios.peor, 'regla empeoró', 'reglas empeoraron') }}
          </RouterLink>
          <span v-if="cambios.mejor" class="chip bien">
            <ArrowUpRight :size="14" :stroke-width="2.6" aria-hidden="true" />{{ plural(cambios.mejor, 'regla mejoró', 'reglas mejoraron') }}
          </span>
          <span class="tenue">frente al {{ diaDeSemana(anterior) }}</span>
        </template>
        <span v-else class="tenue sin-cambio"><Minus :size="14" aria-hidden="true" /> Ninguna regla cambió de estado frente al {{ diaDeSemana(anterior) }}.</span>
      </p>
    </div>
    <RouterLink :to="accion.a" class="boton accion"><ListChecks :size="16" aria-hidden="true" />{{ accion.texto }}</RouterLink>
  </section>
</template>

<style scoped>
.lectura {
  display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 6px 22px; align-items: center;
  padding: 18px 22px 18px 18px; border-left: 5px solid var(--bien);
}
.lectura.CERTIFICADO_CON_OBSERVACIONES { border-left-color: var(--aviso); }
.lectura.NO_CERTIFICADO { border-left-color: var(--critico); }
.sello-dia :deep(svg) { filter: none; }
.texto { display: grid; gap: 4px; min-width: 0; }
.rotulo { font-size: 12.5px; font-weight: 700; color: var(--tenue); letter-spacing: 0; }
.frase { font-size: 22px; font-weight: 800; line-height: 1.25; letter-spacing: -0.02em; text-wrap: balance; }
.explicacion { font-size: 15px; color: var(--tinta-2); max-width: 78ch; text-wrap: pretty; }
.cambios { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 8px; margin-top: 6px; font-size: 13px; }
.cambios .chip { font-size: 12.5px; padding: 3px 10px 3px 7px; }
a.chip { transition: filter 0.12s ease; }
.sin-cambio { display: inline-flex; align-items: center; gap: 6px; }
.accion { align-self: center; white-space: nowrap; color: var(--tinta); text-decoration: none; }
.accion:hover { border-color: var(--marca); color: var(--marca); text-decoration: none; }
@media (max-width: 900px) {
  .lectura { grid-template-columns: auto minmax(0, 1fr); padding: 16px; }
  .accion { grid-column: 2; justify-self: start; }
}
@media (max-width: 560px) {
  .lectura { grid-template-columns: 1fr; gap: 10px; }
  .sello-dia { display: none; }
  .accion { grid-column: 1; }
  .frase { font-size: 19px; }
}
</style>
