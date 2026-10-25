<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

/**
 * Sello del Quality & Privacy Gate: un timbre circular por tabla y corte.
 * El estado va en el ícono central y en el texto (nunca solo en el color).
 * Cuando el estado cambia (otro día, una corrida nueva), el sello se vuelve a estampar.
 * `decorativo`: solo el timbre, sin leyenda y oculto para lectores de pantalla.
 */
const props = withDefaults(
  defineProps<{ estado: string; tabla: string; detalle?: string; tamano?: number; decorativo?: boolean }>(),
  { tamano: 132, detalle: '', decorativo: false },
)

let contador = 0
const id = `sello-${++contador}-${Math.random().toString(36).slice(2, 7)}`
const TONO: Record<string, { clase: string; color: string; suave: string; texto: string; leyenda: string }> = {
  CERTIFICADO: { clase: 'bien', color: 'var(--bien)', suave: 'var(--bien-suave)', texto: 'var(--bien-texto)', leyenda: 'Certificada' },
  CERTIFICADO_CON_OBSERVACIONES: { clase: 'aviso', color: 'var(--aviso)', suave: 'var(--aviso-suave)', texto: 'var(--aviso-texto)', leyenda: 'Con observaciones' },
  NO_CERTIFICADO: { clase: 'critico', color: 'var(--critico)', suave: 'var(--critico-suave)', texto: 'var(--critico-texto)', leyenda: 'No certificada' },
}
const tono = computed(
  () => TONO[props.estado] ?? { clase: 'neutro', color: 'var(--tenue)', suave: 'var(--neutro-suave)', texto: 'var(--tenue)', leyenda: 'Sin evaluar' },
)
const anillo = computed(() => `QUALITY & PRIVACY GATE · ${props.tabla.toUpperCase()} · `)

// Estampado: baja un poco más grande y girado, se aprieta y se asienta (WAAPI: interrumpible).
const timbre = ref<SVGSVGElement | null>(null)
let animacion: Animation | null = null
watch(
  () => props.estado,
  (nuevo, viejo) => {
    if (!viejo || nuevo === viejo || !timbre.value?.animate) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    animacion?.cancel()
    animacion = timbre.value.animate(
      [
        { transform: 'rotate(-17deg) scale(1.16)', opacity: 0.4 },
        { transform: 'rotate(-8deg) scale(0.96)', opacity: 1, offset: 0.62 },
        { transform: 'rotate(-9deg) scale(1)', opacity: 1 },
      ],
      { duration: 340, easing: 'cubic-bezier(0.23, 1, 0.32, 1)' },
    )
  },
)
onBeforeUnmount(() => animacion?.cancel())
</script>

<template>
  <figure
    class="sello"
    :style="{ width: `${tamano}px` }"
    :aria-label="decorativo ? undefined : `${tabla}: ${tono.leyenda}`"
    :aria-hidden="decorativo || undefined"
  >
    <svg ref="timbre" viewBox="0 0 120 120" :width="tamano" :height="tamano" aria-hidden="true">
      <defs>
        <path :id="id" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0" />
      </defs>
      <circle cx="60" cy="60" r="57" :fill="tono.suave" :stroke="tono.color" stroke-width="3" />
      <circle cx="60" cy="60" r="36" fill="none" :stroke="tono.color" stroke-width="1.4" stroke-dasharray="3 3" opacity="0.8" />
      <text class="anillo" :fill="tono.texto">
        <textPath :href="`#${id}`" startOffset="0">{{ anillo }}{{ anillo }}</textPath>
      </text>
      <g :stroke="tono.color" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" fill="none">
        <path v-if="estado === 'CERTIFICADO'" d="M44 61 l11 11 l22 -24" />
        <template v-else-if="estado === 'CERTIFICADO_CON_OBSERVACIONES'">
          <path d="M60 44 v18" />
          <path d="M60 75 v0.5" />
        </template>
        <template v-else-if="estado === 'NO_CERTIFICADO'">
          <path d="M47 47 l26 26" />
          <path d="M73 47 l-26 26" />
        </template>
        <path v-else d="M48 60 h24" />
      </g>
    </svg>
    <figcaption v-if="!decorativo">
      <strong>{{ tabla }}</strong>
      <span class="leyenda" :class="tono.clase">{{ tono.leyenda }}</span>
      <span v-if="detalle" class="tenue">{{ detalle }}</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.sello { margin: 0; display: grid; justify-items: center; gap: 8px; text-align: center; }
svg { transform: rotate(-9deg); transition: transform 0.3s var(--ease-out); filter: drop-shadow(0 6px 10px rgb(15 27 45 / 0.12)); }
@media (hover: hover) and (pointer: fine) {
  .sello:hover svg { transform: rotate(0deg) scale(1.04); }
}
a:focus-visible .sello svg { transform: rotate(0deg) scale(1.04); }
.anillo { font-size: 8.6px; font-weight: 800; letter-spacing: 0.08em; }
figcaption { display: grid; gap: 1px; line-height: 1.3; }
figcaption strong { font-size: 15px; }
figcaption span { font-size: 12.5px; font-weight: 600; }
/* El estado en palabras, del color de su sello (sobre fondos oscuros lo ajusta quien lo usa). */
.leyenda.bien { color: var(--bien-texto); }
.leyenda.aviso { color: var(--aviso-texto); }
.leyenda.critico { color: var(--critico-texto); }
.leyenda.neutro { color: var(--tenue); }
</style>
