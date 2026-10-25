<script setup lang="ts">
import { CircleAlert, RotateCw } from 'lucide-vue-next'

/**
 * Carga: la primera vez muestra la forma de lo que viene (esqueleto); al llegar, los bloques
 * entran escalonados. Mientras recarga, el contenido anterior queda atenuado (sin parpadeos).
 * `forma` elige el esqueleto que más se parece a la vista.
 */
withDefaults(defineProps<{ cargando: boolean; error: string | null; vacio?: boolean; forma?: 'tabla' | 'tarjetas' | 'resumen' | 'lista' }>(), {
  forma: 'tabla',
})
defineEmits<{ reintentar: [] }>()
const ANCHOS = ['92%', '78%', '86%', '64%', '88%', '72%']
</script>

<template>
  <div v-if="error" class="aviso-caja error entre" role="alert">
    <CircleAlert :size="18" />
    <span class="mensaje">No pudimos cargar estos datos: {{ error }}</span>
    <button type="button" @click="$emit('reintentar')"><RotateCw :size="15" /> Reintentar</button>
  </div>
  <div v-else-if="cargando && vacio" class="esqueletos" role="status">
    <span class="visualmente-oculto">Cargando…</span>
    <template v-if="forma === 'resumen'">
      <div class="panel fila-esq" aria-hidden="true">
        <span class="esqueleto circulo" style="width: 64px; height: 64px" />
        <span class="pila-chica crece"><span class="esqueleto" style="width: 58%; height: 20px" /><span class="esqueleto" style="width: 82%; height: 13px" /></span>
      </div>
      <div class="panel fila-esq alto" aria-hidden="true">
        <span class="pila-chica" style="width: 220px"><span class="esqueleto" style="width: 70%; height: 12px" /><span class="esqueleto" style="width: 60%; height: 52px" /></span>
        <span v-for="i in 5" :key="i" class="esqueleto circulo" style="width: 96px; height: 96px" />
      </div>
      <div class="tres" aria-hidden="true"><span v-for="i in 3" :key="i" class="esqueleto" style="height: 86px; border-radius: 12px" /></div>
    </template>
    <template v-else-if="forma === 'tarjetas'">
      <div v-for="i in 3" :key="i" class="panel fila-esq" aria-hidden="true">
        <span class="esqueleto circulo" style="width: 72px; height: 72px" />
        <span class="pila-chica crece"><span class="esqueleto" style="width: 30%; height: 16px" /><span class="esqueleto" :style="{ width: ANCHOS[i], height: '12px' }" /><span class="esqueleto" style="width: 44%; height: 12px" /></span>
      </div>
    </template>
    <div v-else-if="forma === 'lista'" class="panel pila-chica" aria-hidden="true">
      <span v-for="(a, i) in ANCHOS" :key="i" class="fila-esq">
        <span class="esqueleto circulo" style="width: 32px; height: 32px" />
        <span class="pila-chica crece"><span class="esqueleto" :style="{ width: a, height: '13px' }" /><span class="esqueleto" style="width: 36%; height: 11px" /></span>
      </span>
    </div>
    <div v-else class="panel pila-chica" aria-hidden="true">
      <span class="esqueleto" style="width: 28%; height: 14px; margin-bottom: 8px" />
      <span v-for="(a, i) in ANCHOS" :key="i" class="fila-tabla">
        <span class="esqueleto" style="width: 90px; height: 12px" />
        <span class="esqueleto" :style="{ width: a, height: '12px' }" />
        <span class="esqueleto" style="width: 64px; height: 18px; border-radius: 999px" />
      </span>
    </div>
  </div>
  <div v-else class="pila escalonado" :class="{ recargando: cargando }">
    <slot />
  </div>
</template>

<style scoped>
.mensaje { flex: 1; }
.esqueletos { display: grid; gap: 18px; }
.fila-esq { display: flex; align-items: center; gap: 16px; }
.fila-esq.alto { gap: 22px; flex-wrap: wrap; padding: 26px 20px; }
.crece { flex: 1; }
.circulo { border-radius: 50%; flex: none; }
.tres { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.fila-tabla { display: grid; grid-template-columns: 90px 1fr 64px; gap: 18px; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--linea); }
.recargando { opacity: 0.55; transition: opacity 0.15s; }
@media (max-width: 760px) {
  .tres { grid-template-columns: 1fr; }
  .fila-esq.alto .circulo:nth-of-type(n + 4) { display: none; }
}
</style>
