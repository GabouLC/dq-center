<script setup lang="ts">
import { CircleAlert, Info, LoaderCircle, LogIn, Mail } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CampoClave from '@/componentes/CampoClave.vue'
import Sello from '@/componentes/Sello.vue'
import { firebaseConfigurado } from '@/servicios/firebase'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const router = useRouter()
const ruta = useRoute()

const email = ref('')
const clave = ref('')
const mantener = ref(false)
const error = ref<string | null>(null)
const entrando = ref(false)
const sacudir = ref(false)
const vencida = computed(() => ruta.query.motivo === 'vencida')

/** Solo rutas internas: un ?destino=https://… no saca al usuario del portal. */
function destino(): string {
  const d = ruta.query.destino
  return typeof d === 'string' && d.startsWith('/') && !d.startsWith('//') ? d : '/resumen'
}

async function intentar(accion: () => Promise<void>) {
  if (entrando.value) return
  entrando.value = true
  error.value = null
  try {
    await accion()
    await router.replace(destino())
  } catch (e) {
    error.value = e instanceof TypeError
      ? 'No pudimos conectar con el servidor. Intenta en un momento; si sigue, avisa al administrador.'
      : e instanceof Error ? e.message : String(e)
    clave.value = ''
    sacudir.value = true
    await sesion.cerrar()
  } finally {
    entrando.value = false
  }
}

const entrar = () => intentar(() => sesion.entrar(email.value.trim(), clave.value, mantener.value))
const entrarGoogle = () => intentar(sesion.entrarGoogle)
</script>

<template>
  <main class="entrada">
    <section class="presentacion">
      <div class="marca">
        <svg viewBox="0 0 32 32" width="40" height="40" aria-hidden="true">
          <circle cx="16" cy="16" r="15" fill="#18304f" />
          <circle cx="16" cy="16" r="11.5" fill="none" stroke="#5fa8ff" stroke-width="1.6" stroke-dasharray="2.4 2" />
          <path d="M10.5 16.5l3.6 3.6 7.4-7.6" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <strong>Smart-DQ</strong>
      </div>
      <div class="sellos" aria-hidden="true">
        <Sello estado="CERTIFICADO" tabla="Póliza" :tamano="150" />
        <Sello estado="CERTIFICADO_CON_OBSERVACIONES" tabla="Persona" :tamano="120" />
        <Sello estado="NO_CERTIFICADO" tabla="Siniestro" :tamano="104" />
      </div>
      <h1>Cada dato llega a negocio certificado en calidad y privacidad.</h1>
      <p>Ingesta validada, datos personales cifrados y certificación diaria, de RAW a BUSINESS.</p>
    </section>

    <section class="acceso">
      <form class="caja" :class="{ sacudir }" @submit.prevent="entrar" @animationend="sacudir = false">
        <div class="titulo">
          <h2>Iniciar sesión</h2>
          <p class="secundario">Entra con la cuenta que te dio el administrador del portal.</p>
        </div>

        <p v-if="vencida && !error" class="aviso-caja info" role="status">
          <Info :size="17" />Tu sesión venció o se cerró. Vuelve a entrar para continuar.
        </p>

        <div class="campo-entrada">
          <label for="email" class="etiqueta">Correo</label>
          <div class="caja-entrada">
            <Mail :size="17" aria-hidden="true" />
            <input
              id="email"
              v-model="email"
              type="email"
              autocomplete="username"
              placeholder="nombre@empresa.com"
              spellcheck="false"
              required
              autofocus
            />
          </div>
        </div>
        <CampoClave id="clave" v-model="clave" etiqueta="Contraseña" autocomplete="current-password" />

        <label class="recordar">
          <input v-model="mantener" type="checkbox" />
          Mantener la sesión en este equipo
        </label>

        <p v-if="error" class="aviso-caja error" role="alert"><CircleAlert :size="17" />{{ error }}</p>

        <button type="submit" class="primario ancho" :disabled="entrando">
          <LoaderCircle v-if="entrando" :size="18" class="girando" />
          <LogIn v-else :size="18" />
          {{ entrando ? 'Verificando…' : 'Entrar' }}
        </button>

        <template v-if="firebaseConfigurado">
          <div class="separador"><span>o</span></div>
          <button type="button" class="ancho" :disabled="entrando" @click="entrarGoogle">Continuar con Google</button>
        </template>

        <p class="ayuda">
          ¿No tienes cuenta u olvidaste tu contraseña? Pídesela a un administrador del portal.
          El acceso es cerrado por defecto y cada intento queda en la auditoría.
        </p>
        <p class="tenue nota">Aseguradora ficticia y datos sintéticos · Diseño e Implementación de Sistemas, USMP 2026-II</p>
      </form>
    </section>
  </main>
</template>

<style scoped>
.entrada { min-height: 100vh; display: grid; grid-template-columns: 1.1fr 1fr; }
.presentacion {
  background: #10213b;
  color: #dbe5f3;
  padding: 44px 56px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.marca { display: flex; align-items: center; gap: 10px; color: #fff; font-size: 19px; position: absolute; top: 36px; left: 56px; }
.sellos { display: flex; align-items: flex-end; gap: 4px; margin-bottom: 8px; }
.sellos :deep(figcaption) { color: #dbe5f3; }
.sellos :deep(figcaption span) { color: #b9c7dc !important; }
.presentacion h1 { color: #fff; font-size: 36px; max-width: 18ch; letter-spacing: -0.03em; }
.presentacion p { font-size: 16px; max-width: 46ch; color: #b9c7dc; }
.acceso { display: grid; place-items: center; padding: 32px 20px; }
.caja { width: min(400px, 100%); display: grid; gap: 18px; }
.titulo { display: grid; gap: 4px; }
.caja h2 { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; }
.ancho { width: 100%; justify-content: center; padding: 12px; font-size: 15px; border-radius: 12px; }
.recordar { display: flex; align-items: center; gap: 9px; font-size: 13.5px; color: var(--tinta-2); cursor: pointer; width: fit-content; }
.separador { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px; color: var(--tenue); font-size: 12.5px; }
.separador::before, .separador::after { content: ''; height: 1px; background: var(--linea); }
.ayuda { font-size: 13px; color: var(--tinta-2); padding-top: 14px; border-top: 1px solid var(--linea); }
.nota { font-size: 12px; }
.sacudir { animation: sacudir 0.36s cubic-bezier(0.36, 0.07, 0.19, 0.97); }
@keyframes sacudir {
  20%, 60% { transform: translateX(-6px); }
  40%, 80% { transform: translateX(6px); }
}
@media (max-width: 900px) {
  .entrada { grid-template-columns: 1fr; }
  .presentacion { padding: 84px 22px 32px; }
  .marca { left: 22px; top: 26px; }
  .presentacion h1 { font-size: 27px; }
  .sellos :deep(svg) { max-width: 90px; height: auto; }
}
</style>
