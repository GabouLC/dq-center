<script setup lang="ts">
import {
  BadgeCheck, BookOpen, Database, FileText, KeyRound, LayoutDashboard, ListChecks, LogOut, Menu, Moon, PlayCircle,
  ScrollText, SlidersHorizontal, Sun, Users, Workflow, X,
} from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import IndicadorVivo from '@/componentes/IndicadorVivo.vue'
import LineaCortes from '@/componentes/LineaCortes.vue'
import { useSesion } from '@/stores/sesion'
import { useTema } from '@/stores/tema'
import { useVivo } from '@/stores/vivo'

const sesion = useSesion()
const tema = useTema()
const vivo = useVivo()
// La simulación en vivo se consulta mientras haya sesión.
watch(() => sesion.activa, (activa) => (activa ? vivo.iniciar() : vivo.detener()), { immediate: true })
const ruta = useRoute()
const router = useRouter()
const menuAbierto = ref(false)
watch(() => ruta.fullPath, () => (menuAbierto.value = false))

const ICONOS: Record<string, unknown> = {
  resumen: LayoutDashboard,
  validaciones: ListChecks,
  certificacion: BadgeCheck,
  fuentes: Database,
  contratos: FileText,
  linaje: Workflow,
  glosario: BookOpen,
  reglas: SlidersHorizontal,
  ejecuciones: PlayCircle,
  usuarios: Users,
  auditoria: ScrollText,
}
const ADMIN = new Set(['reglas', 'ejecuciones', 'usuarios', 'auditoria'])
const consulta = computed(() => sesion.modulos.filter((m) => !ADMIN.has(m.clave)))
const administracion = computed(() => sesion.modulos.filter((m) => ADMIN.has(m.clave)))

const publica = computed(() => ruta.meta.publica === true)
const conCorte = computed(() => ['resumen', 'validaciones', 'certificacion'].includes(String(ruta.meta.modulo)))
const NOMBRE_ROL: Record<string, string> = { admin: 'Administrador', gobierno: 'Gobierno de datos', lector: 'Lector' }
const iniciales = computed(() => (sesion.perfil?.email ?? '?').slice(0, 2).toUpperCase())

async function salir() {
  await sesion.cerrar()
  await router.push('/entrar')
}
</script>

<template>
  <RouterView v-if="publica" />
  <div v-else class="marco">
    <aside class="lateral" :class="{ abierto: menuAbierto }">
      <div class="marca">
        <svg viewBox="0 0 32 32" width="34" height="34" aria-hidden="true">
          <circle cx="16" cy="16" r="15" fill="var(--nav-2)" />
          <circle cx="16" cy="16" r="11.5" fill="none" stroke="var(--nav-acento)" stroke-width="1.6" stroke-dasharray="2.4 2" />
          <path d="M10.5 16.5l3.6 3.6 7.4-7.6" fill="none" stroke="#fff" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
        </svg>
        <div>
          <strong>Smart-DQ</strong>
          <span>Calidad y privacidad</span>
        </div>
        <button type="button" class="icono cerrar-menu" aria-label="Cerrar menú" @click="menuAbierto = false"><X :size="18" /></button>
      </div>
      <nav aria-label="Módulos">
        <RouterLink v-for="m in consulta" :key="m.clave" :to="`/${m.clave}`">
          <component :is="ICONOS[m.clave]" :size="18" :stroke-width="2" aria-hidden="true" />
          {{ m.nombre }}
        </RouterLink>
        <template v-if="administracion.length">
          <span class="grupo">Administración</span>
          <RouterLink v-for="m in administracion" :key="m.clave" :to="`/${m.clave}`">
            <component :is="ICONOS[m.clave]" :size="18" :stroke-width="2" aria-hidden="true" />
            {{ m.nombre }}
          </RouterLink>
        </template>
      </nav>
      <div class="pie">
        <span>Aseguradora ficticia</span>
        <span>Datos sintéticos · USMP 2026-II</span>
      </div>
    </aside>
    <div v-if="menuAbierto" class="velo" @click="menuAbierto = false" />

    <div class="principal">
      <header class="barra-superior">
        <button type="button" class="icono abrir-menu" aria-label="Abrir menú" @click="menuAbierto = true"><Menu :size="20" /></button>
        <LineaCortes v-if="conCorte" />
        <span v-else class="espacio" />
        <div class="fila acciones">
          <IndicadorVivo />
          <button
            type="button"
            class="icono fantasma"
            :aria-label="tema.esOscuro() ? 'Usar tema claro' : 'Usar tema oscuro'"
            :title="tema.esOscuro() ? 'Tema claro' : 'Tema oscuro'"
            @click="tema.alternar()"
          >
            <component :is="tema.esOscuro() ? Sun : Moon" :size="18" />
          </button>
          <div class="usuario">
            <span class="avatar" aria-hidden="true">{{ iniciales }}</span>
            <span class="datos">
              <strong>{{ sesion.perfil?.email }}</strong>
              <span>{{ NOMBRE_ROL[sesion.perfil?.rol ?? ''] }}</span>
            </span>
          </div>
          <RouterLink v-if="sesion.conClave && !sesion.debeCambiar" to="/clave" class="boton icono fantasma" aria-label="Cambiar contraseña" title="Cambiar contraseña">
            <KeyRound :size="18" />
          </RouterLink>
          <button type="button" class="icono fantasma" aria-label="Salir" title="Salir" @click="salir"><LogOut :size="18" /></button>
        </div>
      </header>
      <main class="contenido">
        <RouterView v-slot="{ Component }">
          <Transition name="vista" mode="out-in">
            <component :is="Component" :key="ruta.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
.marco { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; }
.lateral {
  background: var(--nav);
  color: var(--nav-tinta);
  padding: 20px 14px;
  display: flex;
  flex-direction: column;
  gap: 22px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
}
.marca { display: flex; gap: 11px; align-items: center; padding: 0 6px; color: #fff; }
.marca div { display: grid; line-height: 1.25; flex: 1; }
.marca strong { font-size: 17px; font-weight: 800; letter-spacing: -0.01em; }
.marca span { font-size: 12px; color: var(--nav-tinta); }
nav { display: grid; gap: 3px; }
nav a {
  display: flex;
  align-items: center;
  gap: 11px;
  color: var(--nav-tinta);
  padding: 9px 12px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
  transition: background 0.12s, color 0.12s;
}
nav a:hover { background: var(--nav-2); color: #fff; }
nav a.router-link-active { background: var(--nav-2); color: var(--nav-activo); box-shadow: inset 3px 0 0 var(--nav-acento); }
nav a.router-link-active svg { color: var(--nav-acento); }
.grupo { margin: 14px 12px 4px; font-size: 11.5px; font-weight: 700; color: #7f90ab; }
.pie { margin-top: auto; display: grid; gap: 2px; font-size: 11.5px; color: #7f90ab; padding: 0 8px; }
.cerrar-menu, .abrir-menu, .velo { display: none; }
.principal { min-width: 0; display: flex; flex-direction: column; }
.barra-superior {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 28px;
  background: color-mix(in srgb, var(--superficie) 86%, transparent);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--linea);
  position: sticky;
  top: 0;
  z-index: 10;
}
.espacio { flex: 1; }
.acciones { margin-left: auto; gap: 6px; flex-wrap: nowrap; }
.usuario { display: flex; align-items: center; gap: 9px; padding: 0 6px; }
.avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--marca);
  color: var(--sobre-marca);
  font-weight: 800;
  font-size: 12.5px;
}
.datos { display: grid; line-height: 1.2; }
.datos strong { font-size: 13px; }
.datos span { font-size: 12px; color: var(--tenue); }
.contenido { padding: 28px; max-width: 1320px; width: 100%; }

.vista-enter-active, .vista-leave-active { transition: opacity 0.16s ease, transform 0.16s ease; }
.vista-enter-from { opacity: 0; transform: translateY(6px); }
.vista-leave-to { opacity: 0; }

@media (max-width: 960px) {
  .marco { grid-template-columns: 1fr; }
  .lateral {
    position: fixed;
    inset: 0 auto 0 0;
    width: 272px;
    z-index: 30;
    transform: translateX(-100%);
    transition: transform 0.22s ease;
  }
  .lateral.abierto { transform: none; box-shadow: var(--sombra-alta); }
  .velo { display: block; position: fixed; inset: 0; background: rgb(8 16 28 / 0.45); z-index: 25; }
  .cerrar-menu { display: inline-flex; color: var(--nav-tinta); border-color: transparent; background: transparent; }
  .abrir-menu { display: inline-flex; }
  .barra-superior { padding: 10px 14px; flex-wrap: wrap; }
  .datos { display: none; }
  .contenido { padding: 18px 14px; }
}
</style>
