<script setup lang="ts">
import { computed } from 'vue'

/**
 * Sello del Quality & Privacy Gate: un timbre circular por tabla y corte.
 * El estado va en el ícono central y en el texto (nunca solo en el color).
 */
const props = withDefaults(
  defineProps<{ estado: string; tabla: string; detalle?: string; tamano?: number }>(),
  { tamano: 132, detalle: '' },
)

let contador = 0
const id = `sello-${++contador}-${Math.random().toString(36).slice(2, 7)}`
const TONO: Record<string, { color: string; suave: string; texto: string; leyenda: string }> = {
  CERTIFICADO: { color: 'var(--bien)', suave: 'var(--bien-suave)', texto: 'var(--bien-texto)', leyenda: 'Certificada' },
  CERTIFICADO_CON_OBSERVACIONES: { color: 'var(--aviso)', suave: 'var(--aviso-suave)', texto: 'var(--aviso-texto)', leyenda: 'Con observaciones' },
  NO_CERTIFICADO: { color: 'var(--critico)', suave: 'var(--critico-suave)', texto: 'var(--critico-texto)', leyenda: 'No certificada' },
}
const tono = computed(() => TONO[props.estado] ?? { color: 'var(--tenue)', suave: 'var(--neutro-suave)', texto: 'var(--tenue)', leyenda: 'Sin evaluar' })
const anillo = computed(() => `QUALITY & PRIVACY GATE · ${props.tabla.toUpperCase()} · `)
</script>

<template>
  <figure class="sello" :style="{ width: `${tamano}px` }" :aria-label="`${tabla}: ${tono.leyenda}`">
    <svg viewBox="0 0 120 120" :width="tamano" :height="tamano" aria-hidden="true">
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
    <figcaption>
      <strong>{{ tabla }}</strong>
      <span :style="{ color: tono.texto }">{{ tono.leyenda }}</span>
      <span v-if="detalle" class="tenue">{{ detalle }}</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.sello { margin: 0; display: grid; justify-items: center; gap: 8px; text-align: center; }
svg { transform: rotate(-9deg); transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1); filter: drop-shadow(0 6px 10px rgb(15 27 45 / 0.12)); }
.sello:hover svg, a:focus-visible .sello svg { transform: rotate(0deg) scale(1.04); }
.anillo { font-size: 8.6px; font-weight: 800; letter-spacing: 0.08em; }
figcaption { display: grid; gap: 1px; line-height: 1.3; }
figcaption strong { font-size: 15px; }
figcaption span { font-size: 12.5px; font-weight: 600; }
</style>
