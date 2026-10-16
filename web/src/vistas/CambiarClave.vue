<script setup lang="ts">
import { Circle, CircleAlert, CircleCheck, KeyRound, LoaderCircle } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CampoClave from '@/componentes/CampoClave.vue'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const router = useRouter()
const ruta = useRoute()

const actual = ref('')
const nueva = ref('')
const repetir = ref('')
const guardando = ref(false)
const error = ref<string | null>(null)
const hecho = ref(false)
const temporal = sesion.debeCambiar

// Las mismas reglas que valida la API (dqc.api.autenticacion.problemas_de_clave).
const requisitos = computed(() => {
  const usuario = (sesion.perfil?.email ?? '').split('@')[0].toLowerCase()
  return [
    { texto: 'Al menos 10 caracteres', ok: nueva.value.length >= 10 },
    { texto: 'No contiene tu usuario', ok: nueva.value.length > 0 && !(usuario && nueva.value.toLowerCase().includes(usuario)) },
    { texto: 'No es repetitiva', ok: new Set(nueva.value).size >= 4 },
    { texto: 'Distinta de la actual', ok: nueva.value.length > 0 && nueva.value !== actual.value },
    { texto: 'Las dos coinciden', ok: nueva.value.length > 0 && nueva.value === repetir.value },
  ]
})
const listo = computed(() => actual.value.length > 0 && requisitos.value.every((r) => r.ok))

function destino(): string {
  const d = ruta.query.destino
  return typeof d === 'string' && d.startsWith('/') && !d.startsWith('//') && d !== '/clave' ? d : '/resumen'
}

async function guardar() {
  if (!listo.value || guardando.value) return
  guardando.value = true
  error.value = null
  try {
    await sesion.cambiarClave(actual.value, nueva.value)
    actual.value = nueva.value = repetir.value = ''
    if (temporal) await router.replace(destino())
    else hecho.value = true
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <div class="pila angosta">
    <div class="encabezado">
      <div>
        <h1>{{ temporal ? 'Crea tu contraseña' : 'Cambiar contraseña' }}</h1>
        <p>Al guardarla se cierran las demás sesiones abiertas con tu cuenta.</p>
      </div>
    </div>

    <p v-if="temporal" class="aviso-caja">
      <KeyRound :size="17" />Entraste con una contraseña temporal. Crea una propia para empezar a usar el portal.
    </p>
    <p v-if="hecho" class="aviso-caja bien" role="status"><CircleCheck :size="17" />Listo: tu contraseña cambió.</p>

    <form class="panel formulario" @submit.prevent="guardar">
      <CampoClave id="actual" v-model="actual" :etiqueta="temporal ? 'Contraseña temporal' : 'Contraseña actual'" autocomplete="current-password" />
      <CampoClave id="nueva" v-model="nueva" etiqueta="Contraseña nueva" autocomplete="new-password" />
      <CampoClave id="repetir" v-model="repetir" etiqueta="Repite la contraseña nueva" autocomplete="new-password" />

      <ul class="requisitos" aria-label="Requisitos de la contraseña">
        <li v-for="r in requisitos" :key="r.texto" :class="{ cumple: r.ok }">
          <component :is="r.ok ? CircleCheck : Circle" :size="15" aria-hidden="true" />
          {{ r.texto }}<span class="sr">{{ r.ok ? ': cumple' : ': pendiente' }}</span>
        </li>
      </ul>
      <p class="tenue consejo">Una frase de varias palabras es más fácil de recordar y más difícil de adivinar.</p>

      <p v-if="error" class="aviso-caja error" role="alert"><CircleAlert :size="17" />{{ error }}</p>

      <div class="fila">
        <button type="submit" class="primario" :disabled="!listo || guardando">
          <LoaderCircle v-if="guardando" :size="17" class="girando" />
          <KeyRound v-else :size="17" />
          Guardar contraseña
        </button>
        <button v-if="!temporal" type="button" class="fantasma" @click="router.back()">Volver</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.angosta { max-width: 560px; }
.formulario { display: grid; gap: 16px; padding: 22px; }
.requisitos { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 6px 14px; padding: 0; margin: 0; }
.requisitos li { display: flex; align-items: center; gap: 7px; font-size: 13px; color: var(--tenue); transition: color 0.15s; }
.requisitos li.cumple { color: var(--bien-texto); }
.requisitos li.cumple svg { color: var(--bien); }
.consejo { font-size: 12.5px; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
</style>
