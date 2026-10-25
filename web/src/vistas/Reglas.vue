<script setup lang="ts">
import { CircleCheck, CircleX, Plus, Search, X } from 'lucide-vue-next'
import { computed, reactive, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora, NOMBRE_DIMENSION, NOMBRE_SEVERIDAD, NOMBRE_TABLA, TABLAS } from '@/formato'
import { api } from '@/servicios/api'

type Regla = {
  id: string
  tabla: string
  dim: string
  tipo: string
  sev: string
  umbral: number
  activa?: boolean
  descripcion?: string
  actualizado_por?: string
  actualizado_en?: string
  [clave: string]: unknown
}

const { datos, cargando, error, recargar } = usarCarga(() => api<Regla[]>('/api/v1/reglas'))
const filtro = ref('')
const filtroTabla = ref('')
const reglas = computed(() =>
  (datos.value ?? []).filter(
    (r) =>
      (!filtroTabla.value || r.tabla === filtroTabla.value || (filtroTabla.value === '*' && r.tabla === '*')) &&
      (!filtro.value || `${r.id} ${r.tabla} ${r.dim} ${r.tipo}`.toLowerCase().includes(filtro.value.toLowerCase())),
  ),
)
const mensaje = ref<{ tipo: 'bien' | 'error'; texto: string } | null>(null)
const guardando = ref<string | null>(null)

async function cambiar(regla: Regla, cambios: Record<string, unknown>) {
  guardando.value = regla.id
  mensaje.value = null
  try {
    Object.assign(regla, await api<Regla>(`/api/v1/reglas/${regla.id}`, { metodo: 'PATCH', cuerpo: cambios }))
    mensaje.value = { tipo: 'bien', texto: `${regla.id} guardada. El cambio se aplica en la próxima ejecución.` }
  } catch (e) {
    mensaje.value = { tipo: 'error', texto: `${regla.id}: ${e instanceof Error ? e.message : e}` }
    await recargar()
  } finally {
    guardando.value = null
  }
}

// Severidad: con el teclado, las flechas sobre un select cerrado disparan "change" en Windows.
// Por eso con teclado se guarda al salir del campo (o con Enter) y solo si el valor cambió;
// con el mouse, al elegir la opción.
const SEVERIDADES = ['CRITICA', 'ALTA', 'MEDIA']
let conPuntero = false
const usarPuntero = (si: boolean) => (conPuntero = si)
function guardarSeveridad(regla: Regla, evento: Event, siempre = false) {
  const valor = (evento.target as HTMLSelectElement).value
  if (guardando.value === regla.id || !(siempre || conPuntero) || valor === regla.sev) return
  cambiar(regla, { sev: valor })
}

// Nueva regla
const TIPOS = ['no_nulo', 'al_menos_uno', 'unico', 'regex', 'dominio', 'expresion', 'referencia', 'frescura', 'variacion_volumen', 'minimo_filas']
const creando = ref(false)
const nueva = reactive({ id: '', tabla: 'poliza', dim: 'validez', tipo: 'expresion', sev: 'MEDIA', umbral: 99, campo: '', campos: '', patron: '', valores: '', filtro: '', cumple: '', ref: '', descripcion: '' })
const errorNueva = ref<string | null>(null)
async function crear() {
  errorNueva.value = null
  const lista = (t: string) => t.split(',').map((s) => s.trim()).filter(Boolean)
  const cuerpo: Record<string, unknown> = { id: nueva.id.trim().toUpperCase(), tabla: nueva.tabla, dim: nueva.dim, tipo: nueva.tipo, sev: nueva.sev, umbral: Number(nueva.umbral) }
  for (const clave of ['campo', 'patron', 'filtro', 'cumple', 'ref', 'descripcion'] as const) if (nueva[clave]) cuerpo[clave] = nueva[clave]
  if (nueva.campos) cuerpo.campos = lista(nueva.campos)
  if (nueva.valores) cuerpo.valores = lista(nueva.valores)
  try {
    await api('/api/v1/reglas', { metodo: 'POST', cuerpo })
    creando.value = false
    mensaje.value = { tipo: 'bien', texto: `${cuerpo.id} creada: su SQL compiló contra el último corte.` }
    await recargar()
  } catch (e) {
    errorNueva.value = e instanceof Error ? e.message : String(e)
  }
}
const necesita = (campo: string) =>
  ({
    campo: ['regex', 'dominio', 'referencia'],
    campos: ['no_nulo', 'al_menos_uno', 'unico'],
    patron: ['regex'],
    valores: ['dominio'],
    cumple: ['expresion'],
    ref: ['referencia'],
  })[campo]?.includes(nueva.tipo) ?? false
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Reglas</h1>
        <p>
          El catálogo de calidad, editable sin tocar código. Antes de guardar, la API valida la regla y compila su SQL contra el
          último corte, es decir, el último día de datos (HU-03).
        </p>
      </div>
      <button type="button" class="primario" @click="creando = !creando">
        <component :is="creando ? X : Plus" :size="16" /> {{ creando ? 'Cancelar' : 'Nueva regla' }}
      </button>
    </div>

    <p v-if="mensaje" class="aviso-caja" :class="mensaje.tipo" :role="mensaje.tipo === 'error' ? 'alert' : 'status'">
      <component :is="mensaje.tipo === 'bien' ? CircleCheck : CircleX" :size="17" />{{ mensaje.texto }}
    </p>

    <section v-if="creando" class="panel pila">
      <h2>Nueva regla</h2>
      <div class="formulario">
        <label class="campo">Id (ABC-DEF-01) <input v-model="nueva.id" placeholder="POL-VAL-09" /></label>
        <label class="campo">Tabla
          <select v-model="nueva.tabla"><option v-for="t in TABLAS" :key="t" :value="t">{{ NOMBRE_TABLA[t] }}</option></select>
        </label>
        <label class="campo">Dimensión
          <select v-model="nueva.dim"><option v-for="(n, d) in NOMBRE_DIMENSION" :key="d" :value="d">{{ n }}</option></select>
        </label>
        <label class="campo">Tipo <select v-model="nueva.tipo"><option v-for="t in TIPOS" :key="t">{{ t }}</option></select></label>
        <label class="campo">Severidad
          <select v-model="nueva.sev"><option v-for="v in SEVERIDADES" :key="v" :value="v">{{ NOMBRE_SEVERIDAD[v] }}</option></select>
        </label>
        <label class="campo">Umbral (%) <input v-model.number="nueva.umbral" type="number" min="0" max="100" step="0.5" /></label>
        <label v-if="necesita('campo')" class="campo">Campo <input v-model="nueva.campo" /></label>
        <label v-if="necesita('campos')" class="campo">Campos (coma) <input v-model="nueva.campos" /></label>
        <label v-if="necesita('patron')" class="campo">Patrón (regex) <input v-model="nueva.patron" class="mono" /></label>
        <label v-if="necesita('valores')" class="campo">Valores (coma) <input v-model="nueva.valores" /></label>
        <label v-if="necesita('ref')" class="campo">Referencia (tabla.columna) <input v-model="nueva.ref" class="mono" /></label>
      </div>
      <label v-if="necesita('cumple')" class="campo">Condición que debe cumplir cada fila (SQL) <input v-model="nueva.cumple" class="mono" placeholder="prima_total >= prima_neta" /></label>
      <label class="campo">Filtro del universo (SQL, opcional) <input v-model="nueva.filtro" class="mono" placeholder="estado = 'VIGENTE'" /></label>
      <label class="campo">Descripción <input v-model="nueva.descripcion" /></label>
      <p v-if="errorNueva" class="aviso-caja error" role="alert"><CircleX :size="17" />{{ errorNueva }}</p>
      <div><button type="button" class="primario" @click="crear">Validar y crear</button></div>
    </section>

    <div class="fila">
      <div class="segmentos" role="group" aria-label="Tabla">
        <button type="button" :class="{ activo: !filtroTabla }" :aria-pressed="!filtroTabla" @click="filtroTabla = ''">Todas las reglas</button>
        <button v-for="t in TABLAS" :key="t" type="button" :class="{ activo: filtroTabla === t }" :aria-pressed="filtroTabla === t" @click="filtroTabla = t">{{ NOMBRE_TABLA[t] }}</button>
        <button type="button" :class="{ activo: filtroTabla === '*' }" :aria-pressed="filtroTabla === '*'" @click="filtroTabla = '*'">De todas las tablas</button>
      </div>
      <label class="buscar"><Search :size="15" /><input v-model="filtro" type="search" placeholder="Buscar regla" aria-label="Buscar regla" /></label>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="panel lista">
        <div class="tabla-envoltura">
          <table>
            <thead>
              <tr><th>Activa</th><th>Regla</th><th>Tabla</th><th>Dimensión</th><th>Tipo</th><th>Severidad</th><th>Umbral</th><th>Último cambio</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in reglas" :key="r.id" :class="{ inactiva: r.activa === false }">
                <td>
                  <label class="interruptor" :title="r.activa === false ? 'Activar' : 'Desactivar'">
                    <input type="checkbox" :checked="r.activa !== false" :disabled="guardando === r.id" :aria-label="`Activar ${r.id}`"
                      @change="cambiar(r, { activa: ($event.target as HTMLInputElement).checked })" />
                    <span />
                  </label>
                </td>
                <td>
                  <strong>{{ r.id }}</strong>
                  <span v-if="r.activa === false" class="chip inactiva-etiqueta">Inactiva</span>
                  <p v-if="r.descripcion" class="tenue pequeno">{{ r.descripcion }}</p>
                </td>
                <td>{{ r.tabla === '*' ? 'Todas las tablas' : NOMBRE_TABLA[r.tabla] }}</td>
                <td>{{ NOMBRE_DIMENSION[r.dim] }}</td>
                <td><span class="chip">{{ r.tipo }}</span></td>
                <td>
                  <select
                    :value="r.sev"
                    :disabled="guardando === r.id"
                    :aria-label="`Severidad de ${r.id}`"
                    @pointerdown="usarPuntero(true)"
                    @keydown="usarPuntero(false)"
                    @keydown.enter="guardarSeveridad(r, $event, true)"
                    @change="guardarSeveridad(r, $event)"
                    @blur="guardarSeveridad(r, $event, true)"
                  >
                    <option v-for="v in SEVERIDADES" :key="v" :value="v">{{ NOMBRE_SEVERIDAD[v] }}</option>
                  </select>
                </td>
                <td>
                  <input type="number" min="0" max="100" step="0.5" class="umbral" :value="r.umbral" :disabled="guardando === r.id" aria-label="Umbral"
                    @change="cambiar(r, { umbral: Number(($event.target as HTMLInputElement).value) })" />
                </td>
                <td class="tenue pequeno">{{ r.actualizado_por }}<br />{{ hora(r.actualizado_en) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.formulario { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
.buscar { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--borde-control); border-radius: 999px; padding: 0 12px; background: var(--superficie); color: var(--tenue); }
.buscar:focus-within { border-color: var(--marca); box-shadow: 0 0 0 2px var(--marca-suave); }
.buscar input { border: 0; background: transparent; padding: 7px 0; outline: none; }
.lista { padding: 6px 8px; }
.umbral { width: 84px; }
/* Regla inactiva: texto atenuado que mantiene el contraste (≥ 4.5:1) y la etiqueta "Inactiva". */
.inactiva td:not(:first-child) { color: var(--tenue); }
.inactiva-etiqueta { margin-left: 6px; vertical-align: 1px; }
.pequeno { font-size: 12px; }
.interruptor { position: relative; display: inline-block; width: 38px; height: 22px; }
.interruptor input { position: absolute; opacity: 0; inset: 0; margin: 0; cursor: pointer; }
.interruptor span { position: absolute; inset: 0; border-radius: 999px; background: var(--borde-control); transition: background 0.15s; pointer-events: none; }
.interruptor span::after { content: ''; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; transition: transform 0.15s; box-shadow: 0 1px 2px rgb(0 0 0 / 0.25); }
.interruptor input:checked + span { background: var(--bien); }
.interruptor input:checked + span::after { transform: translateX(16px); }
.interruptor input:focus-visible + span { outline: 2px solid var(--marca); outline-offset: 2px; }
</style>
