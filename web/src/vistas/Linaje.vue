<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import DacChip from '@/componentes/DacChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, NOMBRE_TABLA, TABLAS } from '@/formato'
import { api } from '@/servicios/api'

type Nodo = { id: string; capa: string; objeto: string; detalle: string }
type Arista = { desde: string; hacia: string; proceso: string }
type Campo = { raw: string; master: string; business: string; transformacion: string; dac: string; en_contrato: boolean }
type Linaje = {
  tabla: string
  dominio: string
  nodos: Nodo[]
  aristas: Arista[]
  campos: Campo[]
  cortes_publicados: string[]
  cortes_retenidos: string[]
}
type Termino = { id: string; termino: string; campos?: string[] }

const ruta = useRoute()
const router = useRouter()
const tabla = computed(() => (TABLAS.includes(String(ruta.params.tabla)) ? String(ruta.params.tabla) : 'persona'))
const { datos, cargando, error, recargar } = usarCarga(() => api<Linaje>(`/api/v1/linaje/${tabla.value}`), [tabla])
const glosario = usarCarga(() => api<Termino[]>('/api/v1/glosario'))
const foco = ref<string | null>(null)
const filtro = ref('')

const terminosDe = (campo: string) =>
  (glosario.datos.value ?? []).filter((t) => t.campos?.includes(`${tabla.value}.${campo}`))
const campos = computed(() =>
  (datos.value?.campos ?? []).filter((c) => !filtro.value || [c.raw, c.master].some((n) => n.toLowerCase().includes(filtro.value.toLowerCase()))),
)
const proceso = (desde: string) => datos.value?.aristas.find((a) => a.desde === desde)?.proceso ?? ''
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Linaje</h1>
        <p class="muted">
          Recorrido de cada dato desde el archivo de origen hasta BUSINESS, con las transformaciones que sufre (HU-11). Pasa
          el cursor por un campo para seguir su camino.
        </p>
      </div>
      <select :value="tabla" aria-label="Tabla" @change="router.push(`/linaje/${($event.target as HTMLSelectElement).value}`)">
        <option v-for="t in TABLAS" :key="t" :value="t">{{ NOMBRE_TABLA[t] }}</option>
      </select>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="datos">
        <section class="tarjeta pila">
          <div class="flujo" role="list">
            <template v-for="(n, i) in datos.nodos" :key="n.id">
              <div class="nodo" :class="n.capa" role="listitem">
                <span class="capa">{{ n.capa }}</span>
                <span class="objeto mono"><span class="muted">{{ n.objeto.split('.')[0] }}.</span><strong>{{ n.objeto.split('.')[1] }}</strong></span>
                <span class="muted pequeno">{{ n.detalle }}</span>
              </div>
              <div v-if="i < datos.nodos.length - 1" class="flecha" aria-hidden="true">
                <span class="pequeno muted">{{ proceso(n.id) }}</span>
                <span class="punta">→</span>
              </div>
            </template>
          </div>
          <div class="fila pequeno">
            <span class="muted">Cortes publicados en BUSINESS:</span>
            <span v-for="c in datos.cortes_publicados" :key="c" class="chip ok">{{ nombreCorte(c) }}</span>
            <template v-if="datos.cortes_retenidos.length">
              <span class="muted">Retenidos por el Gate:</span>
              <RouterLink v-for="c in datos.cortes_retenidos" :key="c" to="/certificacion" class="chip falla">{{ nombreCorte(c) }}</RouterLink>
            </template>
          </div>
        </section>

        <section class="tarjeta pila">
          <div class="fila entre">
            <h2>Linaje por campo</h2>
            <input v-model="filtro" type="search" placeholder="Buscar campo…" aria-label="Buscar campo" />
          </div>
          <div class="tabla-envoltura">
            <table class="campos">
              <thead>
                <tr><th>RAW · columna de origen</th><th>Transformación</th><th>MASTER y BUSINESS</th><th>DAC</th><th>Glosario</th></tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in campos"
                  :key="c.raw"
                  :class="{ foco: foco === c.raw, atenuado: foco && foco !== c.raw }"
                  @mouseenter="foco = c.raw"
                  @mouseleave="foco = null"
                  @focusin="foco = c.raw"
                  @focusout="foco = null"
                >
                  <td class="mono">{{ c.raw }}</td>
                  <td><span class="transformacion">→ {{ c.transformacion }} →</span></td>
                  <td class="mono">
                    {{ c.master }}
                    <span v-if="!c.en_contrato" class="chip alerta">fuera de contrato</span>
                  </td>
                  <td><DacChip :dac="c.dac" /></td>
                  <td>
                    <RouterLink v-for="t in terminosDe(c.master)" :key="t.id" :to="`/glosario/${t.id}`" class="chip acento">{{ t.termino }}</RouterLink>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.flujo { display: grid; grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr; gap: 8px; align-items: stretch; }
.nodo {
  display: grid;
  gap: 4px;
  align-content: start;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--surface-2);
  min-width: 0;
}
.objeto { display: grid; font-size: 12.5px; }
.objeto strong { font-size: 13.5px; }
.nodo.RAW { border-top: 3px solid var(--sensible); }
.nodo.MASTER { border-top: 3px solid var(--cifrado); }
.nodo.BUSINESS { border-top: 3px solid var(--ok); }
.capa { font-size: 11px; font-weight: 700; letter-spacing: 0.06em; color: var(--muted); }
.flecha { display: grid; place-items: center; text-align: center; max-width: 130px; }
.punta { font-size: 22px; color: var(--accent); }
.pequeno { font-size: 12px; }
.campos tr { transition: opacity 0.15s; }
.campos tr.atenuado { opacity: 0.45; }
.campos tr.foco { background: var(--accent-soft); }
.transformacion { color: var(--muted); font-size: 12.5px; white-space: nowrap; }
@media (max-width: 900px) {
  .flujo { grid-template-columns: 1fr; }
  .flecha { max-width: none; }
  .punta { transform: rotate(90deg); }
}
</style>
