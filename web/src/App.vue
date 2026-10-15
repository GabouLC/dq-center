<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import SelectorCorte from '@/componentes/SelectorCorte.vue'
import { useSesion } from '@/stores/sesion'

const sesion = useSesion()
const ruta = useRoute()
const router = useRouter()

const publica = computed(() => ruta.meta.publica === true)
// Los módulos que dependen del corte muestran el selector.
const conCorte = computed(() => ['resumen', 'validaciones', 'certificacion'].includes(String(ruta.meta.modulo)))
const NOMBRE_ROL: Record<string, string> = { admin: 'Administrador', gobierno: 'Gobierno de datos', lector: 'Lector' }

async function salir() {
  await sesion.cerrar()
  await router.push('/entrar')
}
</script>

<template>
  <RouterView v-if="publica" />
  <div v-else class="marco">
    <aside class="lateral">
      <div class="marca">
        <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
          <rect width="32" height="32" rx="7" fill="var(--accent)" />
          <path d="M9 17l4.5 4.5L23 11" fill="none" stroke="var(--accent-fg)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
          <strong>Smart-DQ</strong>
          <span class="muted">Calidad y privacidad</span>
        </div>
      </div>
      <nav aria-label="Módulos">
        <RouterLink v-for="m in sesion.modulos" :key="m.clave" :to="`/${m.clave}`">{{ m.nombre }}</RouterLink>
      </nav>
      <p class="muted pie">Aseguradora ficticia · datos sintéticos</p>
    </aside>
    <div class="principal">
      <header class="barra-superior">
        <SelectorCorte v-if="conCorte" />
        <span v-else />
        <div class="fila">
          <span class="usuario">
            <strong>{{ sesion.perfil?.email }}</strong>
            <span class="chip acento">{{ NOMBRE_ROL[sesion.perfil?.rol ?? ''] }}</span>
          </span>
          <button type="button" @click="salir">Salir</button>
        </div>
      </header>
      <main class="contenido">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.marco { display: grid; grid-template-columns: 232px 1fr; min-height: 100%; }
.lateral {
  background: var(--surface);
  border-right: 1px solid var(--line);
  padding: 18px 12px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 0;
  height: 100vh;
}
.marca { display: flex; gap: 10px; align-items: center; padding: 0 6px; }
.marca div { display: grid; line-height: 1.2; }
.marca span { font-size: 12px; }
nav { display: grid; gap: 2px; }
nav a {
  color: var(--fg);
  text-decoration: none;
  padding: 7px 10px;
  border-radius: 8px;
}
nav a:hover { background: var(--surface-2); }
nav a.router-link-active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.pie { margin-top: auto; font-size: 12px; padding: 0 6px; }
.principal { min-width: 0; display: flex; flex-direction: column; }
.barra-superior {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 10px 24px;
  border-bottom: 1px solid var(--line);
  background: var(--surface);
  position: sticky;
  top: 0;
  z-index: 5;
}
.usuario { display: flex; gap: 8px; align-items: center; font-size: 13px; }
.contenido { padding: 24px; max-width: 1280px; width: 100%; }
@media (max-width: 900px) {
  .marco { grid-template-columns: 1fr; }
  .lateral { position: static; height: auto; }
  nav { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); }
  .pie { display: none; }
  .contenido { padding: 16px; }
  .barra-superior { padding: 10px 16px; }
  .usuario strong { display: none; }
}
</style>
