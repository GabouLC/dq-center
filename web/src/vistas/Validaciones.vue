<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BarraCumplimiento from '@/componentes/BarraCumplimiento.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, NOMBRE_DIMENSION, NOMBRE_TABLA, num, pct, signo, TABLAS } from '@/formato'
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
const filtroTabla = ref('')
const filtroNivel = ref('')
const filtroEstado = ref('')
const compararCon = ref('')
const elegida = ref<Regla | null>(null)

const { datos, cargando, error, recargar } = usarCarga(
  () => api<{ reglas: Regla[] }>('/api/v1/validaciones', { params: { corte: cortes.elegido } }),
  [() => cortes.elegido],
)
const reglas = computed(() =>
  (datos.value?.reglas ?? []).filter(
    (r) =>
      (!filtroTabla.value || r.tabla === filtroTabla.value) &&
      (!filtroNivel.value || r.nivel === filtroNivel.value) &&
      (!filtroEstado.value || r.estado === filtroEstado.value),
  ),
)

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
  if (!regla || !regla.fallidos || regla.tabla === undefined) return
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
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Validaciones</h1>
        <p class="muted">Cada regla del corte con su cumplimiento contra el umbral. Primero las más graves.</p>
      </div>
      <div class="fila">
        <select v-model="filtroTabla" aria-label="Tabla">
          <option value="">Todas las tablas</option>
          <option v-for="t in TABLAS" :key="t" :value="t">{{ NOMBRE_TABLA[t] }}</option>
        </select>
        <select v-model="filtroNivel" aria-label="Nivel">
          <option value="">Todos los niveles</option>
          <option value="N1">N1 · básico</option>
          <option value="N2">N2 · negocio</option>
          <option value="N3">N3 · carga</option>
        </select>
        <select v-model="filtroEstado" aria-label="Estado">
          <option value="">Todos los estados</option>
          <option value="FALLA">FAIL</option>
          <option value="ALERTA">Alerta</option>
          <option value="OK">PASS</option>
          <option value="SIN_DATOS">Sin datos</option>
        </select>
        <select v-model="compararCon" aria-label="Comparar con">
          <option value="">Comparar con…</option>
          <option v-for="c in cortes.lista.filter((x) => x.fecha_corte !== cortes.elegido)" :key="c.fecha_corte" :value="c.fecha_corte">
            {{ nombreCorte(c.fecha_corte) }}
          </option>
        </select>
      </div>
    </div>

    <section v-if="compararCon" class="tarjeta pila">
      <div class="fila entre">
        <h2>Qué empeoró de {{ nombreCorte(compararCon) }} a {{ nombreCorte(cortes.elegido ?? '') }}</h2>
        <button type="button" @click="compararCon = ''">Cerrar comparación</button>
      </div>
      <BloqueCarga :cargando="comparacion.cargando.value" :error="comparacion.error.value" :vacio="!comparacion.datos.value" @reintentar="comparacion.recargar">
        <p v-if="!empeoradas.length" class="muted">Ninguna regla empeoró.</p>
        <div v-else class="tabla-envoltura">
          <table>
            <thead>
              <tr><th>Regla</th><th>Tabla</th><th class="der">Antes</th><th class="der">Ahora</th><th class="der">Cambio</th><th>Estado</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in empeoradas" :key="r.id_regla + r.tabla">
                <td class="mono">{{ r.id_regla }}</td>
                <td>{{ NOMBRE_TABLA[r.tabla] }}</td>
                <td class="der num">{{ pct(r.cumplimiento_a) }}</td>
                <td class="der num">{{ pct(r.cumplimiento_b) }}</td>
                <td class="der num falla-texto">{{ signo(r.delta, ' pts') }}</td>
                <td class="fila"><EstadoChip :estado="r.estado_a" /> → <EstadoChip :estado="r.estado_b" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </BloqueCarga>
    </section>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <div class="disposicion" :class="{ con_panel: elegida }">
        <section class="tarjeta tabla-envoltura">
          <table>
            <thead>
              <tr>
                <th>Regla</th><th>Tabla</th><th>Nivel</th><th>Dimensión</th><th>Severidad</th>
                <th>Cumplimiento</th><th>Estado</th><th class="der">Fallidos</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="r in reglas"
                :key="r.id_regla + r.tabla"
                class="clicable"
                :class="{ seleccionada: elegida?.id_regla === r.id_regla && elegida?.tabla === r.tabla }"
                @click="elegida = r"
              >
                <td class="mono">{{ r.id_regla }}</td>
                <td>{{ NOMBRE_TABLA[r.tabla] }}</td>
                <td>{{ r.nivel }}</td>
                <td>{{ NOMBRE_DIMENSION[r.dimension] }}</td>
                <td>{{ r.severidad }}</td>
                <td class="ancho-barra"><BarraCumplimiento :valor="r.cumplimiento" :umbral="r.umbral" :estado="r.estado" /></td>
                <td><EstadoChip :estado="r.estado" /></td>
                <td class="der num">{{ num(r.fallidos) }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="!reglas.length" class="muted vacio">Ninguna regla con esos filtros.</p>
        </section>

        <aside v-if="elegida" class="tarjeta pila panel" aria-label="Detalle de la regla">
          <div class="fila entre">
            <h2 class="mono">{{ elegida.id_regla }}</h2>
            <button type="button" aria-label="Cerrar" @click="elegida = null">✕</button>
          </div>
          <div class="fila"><EstadoChip :estado="elegida.estado" /><span class="muted">{{ elegida.dominio }} · {{ NOMBRE_TABLA[elegida.tabla] }} · {{ elegida.nivel }}</span></div>
          <dl class="definicion">
            <dt>Cumplimiento</dt><dd class="num">{{ pct(elegida.cumplimiento) }} (umbral {{ pct(elegida.umbral) }})</dd>
            <dt>Universo</dt><dd class="num">{{ num(elegida.universo) }} filas · {{ num(elegida.fallidos) }} fallidas</dd>
            <template v-for="(v, k) in elegida.definicion" :key="k">
              <dt class="capital">{{ String(k).replace('_', ' ') }}</dt>
              <dd><code>{{ Array.isArray(v) ? v.join(', ') : v }}</code></dd>
            </template>
          </dl>
          <template v-if="elegida.fallidos">
            <h3>Muestra de registros fallidos</h3>
            <p v-if="errorFallidos" class="aviso error">{{ errorFallidos }}</p>
            <p v-else-if="!fallidos" class="muted">Cargando…</p>
            <template v-else>
              <p v-if="fallidos.campos_restringidos.length" class="aviso">
                Tu rol no puede ver {{ fallidos.campos_restringidos.join(', ') }}: aparecen ocultos y el acceso quedó registrado.
              </p>
              <p v-if="!columnas.length" class="muted">
                Esta regla evalúa la carga completa: el detalle está en Fuentes.
              </p>
              <div v-else class="tabla-envoltura muestra">
                <table>
                  <thead><tr><th v-for="c in columnas" :key="c">{{ c }}</th></tr></thead>
                  <tbody>
                    <tr v-for="m in fallidos.muestras.filter((x) => x.fila)" :key="m.llave">
                      <td v-for="c in columnas" :key="c" :class="{ oculto: String(m.fila?.[c]).startsWith('••••') }">{{ valor(m.fila?.[c]) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <p class="muted nota">{{ num(fallidos.total) }} registros fallidos en total; se muestran hasta 10.</p>
            </template>
          </template>
        </aside>
      </div>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.disposicion { display: grid; gap: 16px; }
.disposicion.con_panel { grid-template-columns: minmax(0, 1fr) minmax(320px, 420px); align-items: start; }
.ancho-barra { min-width: 190px; }
td.mono { white-space: nowrap; }
.capital { text-transform: capitalize; }
.der { text-align: right; }
.vacio { padding: 16px; }
.panel { position: sticky; top: 72px; max-height: calc(100vh - 96px); overflow: auto; }
.definicion { display: grid; grid-template-columns: max-content 1fr; gap: 6px 12px; margin: 0; font-size: 13px; }
.definicion dt { color: var(--muted); }
.definicion dd { margin: 0; overflow-wrap: anywhere; }
.muestra td { font-size: 12.5px; white-space: nowrap; }
.oculto { color: var(--cifrado); font-style: italic; }
.falla-texto { color: var(--falla); }
.nota { font-size: 12px; }
@media (max-width: 1100px) {
  .disposicion.con_panel { grid-template-columns: 1fr; }
  .panel { position: static; max-height: none; }
}
</style>
