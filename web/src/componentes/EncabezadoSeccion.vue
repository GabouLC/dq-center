<script setup lang="ts">
import { ChevronDown, Info, Lock } from 'lucide-vue-next'
import { computed, useId } from 'vue'
import { usarPreferencia } from '@/composables/usarPreferencia'
import { MODULOS, type Clave } from '@/navegacion'

/**
 * Encabezado común de cada sección: dónde estoy (título), para qué sirve (la pregunta que
 * responde y un subtítulo) y, plegado, «¿Cómo se lee?»: qué significan los colores, barras y
 * marcas de la página. Abierto o cerrado se recuerda por usuario y por sección.
 */
const props = defineProps<{ modulo: string; titulo: string; subtitulo?: string; lectura?: Clave[] }>()

const info = computed(() => MODULOS[props.modulo])
const id = useId()
const abiertos = usarPreferencia<Record<string, boolean>>('como-se-lee', {})
const abierto = computed({
  get: () => abiertos.value[props.modulo] ?? false,
  set: (valor: boolean) => (abiertos.value = { ...abiertos.value, [props.modulo]: valor }),
})
</script>

<template>
  <header class="cabeza">
    <div class="texto">
      <div class="titulo">
        <span v-if="info" class="icono-modulo" aria-hidden="true"><component :is="info.icono" :size="18" :stroke-width="2.2" /></span>
        <h1>{{ titulo }}</h1>
      </div>
      <p v-if="info" class="pregunta">{{ info.pregunta }}</p>
      <p v-if="subtitulo" class="subtitulo">{{ subtitulo }}</p>
    </div>
    <div v-if="$slots.default" class="acciones"><slot /></div>

    <div v-if="lectura?.length" class="lectura">
      <button type="button" class="alternar" :class="{ abierto }" :aria-expanded="abierto" :aria-controls="id" @click="abierto = !abierto">
        <Info :size="15" aria-hidden="true" /> ¿Cómo se lee?
        <ChevronDown :size="15" class="flecha" aria-hidden="true" />
      </button>
      <div :id="id" class="plegable" :class="{ abierto }">
        <div class="interior">
          <ul class="claves">
            <li v-for="c in lectura" :key="c.texto">
              <span v-if="c.muestras?.length" class="muestras" aria-hidden="true">
                <template v-for="m in c.muestras" :key="m">
                  <Lock v-if="m === 'candado'" :size="13" :stroke-width="2.4" class="candado" />
                  <i v-else class="muestra" :class="m" />
                </template>
              </span>
              <span>{{ c.texto }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  </header>
</template>

<style scoped>
.cabeza { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 4px 20px; align-items: end; }
.texto { display: grid; gap: 6px; min-width: 0; }
.titulo { display: flex; align-items: center; gap: 11px; }
.icono-modulo {
  display: grid; place-items: center; flex: none; width: 34px; height: 34px; border-radius: 10px;
  background: var(--marca-suave); color: var(--marca);
}
.pregunta { font-size: 17.5px; font-weight: 600; line-height: 1.35; letter-spacing: -0.01em; color: var(--tinta); max-width: 60ch; text-wrap: balance; }
.subtitulo { color: var(--tinta-2); max-width: 74ch; }
.acciones { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; justify-content: flex-end; }

.lectura { grid-column: 1 / -1; display: grid; justify-items: start; margin-top: 6px; }
.alternar {
  gap: 6px; padding: 4px 10px 4px 9px; font-size: 12.5px; color: var(--tinta-2);
  border-color: var(--linea-fuerte); background: var(--superficie);
}
.alternar.abierto { background: var(--marca-suave); color: var(--marca); border-color: transparent; }
.flecha { transition: transform 0.2s var(--ease-out); }
.alternar.abierto .flecha { transform: rotate(180deg); }

/* Pliegue: la altura sigue al contenido (0fr → 1fr); cerrado no se ve ni recibe foco. */
.plegable {
  display: grid; grid-template-rows: 0fr; width: 100%; visibility: hidden;
  transition: grid-template-rows 0.24s var(--ease-out), visibility 0s linear 0.24s;
}
.plegable.abierto { grid-template-rows: 1fr; visibility: visible; transition-delay: 0s; }
.interior { overflow: hidden; min-height: 0; opacity: 0; transition: opacity 0.18s ease; }
.plegable.abierto .interior { opacity: 1; }
.claves {
  list-style: none; margin: 10px 0 0; padding: 14px 16px; display: grid; gap: 10px 28px;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 400px), 1fr));
  background: var(--superficie); border: 1px solid var(--linea); border-radius: 12px;
}
.claves li { display: flex; gap: 10px; align-items: baseline; font-size: 13px; line-height: 1.5; color: var(--tinta-2); }
.muestras { display: inline-flex; gap: 3px; align-items: center; flex: none; min-width: 20px; transform: translateY(1px); }
.muestra { display: inline-block; width: 12px; height: 12px; border-radius: 3px; background: var(--superficie-3); }
.muestra.bien { background: var(--bien); }
.muestra.aviso { background: var(--celda-aviso); }
.muestra.critico { background: var(--celda-critico); box-shadow: inset 0 0 0 1.5px var(--tinta); }
.muestra.neutro { background: var(--linea-fuerte); }
.muestra.publico { background: var(--linea-fuerte); }
.muestra.sensible { background: var(--aviso); }
.muestra.cifrado { background: var(--sello); }
.muestra.marca { background: var(--marca); }
.muestra.punto { width: 9px; height: 9px; border-radius: 50%; background: var(--critico); }
.muestra.finde { background: var(--superficie-2); box-shadow: inset 0 0 0 1px var(--linea-fuerte); }
.muestra.limite { width: 18px; height: 0; border-radius: 0; background: none; border-top: 2px dashed var(--critico); }
/* Barra de cumplimiento con su línea de umbral, en miniatura. */
.muestra.umbral { position: relative; width: 28px; height: 8px; border-radius: 999px; background: linear-gradient(90deg, var(--bien) 0 55%, var(--superficie-3) 55%); }
.muestra.umbral::after { content: ''; position: absolute; left: 68%; top: -3px; bottom: -3px; width: 2px; border-radius: 2px; background: var(--tinta); opacity: 0.7; }
.candado { color: var(--sello); }

@media (max-width: 760px) {
  .cabeza { grid-template-columns: 1fr; }
  .acciones { justify-content: flex-start; }
  .pregunta { font-size: 16px; }
  .claves { grid-template-columns: 1fr; padding: 12px 14px; }
}
</style>
