<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { apiPublica } from '@/servicios/api'
import { firebaseConfigurado } from '@/servicios/firebase'
import { useSesion } from '@/stores/sesion'

type UsuarioDemo = { email: string; rol: string }

const sesion = useSesion()
const router = useRouter()
const ruta = useRoute()
const demo = ref<UsuarioDemo[]>([])
const error = ref<string | null>(null)
const entrando = ref(false)

const DESCRIPCION: Record<string, string> = {
  admin: 'Configura reglas, lanza corridas y administra usuarios.',
  gobierno: 'Ve los campos sensibles y edita el glosario.',
  lector: 'Consulta indicadores; los campos sensibles aparecen ocultos.',
}

onMounted(async () => {
  if (!firebaseConfigurado) {
    try {
      demo.value = await apiPublica<UsuarioDemo[]>('/api/v1/auth/demo')
    } catch {
      error.value = 'No se pudo conectar con la API. ¿Está corriendo python -m dqc.api?'
    }
  }
})

async function entrar(accion: () => Promise<void>) {
  entrando.value = true
  error.value = null
  try {
    await accion()
    await router.push(String(ruta.query.destino ?? '/resumen'))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    await sesion.cerrar()
  } finally {
    entrando.value = false
  }
}
</script>

<template>
  <main class="entrada">
    <section class="tarjeta panel">
      <div class="fila">
        <svg viewBox="0 0 32 32" width="36" height="36" aria-hidden="true">
          <rect width="32" height="32" rx="7" fill="var(--accent)" />
          <path d="M9 17l4.5 4.5L23 11" fill="none" stroke="var(--accent-fg)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
          <h1>Smart-DQ</h1>
          <p class="muted">Portal de calidad y privacidad de datos</p>
        </div>
      </div>

      <button v-if="firebaseConfigurado" type="button" class="primario ancho" :disabled="entrando" @click="entrar(sesion.entrarGoogle)">
        Entrar con Google
      </button>

      <template v-else>
        <p class="muted">Modo demostración: elige un usuario para probar cada rol.</p>
        <div class="usuarios">
          <button
            v-for="u in demo"
            :key="u.email"
            type="button"
            class="usuario"
            :disabled="entrando"
            @click="entrar(() => sesion.entrarDemo(u.email))"
          >
            <strong>{{ u.rol }}</strong>
            <span class="mono">{{ u.email }}</span>
            <span class="muted">{{ DESCRIPCION[u.rol] }}</span>
          </button>
        </div>
      </template>

      <p v-if="error" class="aviso error" role="alert">{{ error }}</p>
      <p class="muted nota">Aseguradora ficticia y datos sintéticos · Diseño e Implementación de Sistemas, USMP 2026-II</p>
    </section>
  </main>
</template>

<style scoped>
.entrada { min-height: 100%; display: grid; place-items: center; padding: 24px 16px; }
.panel { width: min(460px, 100%); display: grid; gap: 18px; padding: 28px; }
.ancho { width: 100%; padding: 10px; }
.usuarios { display: grid; gap: 8px; }
.usuario { display: grid; gap: 2px; text-align: left; padding: 12px 14px; }
.usuario strong { text-transform: capitalize; }
.usuario .muted { font-size: 12.5px; }
.nota { font-size: 12px; }
</style>
