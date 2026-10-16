<script setup lang="ts">
import { EyeOff, GitCompareArrows, Lock, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import BarraCumplimiento from '@/componentes/BarraCumplimiento.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, corteCorto, NOMBRE_DIMENSION, NOMBRE_TABLA, num, pct, signo, TABLAS } from '@/formato'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'

type Regla = {
  id_regla: string
  tabla: string
  dominio: string
  nivel: string
  dimension: string
  severidad: string
  umbral: number
  universo: number
  cumplimiento: number | null
  estado: string
  fallidos: number
  descripcion: string | null
  definicion: Record<string, unknown>
}
type Comparacion = {
  id_regla: string
  tabla: string
  cumplimiento_a: number | null
  cumplimiento_b: number | null
  estado_a: string
  estado_b: string
  delta: number | null
  empeoro: boolean
}
type Fallidos = { total: number; muestras: { llave: string; fila: Record<string, unknown> | null }[]; campos_restringidos: string[] }

const cortes = useCortes()
const ruta = useRoute()
const filtroTabla = ref(String(ruta.query.tabla ?? ''))
const filtroNivel = ref('')
const filtroEstado = ref('')
const compararCon = ref('')
// Atajos para comparar: el día anterior, una semana antes y el inicio del período.
const atajos = computed(() => {
  const i = cortes.lista.findIndex((c) => c.fecha_corte === cortes.elegido)
  return [
    { nombre: 'Día anterior', k: i - 1 },
    { nombre: 'Hace 7 días', k: i - 7 },
    { nombre: 'Inicio del período', k: 0 },
  ].flatMap((a) => (a.k >= 0 && a.k < i ? [{ nombre: a.nombre, fecha: cortes.lista[a.k].fecha_corte }] : []))
})
const elegida = ref<Regla | null>(null)

const { datos, cargando, error, recargar } = usarCarga(
  () => api<{ reglas: Regla[] }>('/api/v1/validaciones', { params: { corte: cortes.elegido } }),
  [() => cortes.elegido],
)
const deLaTabla = computed(() => (datos.value?.reglas ?? []).filter((r) => !filtroTabla.value || r.tabla === filtroTabla.value))
const reglas = computed(() =>
  deLaTabla.value.filter((r) => (!filtroNivel.value || r.nivel === filtroNivel.value) && (!filtroEstado.value || r.estado === filtroEstado.value)),
)
const cuenta = (campo: 'estado' | 'nivel', valor: string) => deLaTabla.value.filter((r) => r[campo] === valor).length
const ESTADOS = [['', 'Todos'], ['FALLA', 'FAIL'], ['ALERTA', 'Alerta'], ['OK', 'PASS'], ['SIN_DATOS', 'Sin datos']]
const NIVELES = [['', 'Todos'], ['N1', 'N1 básico'], ['N2', 'N2 negocio'], ['N3', 'N3 carga']]

const comparacion = usarCarga(
  () =>
    compararCon.value && cortes.elegido
      ? api<{ reglas: Comparacion[] }>('/api/v1/validaciones/comparar', { params: { a: compararCon.value, b: cortes.elegido } })
      : Promise.resolve(null),
  [compararCon, () => cortes.elegido],
)
const empeoradas = computed(() => (comparacion.datos.value?.reglas ?? []).filter((r) => r.empeoro))

const fallidos = ref<Fallidos | null>(null)
const errorFallidos = ref<string | null>(null)
watch([elegida, () => cortes.elegido], async ([regla]) => {
  fallidos.value = null
  errorFallidos.value = null
  if (!regla || !regla.fallidos) return
  try {
    fallidos.value = await api<Fallidos>(`/api/v1/validaciones/${regla.id_regla}/${regla.tabla}/fallidos`, {
      params: { corte: cortes.elegido, limite: 10 },
    })
  } catch (e) {
    errorFallidos.value = e instanceof Error ? e.message : String(e)
  }
})
// fecha_corte es la misma en toda la muestra: no hace falta repetirla.
const columnas = computed(() =>
  Object.keys(fallidos.value?.muestras.find((m) => m.fila)?.fila ?? {}).filter((c) => c !== 'fecha_corte'),
)
const valor = (v: unknown) => (v === null || v === undefined ? '∅' : String(v))
const oculto = (v: unknown) => String(v).startsWith('••••')
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Validaciones</h1>
        <p>Cada regla del corte contra su umbral (la marca vertical). Primero las más graves; elige una para ver sus registros fallidos.</p>
      </div>
      <label class="fila comparar">
        <GitCompareArrows :size="17" />
        <select v-model="compararCon" aria-label="Comparar con otro corte">
          <option value="">Comparar con otro día…</option>
          <optgroup label="Atajos">
            <option v-for="a in atajos" :key="a.fecha" :value="a.fecha">{{ a.nombre }} · {{ corteCorto(a.fecha) }}</option>
          </optgroup>
          <optgroup label="Todos los días">
            <option v-for="c in cortes.lista.filter((x) => x.fecha_corte !== cortes.elegido)" :key="c.fecha_corte" :value="c.fecha_corte">
              {{ nombreCorte(c.fecha_corte) }}
            </option>
          </optgroup>
        </select>
      </label>
    </div>

    <div class="filtros">
      <div class="segmentos" role="group" aria-label="Tabla">
        <button type="button" :class="{ activo: !filtroTabla }" @click="filtroTabla = ''">Todas</button>
        <button v-for="t in TABLAS" :key="t" type="button" :class="{ activo: filtroTabla === t }" @click="filtroTabla = t">{{ NOMBRE_TABLA[t] }}</button>
      </div>
      <div class="segmentos" role="group" aria-label="Estado">
        <button v-for="[v, n] in ESTADOS" :key="v" type="button" :class="{ activo: filtroEstado === v }" @click="filtroEstado = v">
          {{ n }} <span v-if="v" class="cuenta">{{ cuenta('estado', v) }}</span>
        </button>
      </div>
      <div class="segmentos" role="group" aria-label="Nivel">
        <button v-for="[v, n] in NIVELES" :key="v" type="button" :class="{ activo: filtroNivel === v }" @click="filtroNivel = v">
          {{ n }} <span v-if="v" class="cuenta">{{ cuenta('nivel', v) }}</span>
        </button>
      </div>
    </div>

    <section v-if="compararCon" class="panel pila">
      <div class="fila entre">
        <h2>Qué empeoró de {{ nombreCorte(compararCon) }} a {{ nombreCorte(cortes.elegido ?? '') }}</h2>
        <button type="button" class="fantasma" @click="compararCon = ''"><X :size="16" /> Cerrar</button>
      </div>
      <BloqueCarga :cargando="comparacion.cargando.value" :error="comparacion.error.value" :vacio="!comparacion.datos.value" @reintentar="comparacion.recargar">
        <p v-if="!empeoradas.length" class="aviso-caja bien">Ninguna regla empeoró entre esos cortes.</p>
        <div v-else class="tabla-envoltura">
          <table>
            <thead>
              <tr><th>Regla</th><th>Tabla</th><th class="der">Antes</th><th class="der">Ahora</th><th class="der">Cambio</th><th>Estado</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in empeoradas" :key="r.id_regla + r.tabla">
                <td class="id">{{ r.id_regla }}</td>
                <td>{{ NOMBRE_TABLA[r.tabla] }}</td>
                <td class="der num">{{ pct(r.cumplimiento_a) }}</td>
                <td class="der num">{{ pct(r.cumplimiento_b) }}</td>
                <td class="der num baja">{{ signo(r.delta, ' pts') }}</td>
                <td><span class="fila nowrap"><EstadoChip :estado="r.estado_a" /> → <EstadoChip :estado="r.estado_b" /></span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </BloqueCarga>
    </section>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="panel lista">
        <div class="tabla-envoltura">
          <table>
            <thead>
              <tr>
                <th>Regla</th><th>Tabla</th><th>Nivel</th><th>Dimensión</th><th>Severidad</th>
                <th class="ancho-barra">Cumplimiento vs. umbral</th><th>Estado</th><th class="der">Fallidos</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in reglas"
                :key="r.id_regla + r.tabla"
                class="clicable"
                :class="{ seleccionada: elegida?.id_regla === r.id_regla && elegida?.tabla === r.tabla }"
                tabindex="0"
                @click="elegida = r"
                @keydown.enter="elegida = r"
              >
                <td class="id">{{ r.id_regla }}</td>
                <td>{{ NOMBRE_TABLA[r.tabla] }}</td>
                <td><span class="chip marca">{{ r.nivel }}</span></td>
                <td>{{ NOMBRE_DIMENSION[r.dimension] }}</td>
                <td><span class="severidad" :class="r.severidad">{{ r.severidad }}</span></td>
                <td class="ancho-barra"><BarraCumplimiento :valor="r.cumplimiento" :umbral="r.umbral" :estado="r.estado" /></td>
                <td><EstadoChip :estado="r.estado" /></td>
                <td class="der num">{{ num(r.fallidos) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-if="!reglas.length" class="tenue vacio">Ninguna regla con esos filtros. Prueba con "Todos".</p>
      </section>
    </BloqueCarga>

    <Transition name="cajon">
      <aside v-if="elegida" class="cajon" aria-label="Detalle de la regla">
        <div class="fila entre">
          <div>
            <span class="tenue pequeno">{{ elegida.dominio }} · {{ NOMBRE_TABLA[elegida.tabla] }} · {{ elegida.nivel }}</span>
            <h2 class="titulo-cajon">{{ elegida.id_regla }}</h2>
          </div>
          <button type="button" class="icono fantasma" aria-label="Cerrar" @click="elegida = null"><X :size="18" /></button>
        </div>
        <p v-if="elegida.descripcion">{{ elegida.descripcion }}</p>
        <div class="fila">
          <EstadoChip :estado="elegida.estado" />
          <strong class="num grande">{{ pct(elegida.cumplimiento) }}</strong>
          <span class="tenue">umbral {{ pct(elegida.umbral) }}</span>
        </div>
        <BarraCumplimiento :valor="elegida.cumplimiento" :umbral="elegida.umbral" :estado="elegida.estado" />
        <dl class="definicion">
          <dt>Universo</dt><dd class="num">{{ num(elegida.universo) }} filas · {{ num(elegida.fallidos) }} fallidas</dd>
          <template v-for="(v, k) in elegida.definicion" :key="k">
            <dt>{{ String(k).replace('_', ' ') }}</dt>
            <dd><code>{{ Array.isArray(v) ? v.join(', ') : v }}</code></dd>
          </template>
        </dl>

        <template v-if="elegida.fallidos">
          <h3>Registros fallidos</h3>
          <p v-if="errorFallidos" class="aviso-caja error">{{ errorFallidos }}</p>
          <p v-else-if="!fallidos" class="tenue">Cargando…</p>
          <template v-else>
            <p v-if="fallidos.campos_restringidos.length" class="aviso-caja">
              <EyeOff :size="17" />
              <span>Tu rol no puede ver {{ fallidos.campos_restringidos.join(', ') }}: aparecen ocultos y el acceso quedó registrado.</span>
            </p>
            <p v-if="!columnas.length" class="aviso-caja info">Esta regla evalúa la carga completa: el detalle está en Fuentes.</p>
            <div v-else class="tabla-envoltura muestra">
              <table>
                <thead><tr><th v-for="c in columnas" :key="c">{{ c }}</th></tr></thead>
                <tbody>
                  <tr v-for="m in fallidos.muestras.filter((x) => x.fila)" :key="m.llave">
                    <td v-for="c in columnas" :key="c">
                      <span v-if="oculto(m.fila?.[c])" class="chip sello"><Lock :size="11" />{{ String(m.fila?.[c]).replace('•••• ', '') }}</span>
                      <template v-else>{{ valor(m.fila?.[c]) }}</template>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p class="tenue pequeno">{{ num(fallidos.total) }} registros fallidos en total; se muestran hasta 10.</p>
          </template>
        </template>
      </aside>
    </Transition>
    <div v-if="elegida" class="velo" @click="elegida = null" />
  </div>
</template>

<style scoped>
.comparar { gap: 8px; color: var(--tinta-2); }
.filtros { display: flex; gap: 10px; flex-wrap: wrap; }
.lista { padding: 6px 8px; }
.id { font-weight: 800; white-space: nowrap; letter-spacing: -0.01em; }
.ancho-barra { min-width: 220px; }
.severidad { font-size: 12px; font-weight: 800; color: var(--tinta-2); }
.severidad.CRITICA { color: var(--critico-texto); }
.severidad.ALTA { color: var(--aviso-texto); }
.baja { color: var(--critico-texto); font-weight: 700; }
.nowrap { flex-wrap: nowrap; }
.vacio { padding: 18px; }
.pequeno { font-size: 12.5px; }
.cajon {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(520px, 100vw);
  background: var(--superficie);
  border-left: 1px solid var(--linea);
  box-shadow: var(--sombra-alta);
  z-index: 40;
  padding: 22px;
  overflow-y: auto;
  display: grid;
  gap: 14px;
  align-content: start;
}
.velo { position: fixed; inset: 0; background: rgb(8 16 28 / 0.28); z-index: 35; }
.titulo-cajon { font-size: 22px; font-weight: 800; }
.grande { font-size: 22px; font-weight: 800; }
.definicion { display: grid; grid-template-columns: max-content 1fr; gap: 6px 14px; margin: 0; font-size: 13px; padding: 12px; background: var(--superficie-2); border-radius: 10px; }
.definicion dt { color: var(--tenue); font-weight: 600; text-transform: capitalize; }
.definicion dd { margin: 0; overflow-wrap: anywhere; }
.muestra td { font-size: 12.5px; white-space: nowrap; }
.cajon-enter-active, .cajon-leave-active { transition: transform 0.22s cubic-bezier(0.2, 0.8, 0.2, 1); }
.cajon-enter-from, .cajon-leave-to { transform: translateX(100%); }
</style>
