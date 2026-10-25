<script setup lang="ts">
import {
  BadgeCheck, CircleAlert, CircleX, FastForward, FileInput, Info, Pause, Play, Radio, TriangleAlert, X,
} from 'lucide-vue-next'
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { corteCorto, relativo } from '@/formato'
import { useSesion } from '@/stores/sesion'
import { useVivo, type Evento } from '@/stores/vivo'

/** «En vivo»: estado de la simulación, panel de actividad y avisos de lo importante. */
const vivo = useVivo()
const sesion = useSesion()
const ahora = ref(Date.now())
let reloj: ReturnType<typeof setInterval>
onMounted(() => (reloj = setInterval(() => (ahora.value = Date.now()), 5000)))
onBeforeUnmount(() => clearInterval(reloj))

const ICONO: Record<string, unknown> = { carga: FileInput, certificacion: BadgeCheck }
const ICONO_TONO: Record<string, unknown> = { critico: CircleX, aviso: TriangleAlert, bien: BadgeCheck, info: Info }
const icono = (e: Evento) => (e.tono === 'critico' || e.tono === 'aviso' ? ICONO_TONO[e.tono] : ICONO[e.tipo] ?? ICONO_TONO[e.tono])

const texto = computed(() => {
  const e = vivo.estado
  if (!e?.activo) return ''
  if (e.pausado) return 'En pausa'
  if (e.corte_en_curso) return `Llegando ${corteCorto(e.corte_en_curso)} · ${e.archivos_recibidos} recibidos`
  if (e.dias_pendientes) return vivo.proximoEn !== null ? `Próximo archivo en ${Math.ceil(vivo.proximoEn)} s` : 'Esperando archivos'
  return 'Al día'
})
const enCurso = computed(() => !!vivo.estado?.activo && !vivo.estado.pausado && !!vivo.estado.dias_pendientes)

// Foco del panel: al abrirse va a "Cerrar"; al cerrarse vuelve a quien lo abrió (la pastilla o "Ver todo").
const pastilla = ref<HTMLButtonElement | null>(null)
const panel = ref<HTMLElement | null>(null)
const botonCerrar = ref<HTMLButtonElement | null>(null)
let abridor: HTMLElement | null = null
watch(
  () => vivo.panelAbierto,
  async (abierto) => {
    if (abierto) {
      abridor = document.activeElement instanceof HTMLElement ? document.activeElement : null
      await nextTick()
      botonCerrar.value?.focus()
      return
    }
    // Solo se devuelve el foco si estaba dentro del panel (no se le roba a otro control).
    const activo = document.activeElement
    if (activo && activo !== document.body && !panel.value?.contains(activo)) return
    const destino = abridor?.isConnected ? abridor : pastilla.value
    destino?.focus()
  },
)
</script>

<template>
  <template v-if="vivo.estado?.activo">
    <button
      ref="pastilla"
      type="button"
      class="pastilla"
      :class="{ pausado: vivo.estado.pausado, quieto: !enCurso }"
      aria-controls="panel-vivo"
      :aria-expanded="vivo.panelAbierto"
      @click="vivo.panelAbierto = !vivo.panelAbierto"
    >
      <span class="punto" aria-hidden="true" />
      <strong>En vivo</strong>
      <span class="texto">{{ texto }}</span>
    </button>

    <Teleport to="body">
      <Transition name="panel">
        <aside v-if="vivo.panelAbierto" id="panel-vivo" ref="panel" class="panel-vivo" aria-label="Actividad en vivo" @keydown.esc="vivo.panelAbierto = false">
          <header class="fila entre">
            <h2><Radio :size="18" /> Actividad en vivo</h2>
            <button ref="botonCerrar" type="button" class="icono fantasma" aria-label="Cerrar" @click="vivo.panelAbierto = false"><X :size="18" /></button>
          </header>
          <p class="estado-vivo">
            <span class="punto" :class="{ quieto: !enCurso }" aria-hidden="true" />
            <span>
              <template v-if="vivo.estado.corte_en_curso">
                Llegando los datos del <strong>{{ corteCorto(vivo.estado.corte_en_curso) }}</strong>:
                {{ vivo.estado.archivos_recibidos }} archivos en RAW, {{ vivo.estado.archivos_pendientes }} por llegar.
              </template>
              <template v-else-if="vivo.estado.dias_pendientes">
                Último día publicado: <strong>{{ corteCorto(vivo.estado.ultimo_corte ?? '') }}</strong>. Quedan
                {{ vivo.estado.dias_pendientes }} días por llegar.
              </template>
              <template v-else>Todo al día: no hay entregas pendientes.</template>
            </span>
          </p>
          <div v-if="sesion.puede('configurar') && vivo.estado.dias_pendientes" class="fila controles">
            <button type="button" @click="vivo.pausar(!vivo.estado.pausado)">
              <component :is="vivo.estado.pausado ? Play : Pause" :size="15" />{{ vivo.estado.pausado ? 'Reanudar' : 'Pausar' }}
            </button>
            <button type="button" :disabled="vivo.estado.pausado" @click="vivo.adelantar()">
              <FastForward :size="15" /> Siguiente archivo ahora
            </button>
          </div>
          <TransitionGroup tag="ol" name="evento" class="eventos">
            <li v-for="e in vivo.eventos" :key="e.id" :class="e.tono">
              <span class="marca-evento"><component :is="icono(e)" :size="15" /></span>
              <div>
                <strong>{{ e.titulo }}</strong>
                <p v-if="e.detalle">{{ e.detalle }}</p>
                <span class="tenue cuando">{{ relativo(e.cuando, ahora) }}<template v-if="e.fecha_corte"> · datos del {{ corteCorto(e.fecha_corte) }}</template></span>
              </div>
            </li>
            <li v-if="!vivo.eventos.length" key="vacio" class="vacio tenue">Todavía no hay actividad. El próximo archivo llega en unos segundos.</li>
          </TransitionGroup>
        </aside>
      </Transition>

      <div class="avisos" aria-live="polite">
        <TransitionGroup name="aviso">
          <button v-for="a in vivo.avisos" :key="a.id" type="button" class="aviso" :class="a.tono" @click="vivo.descartar(a.id)">
            <component :is="a.tono === 'critico' ? CircleAlert : BadgeCheck" :size="18" />
            <span><strong>{{ a.titulo }}</strong><span v-if="a.detalle">{{ a.detalle }}</span></span>
          </button>
        </TransitionGroup>
      </div>
    </Teleport>
  </template>
</template>

<style scoped>
.pastilla { gap: 8px; padding: 6px 12px; white-space: nowrap; flex: none; border-color: color-mix(in srgb, var(--bien) 45%, var(--linea)); background: var(--bien-suave); color: var(--tinta); font-size: 12.5px; max-width: 320px; }
.pastilla:hover { color: var(--tinta); border-color: var(--bien); }
.pastilla.pausado { background: var(--aviso-suave); border-color: var(--aviso); }
.pastilla .texto { color: var(--tinta-2); font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 170px; }
.punto { width: 8px; height: 8px; border-radius: 50%; background: var(--bien); flex: none; box-shadow: 0 0 0 0 color-mix(in srgb, var(--bien) 60%, transparent); animation: pulso 1.6s infinite; }
.pausado .punto, .punto.quieto, .quieto .punto { animation: none; }
.pausado .punto { background: var(--aviso); }
@keyframes pulso { 70% { box-shadow: 0 0 0 7px transparent; } 100% { box-shadow: 0 0 0 0 transparent; } }

.panel-vivo {
  position: fixed; top: 64px; right: 16px; bottom: 16px; width: min(400px, calc(100vw - 32px)); z-index: 60;
  display: flex; flex-direction: column; gap: 12px; padding: 16px; border-radius: 16px;
  background: var(--superficie); border: 1px solid var(--linea); box-shadow: var(--sombra-alta);
}
.panel-vivo h2 { display: inline-flex; align-items: center; gap: 8px; font-size: 17px; }
.estado-vivo { display: flex; gap: 10px; align-items: flex-start; font-size: 13px; color: var(--tinta-2); background: var(--superficie-2); border-radius: 10px; padding: 10px 12px; }
.estado-vivo .punto { margin-top: 5px; }
.controles { gap: 8px; flex-wrap: wrap; }
.eventos { list-style: none; margin: 0; padding: 0; overflow-y: auto; display: grid; gap: 2px; align-content: start; }
.eventos li { display: grid; grid-template-columns: 30px 1fr; gap: 10px; padding: 8px 4px; border-bottom: 1px solid var(--linea); }
.eventos li strong { font-size: 13px; }
.eventos li p { font-size: 12.5px; color: var(--tinta-2); margin: 1px 0; }
.cuando { font-size: 11.5px; }
.marca-evento { display: grid; place-items: center; width: 28px; height: 28px; border-radius: 50%; background: var(--superficie-2); color: var(--marca); }
.critico .marca-evento { background: var(--critico-suave); color: var(--critico); }
.aviso .marca-evento { background: var(--aviso-suave); color: var(--aviso-texto); }
.bien .marca-evento { background: var(--bien-suave); color: var(--bien); }
.vacio { display: block !important; font-size: 13px; }
/* Evento nuevo: entra desde arriba; los demás bajan para hacerle sitio. */
.evento-enter-active { transition: opacity 0.26s var(--ease-out), transform 0.26s var(--ease-out); }
.evento-enter-from { opacity: 0; transform: translateY(-10px); }
.evento-move { transition: transform 0.26s var(--ease-out); }

.avisos { position: fixed; right: 16px; bottom: 16px; z-index: 70; display: grid; gap: 8px; width: min(360px, calc(100vw - 32px)); }
.aviso { justify-content: flex-start; align-items: flex-start; gap: 10px; text-align: left; border-radius: 12px; padding: 12px 14px; background: var(--superficie); box-shadow: var(--sombra-alta); border-color: var(--linea); font-weight: 500; }
.aviso > span { display: grid; gap: 2px; font-size: 12.5px; color: var(--tinta-2); }
.aviso strong { color: var(--tinta); font-size: 13.5px; }
.aviso.critico { border-left: 4px solid var(--critico); }
.aviso.critico svg { color: var(--critico); }
.aviso.bien, .aviso.info { border-left: 4px solid var(--bien); }
.aviso.bien svg { color: var(--bien); }
.panel-enter-active { transition: opacity 0.22s var(--ease-out), transform 0.22s var(--ease-out); }
.panel-leave-active { transition: opacity 0.15s ease, transform 0.15s ease; }
.panel-enter-from, .panel-leave-to { opacity: 0; transform: translateX(16px); }
/* Avisos: entran y salen por abajo, por donde aparecen. */
.aviso-enter-active { transition: opacity 0.24s var(--ease-out), transform 0.24s var(--ease-out); }
.aviso-leave-active { transition: opacity 0.16s ease, transform 0.16s ease; }
.aviso-enter-from, .aviso-leave-to { opacity: 0; transform: translateY(12px); }
@media (max-width: 1360px) { .pastilla .texto { display: none; } }
</style>
