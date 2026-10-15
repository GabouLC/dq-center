<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora, NOMBRE_TABLA, TABLAS } from '@/formato'
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
const reglas = computed(() =>
  (datos.value ?? []).filter((r) => !filtro.value || `${r.id} ${r.tabla} ${r.dim} ${r.tipo}`.toLowerCase().includes(filtro.value.toLowerCase())),
)
const mensaje = ref<{ tipo: 'ok' | 'error'; texto: string } | null>(null)
const guardando = ref<string | null>(null)

async function cambiar(regla: Regla, cambios: Record<string, unknown>) {
  guardando.value = regla.id
  mensaje.value = null
  try {
    const nueva = await api<Regla>(`/api/v1/reglas/${regla.id}`, { metodo: 'PATCH', cuerpo: cambios })
    Object.assign(regla, nueva)
    mensaje.value = { tipo: 'ok', texto: `${regla.id} guardada. El cambio se aplica en la próxima corrida.` }
  } catch (e) {
    mensaje.value = { tipo: 'error', texto: `${regla.id}: ${e instanceof Error ? e.message : e}` }
    await recargar()
  } finally {
    guardando.value = null
  }
}

// Nueva regla
const TIPOS = ['no_nulo', 'al_menos_uno', 'unico', 'regex', 'dominio', 'expresion', 'referencia', 'frescura', 'variacion_volumen', 'minimo_filas']
const DIMENSIONES = ['completitud', 'unicidad', 'validez', 'consistencia', 'integridad', 'oportunidad', 'volumetria']
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
    mensaje.value = { tipo: 'ok', texto: `${cuerpo.id} creada: su SQL se validó contra el último corte.` }
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
        <p class="muted">
          Catálogo de reglas de calidad. Se editan sin tocar código; antes de guardar, la API valida la regla y compila su
          SQL contra el último corte (HU-03).
        </p>
      </div>
      <div class="fila">
        <input v-model="filtro" type="search" placeholder="Filtrar reglas…" aria-label="Filtrar reglas" />
        <button type="button" class="primario" @click="creando = !creando">{{ creando ? 'Cancelar' : 'Nueva regla' }}</button>
      </div>
    </div>

    <p v-if="mensaje" class="aviso" :class="{ error: mensaje.tipo === 'error' }" role="status">{{ mensaje.texto }}</p>

    <section v-if="creando" class="tarjeta pila">
      <h2>Nueva regla</h2>
      <div class="formulario">
        <label class="campo">Id (ABC-DEF-01) <input v-model="nueva.id" placeholder="POL-VAL-09" /></label>
        <label class="campo">Tabla
          <select v-model="nueva.tabla"><option v-for="t in TABLAS" :key="t" :value="t">{{ NOMBRE_TABLA[t] }}</option></select>
        </label>
        <label class="campo">Dimensión <select v-model="nueva.dim"><option v-for="d in DIMENSIONES" :key="d">{{ d }}</option></select></label>
        <label class="campo">Tipo <select v-model="nueva.tipo"><option v-for="t in TIPOS" :key="t">{{ t }}</option></select></label>
        <label class="campo">Severidad <select v-model="nueva.sev"><option>CRITICA</option><option>ALTA</option><option>MEDIA</option></select></label>
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
      <p v-if="errorNueva" class="aviso error">{{ errorNueva }}</p>
      <div><button type="button" class="primario" @click="crear">Validar y crear</button></div>
    </section>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="tarjeta tabla-envoltura">
        <table>
          <thead>
            <tr><th>Regla</th><th>Tabla</th><th>Dimensión</th><th>Tipo</th><th>Severidad</th><th>Umbral</th><th>Activa</th><th>Último cambio</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in reglas" :key="r.id" :class="{ inactiva: r.activa === false }">
              <td class="mono">{{ r.id }}</td>
              <td>{{ r.tabla === '*' ? 'Todas' : NOMBRE_TABLA[r.tabla] }}</td>
              <td class="capital">{{ r.dim }}</td>
              <td class="mono">{{ r.tipo }}</td>
              <td>
                <select :value="r.sev" :disabled="guardando === r.id" aria-label="Severidad" @change="cambiar(r, { sev: ($event.target as HTMLSelectElement).value })">
                  <option>CRITICA</option><option>ALTA</option><option>MEDIA</option>
                </select>
              </td>
              <td>
                <input
                  type="number" min="0" max="100" step="0.5" class="umbral" :value="r.umbral" :disabled="guardando === r.id" aria-label="Umbral"
                  @change="cambiar(r, { umbral: Number(($event.target as HTMLInputElement).value) })"
                />
              </td>
              <td>
                <input type="checkbox" :checked="r.activa !== false" :disabled="guardando === r.id" aria-label="Activa"
                  @change="cambiar(r, { activa: ($event.target as HTMLInputElement).checked })" />
              </td>
              <td class="muted pequeno">{{ r.actualizado_por }} <br />{{ hora(r.actualizado_en) }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.formulario { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
.umbral { width: 80px; }
.capital { text-transform: capitalize; }
.inactiva td { opacity: 0.5; }
.pequeno { font-size: 12px; }
</style>
