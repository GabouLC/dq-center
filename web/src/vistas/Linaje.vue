<script setup lang="ts">
import { ArrowRight, BadgeCheck, ChevronDown, Database, Eye, FileInput, Lock, Search } from 'lucide-vue-next'
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
const abierto = ref<string | null>(null)
const filtro = ref('')
const filtroDac = ref('')

const ICONO_NODO: Record<string, unknown> = { raw: FileInput, master: Database, p: BadgeCheck, v: Eye }
const COLOR_DAC: Record<string, string> = {
  PUBLICO: 'var(--linea-fuerte)',
  SENSIBLE: 'var(--aviso)',
  SENSIBLE_CIFRADO: 'var(--sello)',
  SIN_CLASIFICAR: 'var(--critico)',
}
const terminosDe = (campo: string) => (glosario.datos.value ?? []).filter((t) => t.campos?.includes(`${tabla.value}.${campo}`))
const campos = computed(() =>
  (datos.value?.campos ?? []).filter(
    (c) =>
      (!filtroDac.value || c.dac === filtroDac.value) &&
      (!filtro.value || [c.raw, c.master].some((n) => n.toLowerCase().includes(filtro.value.toLowerCase()))),
  ),
)
const cuenta = (dac: string) => (datos.value?.campos ?? []).filter((c) => c.dac === dac).length
const proceso = (desde: string) => datos.value?.aristas.find((a) => a.desde === desde)?.proceso ?? ''
const cifrado = (c: Campo) => c.transformacion.includes('cifrado')
const pasos = (c: Campo) => c.transformacion.split(' · ').filter((p) => p !== 'copia')
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Linaje</h1>
        <p>De dónde viene cada dato, qué le pasa en el camino y dónde se expone. Elige un campo para ver su recorrido paso a paso.</p>
      </div>
      <div class="segmentos" role="group" aria-label="Tabla">
        <button v-for="t in TABLAS" :key="t" type="button" :class="{ activo: t === tabla }" :aria-pressed="t === tabla" @click="router.push(`/linaje/${t}`)">{{ NOMBRE_TABLA[t] }}</button>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="datos">
        <section class="panel pila">
          <ol class="flujo">
            <template v-for="(n, i) in datos.nodos" :key="n.id">
              <li class="nodo" :class="n.capa">
                <span class="icono-nodo"><component :is="ICONO_NODO[n.id]" :size="20" /></span>
                <span class="capa">{{ n.capa === 'BUSINESS' && n.id === 'v' ? 'Vista' : n.capa }}</span>
                <span class="objeto">
                  <span class="tenue">{{ n.objeto.split('.')[0] }}.</span><strong>{{ n.objeto.split('.')[1] }}</strong>
                </span>
                <span class="tenue pequeno">{{ n.detalle }}</span>
              </li>
              <li v-if="i < datos.nodos.length - 1" class="paso">
                <ArrowRight :size="20" aria-hidden="true" />
                <span>{{ proceso(n.id) }}</span>
              </li>
            </template>
          </ol>
          <div class="fila publicacion">
            <span class="secundario">Publicado en BUSINESS:</span>
            <span v-for="c in datos.cortes_publicados" :key="c" class="chip bien"><BadgeCheck :size="12" />{{ nombreCorte(c) }}</span>
            <template v-if="datos.cortes_retenidos.length">
              <span class="secundario">No publicado en BUSINESS:</span>
              <RouterLink v-for="c in datos.cortes_retenidos" :key="c" to="/certificacion" class="chip critico">{{ nombreCorte(c) }}</RouterLink>
            </template>
          </div>
        </section>

        <section class="panel pila">
          <div class="fila entre">
            <h2>Recorrido de cada campo</h2>
            <div class="fila">
              <div class="segmentos" role="group" aria-label="Clasificación DAC">
                <button type="button" :class="{ activo: !filtroDac }" :aria-pressed="!filtroDac" @click="filtroDac = ''">Todos</button>
                <button type="button" :class="{ activo: filtroDac === 'PUBLICO' }" :aria-pressed="filtroDac === 'PUBLICO'" @click="filtroDac = 'PUBLICO'">Público <span class="cuenta">{{ cuenta('PUBLICO') }}</span></button>
                <button type="button" :class="{ activo: filtroDac === 'SENSIBLE' }" :aria-pressed="filtroDac === 'SENSIBLE'" @click="filtroDac = 'SENSIBLE'">Sensible <span class="cuenta">{{ cuenta('SENSIBLE') }}</span></button>
                <button type="button" :class="{ activo: filtroDac === 'SENSIBLE_CIFRADO' }" :aria-pressed="filtroDac === 'SENSIBLE_CIFRADO'" @click="filtroDac = 'SENSIBLE_CIFRADO'">Sensible cifrado <span class="cuenta">{{ cuenta('SENSIBLE_CIFRADO') }}</span></button>
              </div>
              <label class="buscar"><Search :size="15" /><input v-model="filtro" type="search" placeholder="Buscar campo" aria-label="Buscar campo" /></label>
            </div>
          </div>

          <div class="cabecera-recorrido tenue">
            <span>Origen (CSV en RAW)</span><span /><span>MASTER</span><span /><span>BUSINESS</span><span>DAC</span>
          </div>
          <div class="recorridos" :class="{ hay_foco: foco }">
            <div
              v-for="c in campos"
              :key="c.raw"
              class="recorrido"
              :class="{ foco: foco === c.raw, abierto: abierto === c.raw }"
              :style="{ '--color-dac': COLOR_DAC[c.dac] }"
              @mouseenter="foco = c.raw"
              @mouseleave="foco = null"
            >
              <button type="button" class="linea-campo" :aria-expanded="abierto === c.raw" @click="abierto = abierto === c.raw ? null : c.raw" @focus="foco = c.raw" @blur="foco = null">
                <span class="pastilla origen mono">{{ c.raw }}</span>
                <svg class="conector" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true"><path d="M0 10 H96" /><path d="M90 5 L97 10 L90 15" class="punta" /></svg>
                <span class="pastilla master">
                  <Lock v-if="cifrado(c)" :size="13" class="candado" />{{ c.master }}
                  <span v-if="!c.en_contrato" class="chip aviso mini">fuera de contrato</span>
                </span>
                <svg class="conector" viewBox="0 0 100 20" preserveAspectRatio="none" aria-hidden="true"><path d="M0 10 H96" /><path d="M90 5 L97 10 L90 15" class="punta" /></svg>
                <span class="pastilla business"><Lock v-if="cifrado(c)" :size="13" class="candado" />{{ c.business }}</span>
                <DacChip :dac="c.dac" />
                <ChevronDown :size="16" class="flecha" />
              </button>
              <div v-if="abierto === c.raw" class="detalle">
                <ol class="pasos">
                  <li><strong class="mono">{{ c.raw }}</strong><span class="tenue">texto, tal como llega en el CSV</span></li>
                  <li v-for="p in pasos(c)" :key="p">
                    <strong>{{ p }}</strong>
                    <span v-if="p.startsWith('cifrado determinístico')" class="tenue">mismo valor, mismo cifrado: permite unicidad y cruces</span>
                    <span v-else-if="p.startsWith('cifrado aleatorio')" class="tenue">cada cifrado es distinto; solo el motor lo descifra en memoria</span>
                    <span v-else-if="p.startsWith('convertir')" class="tenue">si no se puede convertir, el registro va a incidencias</span>
                  </li>
                  <li><strong class="mono">{{ c.master }}</strong><span class="tenue">en dq_master y en BUSINESS solo si ese día se certifica</span></li>
                </ol>
                <div v-if="terminosDe(c.master).length" class="fila">
                  <span class="secundario">En el glosario:</span>
                  <RouterLink v-for="t in terminosDe(c.master)" :key="t.id" :to="`/glosario/${t.id}`" class="chip marca">{{ t.termino }}</RouterLink>
                </div>
              </div>
            </div>
          </div>
          <p v-if="!campos.length" class="tenue">Ningún campo coincide.</p>
        </section>
      </template>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.flujo { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr auto 1fr auto 1fr auto 1fr; gap: 10px; align-items: stretch; }
.nodo { display: grid; gap: 4px; align-content: start; padding: 14px; border-radius: 12px; background: var(--superficie-2); border-top: 4px solid var(--linea-fuerte); min-width: 0; }
.nodo.RAW { border-top-color: var(--aviso); }
.nodo.MASTER { border-top-color: var(--sello); }
.nodo.BUSINESS { border-top-color: var(--bien); }
.icono-nodo { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 10px; background: var(--superficie); color: var(--tinta-2); }
.nodo.RAW .icono-nodo { color: var(--aviso-texto); }
.nodo.MASTER .icono-nodo { color: var(--sello); }
.nodo.BUSINESS .icono-nodo { color: var(--bien-texto); }
.capa { font-size: 12px; font-weight: 800; color: var(--tinta-2); }
.objeto { display: grid; font-size: 13px; overflow-wrap: anywhere; }
.objeto strong { font-size: 15px; }
.nodo .pequeno { overflow-wrap: anywhere; }
.paso { display: grid; place-items: center; align-content: center; gap: 4px; max-width: 140px; text-align: center; color: var(--marca); font-size: 12px; font-weight: 600; }
.paso span { color: var(--tinta-2); }
.publicacion { gap: 6px; }
.pequeno { font-size: 12.5px; }
.buscar { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--borde-control); border-radius: 999px; padding: 0 12px; background: var(--superficie); color: var(--tenue); }
.buscar:focus-within { border-color: var(--marca); box-shadow: 0 0 0 2px var(--marca-suave); }
.buscar input { border: 0; background: transparent; min-width: 140px; padding: 7px 0; outline: none; }

.cabecera-recorrido, .linea-campo {
  display: grid;
  grid-template-columns: minmax(130px, 1fr) minmax(40px, 0.6fr) minmax(150px, 1.1fr) minmax(40px, 0.6fr) minmax(140px, 1fr) 150px 18px;
  align-items: center;
  gap: 6px;
}
.cabecera-recorrido { font-size: 12px; font-weight: 700; padding: 0 12px; }
.recorridos { display: grid; gap: 4px; }
.recorrido { border-radius: 12px; transition: opacity 0.15s, background 0.15s; }
.recorridos.hay_foco .recorrido:not(.foco) { opacity: 0.4; }
.recorrido.foco, .recorrido.abierto { background: var(--superficie-2); }
.linea-campo { width: 100%; border: 0; border-radius: 12px; background: transparent; padding: 6px 12px; font-weight: 600; text-align: left; color: var(--tinta); }
.linea-campo:hover { color: var(--tinta); }
.pastilla { display: inline-flex; align-items: center; gap: 5px; padding: 5px 10px; border-radius: 8px; border: 1.5px solid var(--color-dac); background: var(--superficie); font-size: 13px; min-width: 0; overflow-wrap: anywhere; }
.pastilla.origen { font-size: 12px; }
.candado { color: var(--sello); flex: none; }
.mini { font-size: 10.5px; padding: 0 6px; }
.conector { width: 100%; height: 20px; overflow: visible; }
.conector path { fill: none; stroke: var(--color-dac); stroke-width: 2; vector-effect: non-scaling-stroke; }
.conector .punta { stroke-linecap: round; stroke-linejoin: round; }
.recorrido.foco .conector path:first-child { stroke-dasharray: 6 4; animation: fluye 0.7s linear infinite; }
@keyframes fluye { to { stroke-dashoffset: -10; } }
.flecha { color: var(--tenue); transition: transform 0.15s; }
.recorrido.abierto .flecha { transform: rotate(180deg); }
.detalle { padding: 4px 18px 16px; display: grid; gap: 10px; }
.pasos { margin: 0; padding: 0; list-style: none; display: grid; gap: 0; counter-reset: paso; }
.pasos li { display: grid; grid-template-columns: 26px 1fr; column-gap: 10px; padding: 6px 0; position: relative; }
.pasos li::before {
  counter-increment: paso;
  content: counter(paso);
  grid-row: span 2;
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--superficie);
  border: 2px solid var(--color-dac);
  font-size: 12px;
  font-weight: 800;
}
.pasos li span { grid-column: 2; font-size: 12.5px; }
@media (max-width: 1000px) {
  .flujo { grid-template-columns: 1fr; }
  .paso { max-width: none; grid-auto-flow: column; justify-content: start; }
  .paso svg { transform: rotate(90deg); }
  .cabecera-recorrido { display: none; }
  .linea-campo { grid-template-columns: 1fr 24px 1fr; row-gap: 6px; }
  .linea-campo .conector:nth-of-type(2), .linea-campo .business { display: none; }
}
</style>
