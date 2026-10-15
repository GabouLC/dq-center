<script setup lang="ts">
import { BookOpen, LogIn, ShieldCheck, SlidersHorizontal } from 'lucide-vue-next'
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Sello from '@/componentes/Sello.vue'
import { apiPublica } from '@/servicios/api'
import { firebaseConfigurado } from '@/servicios/firebase'
import { useSesion } from '@/stores/sesion'

type UsuarioDemo = { email: string; rol: string }

const sesion = useSesion()
const router = useRouter()
const ruta = useRoute()
const demo = ref<UsuarioDemo[]>([])
const error = ref<string | null>(null)
const entrando = ref<string | null>(null)

const ROLES: Record<string, { nombre: string; texto: string; icono: unknown }> = {
  admin: { nombre: 'Administrador', texto: 'Configura reglas, lanza corridas y gestiona usuarios.', icono: SlidersHorizontal },
  gobierno: { nombre: 'Gobierno de datos', texto: 'Ve los campos sensibles y edita el glosario.', icono: BookOpen },
  lector: { nombre: 'Lector', texto: 'Consulta indicadores; los campos sensibles aparecen ocultos.', icono: ShieldCheck },
}

onMounted(async () => {
  if (!firebaseConfigurado) {
    try {
      demo.value = await apiPublica<UsuarioDemo[]>('/api/v1/auth/demo')
    } catch {
      error.value = 'No hay conexión con la API. Levántala con: python -m dqc.api'
    }
  }
})

async function entrar(clave: string, accion: () => Promise<void>) {
  entrando.value = clave
  error.value = null
  try {
    await accion()
    await router.push(String(ruta.query.destino ?? '/resumen'))
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    await sesion.cerrar()
  } finally {
    entrando.value = null
  }
}
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
      <h1>Cada dato llega a negocio con su sello de calidad y privacidad.</h1>
      <p>Ingesta validada, PII cifrada y certificación por corte, de RAW a BUSINESS.</p>
    </section>

    <section class="acceso">
      <div class="caja">
        <h2>Entrar al portal</h2>
        <button v-if="firebaseConfigurado" type="button" class="primario ancho" :disabled="!!entrando" @click="entrar('google', sesion.entrarGoogle)">
          <LogIn :size="17" /> Entrar con Google
        </button>
        <template v-else>
          <p class="secundario">Modo demostración: elige con qué rol entrar.</p>
          <div class="roles">
            <button
              v-for="u in demo"
              :key="u.email"
              type="button"
              class="rol"
              :disabled="!!entrando"
              @click="entrar(u.email, () => sesion.entrarDemo(u.email))"
            >
              <span class="icono-rol"><component :is="ROLES[u.rol]?.icono" :size="20" /></span>
              <span class="texto">
                <strong>{{ ROLES[u.rol]?.nombre ?? u.rol }}</strong>
                <span>{{ ROLES[u.rol]?.texto }}</span>
                <span class="tenue correo">{{ u.email }}</span>
              </span>
              <LogIn :size="17" class="ir" />
            </button>
          </div>
        </template>
        <p v-if="error" class="aviso-caja error" role="alert">{{ error }}</p>
        <p class="tenue nota">Aseguradora ficticia y datos sintéticos · Diseño e Implementación de Sistemas, USMP 2026-II</p>
      </div>
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
.caja { width: min(460px, 100%); display: grid; gap: 16px; }
.caja h2 { font-size: 24px; font-weight: 800; }
.ancho { width: 100%; justify-content: center; padding: 12px; }
.roles { display: grid; gap: 10px; }
.rol {
  display: grid;
  grid-template-columns: 44px 1fr auto;
  align-items: center;
  gap: 14px;
  text-align: left;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--superficie);
  box-shadow: var(--sombra);
  font-weight: 500;
}
.rol:hover { border-color: var(--marca); transform: translateY(-1px); box-shadow: var(--sombra-alta); color: inherit; }
.icono-rol { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; background: var(--marca-suave); color: var(--marca); }
.texto { display: grid; gap: 1px; font-size: 13px; color: var(--tinta-2); }
.texto strong { color: var(--tinta); font-size: 15px; }
.correo { font-size: 12px; }
.ir { color: var(--tenue); }
.rol:hover .ir { color: var(--marca); }
.nota { font-size: 12px; }
@media (max-width: 900px) {
  .entrada { grid-template-columns: 1fr; }
  .presentacion { padding: 84px 22px 32px; }
  .marca { left: 22px; top: 26px; }
  .presentacion h1 { font-size: 27px; }
  .sellos :deep(svg) { max-width: 90px; height: auto; }
}
</style>
