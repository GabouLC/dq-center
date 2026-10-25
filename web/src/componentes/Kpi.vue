<script setup lang="ts">
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-vue-next'

/**
 * Indicador en tarjeta: franja superior y mosaico del ícono del color de su estado, la cifra
 * grande (dígitos tabulares) y, si hay, la variación frente al día anterior. La variación lleva
 * flecha y texto: el color dice si el cambio es bueno o malo, pero nunca va solo.
 */
export type Variacion = { texto: string; direccion: 'sube' | 'baja' | 'igual'; tono: 'bien' | 'critico' | 'neutro' }
defineProps<{ titulo: string; valor: string; detalle?: string; tono?: 'bien' | 'aviso' | 'critico'; icono?: unknown; variacion?: Variacion | null }>()
const FLECHA = { sube: ArrowUpRight, baja: ArrowDownRight, igual: Minus }
</script>

<template>
  <div class="kpi" :class="tono ?? 'neutro'">
    <span class="titulo">
      <span v-if="icono" class="icono-kpi" aria-hidden="true"><component :is="icono" :size="17" :stroke-width="2.2" /></span>
      {{ titulo }}
    </span>
    <span class="cifra-fila">
      <strong class="valor">{{ valor }}</strong>
      <span v-if="variacion" class="variacion" :class="variacion.tono">
        <component :is="FLECHA[variacion.direccion]" :size="13" :stroke-width="2.6" aria-hidden="true" />{{ variacion.texto }}
      </span>
    </span>
    <span v-if="detalle" class="detalle">{{ detalle }}</span>
  </div>
</template>

<style scoped>
.kpi {
  --tono: var(--marca);
  --tono-suave: var(--marca-suave);
  --tono-texto: var(--marca);
  position: relative; overflow: hidden; display: grid; gap: 6px; align-content: start; min-width: 0;
  padding: 18px 18px 16px; border-radius: var(--radio);
  background: var(--superficie); border: 1px solid color-mix(in srgb, var(--linea) 80%, transparent); box-shadow: var(--elev-1);
}
/* Franja de estado arriba, del ancho de la tarjeta. */
.kpi::before { content: ''; position: absolute; inset: 0 0 auto; height: 3px; background: var(--tono); }
.kpi.bien { --tono: var(--bien); --tono-suave: var(--bien-suave); --tono-texto: var(--bien-texto); }
.kpi.aviso { --tono: var(--aviso); --tono-suave: var(--aviso-suave); --tono-texto: var(--aviso-texto); }
.kpi.critico { --tono: var(--critico); --tono-suave: var(--critico-suave); --tono-texto: var(--critico-texto); }
.titulo { display: flex; align-items: center; gap: 9px; font-size: 13px; font-weight: 700; color: var(--tinta-2); }
.icono-kpi { display: grid; place-items: center; flex: none; width: 32px; height: 32px; border-radius: 10px; background: var(--tono-suave); color: var(--tono-texto); }
.cifra-fila { display: flex; align-items: baseline; gap: 4px 10px; flex-wrap: wrap; margin-top: 2px; }
.valor { font-size: var(--cifra-l); font-weight: 800; letter-spacing: -0.035em; line-height: 1.05; font-variant-numeric: tabular-nums; }
.variacion {
  display: inline-flex; align-items: center; gap: 3px; padding: 2px 8px 2px 6px; border-radius: 999px;
  font-size: 12px; font-weight: 700; white-space: nowrap; background: var(--neutro-suave); color: var(--tinta-2);
  font-variant-numeric: tabular-nums;
}
.variacion.bien { background: var(--bien-suave); color: var(--bien-texto); }
.variacion.critico { background: var(--critico-suave); color: var(--critico-texto); }
.detalle { font-size: 12.5px; color: var(--tenue); }
</style>
