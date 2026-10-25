<script setup lang="ts">
import { CircleHelp, KeyRound, LogOut, Menu, Moon, Sun, X } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import IndicadorVivo from '@/componentes/IndicadorVivo.vue'
import LineaCortes from '@/componentes/LineaCortes.vue'
import RecorridoGuiado from '@/componentes/RecorridoGuiado.vue'
import { GRUPOS, MODULOS } from '@/navegacion'
import { useRecorrido } from '@/stores/recorrido'
import { useSesion, type Modulo } from '@/stores/sesion'
import { useTema } from '@/stores/tema'
import { useVivo } from '@/stores/vivo'

const sesion = useSesion()
const tema = useTema()
const vivo = useVivo()
const recorrido = useRecorrido()
// La simulación en vivo se consulta mientras haya sesión.
watch(() => sesion.activa, (activa) => (activa ? vivo.iniciar() : vivo.detener()), { immediate: true })
const ruta = useRoute()
const router = useRouter()
const menuAbierto = ref(false)
watch(() => ruta.fullPath, () => {
  menuAbierto.value = false
  ocultarAyuda(true)
})

// Primera visita al Resumen: recorrido guiado (una vez por usuario).
watch(
  () => [sesion.activa, sesion.debeCambiar, ruta.path] as const,
  ([activa, debeCambiar, camino]) => {
    if (activa && !debeCambiar && camino === '/resumen') recorrido.abrirSiEsPrimeraVez()
  },
  { immediate: true },
)

// Menú agrupado por objetivo; los módulos (y sus nombres) los decide la API según el rol.
type GrupoNav = { clave: string; nombre: string; modulos: Modulo[] }
const grupos = computed<GrupoNav[]>(() => {
  const lista: GrupoNav[] = GRUPOS.map((g) => ({
    clave: g.clave,
    nombre: g.nombre,
    modulos: sesion.modulos.filter((m) => MODULOS[m.clave]?.grupo === g.clave),
  }))
  const otros = sesion.modulos.filter((m) => !MODULOS[m.clave])
  if (otros.length) lista.push({ clave: 'otros', nombre: 'Otros', modulos: otros })
  return lista.filter((g) => g.modulos.length)
})

// Para qué sirve cada opción: globo al pasar el puntero o al llegar con el teclado (escritorio).
// El primero espera un poco (no salta al pasar de largo); los siguientes aparecen al instante.
const ayuda = ref<{ texto: string; top: number; left: number } | null>(null)
let esperaAyuda = 0
let esperaOcultar = 0
function mostrarAyuda(clave: string, evento: Event, inmediata = false) {
  const texto = MODULOS[clave]?.descripcion
  if (!texto || window.matchMedia('(max-width: 960px)').matches) return
  const enlace = evento.currentTarget as HTMLElement
  clearTimeout(esperaAyuda)
  clearTimeout(esperaOcultar)
  const poner = () => {
    const r = enlace.getBoundingClientRect()
    const lateral = enlace.closest('.lateral')?.getBoundingClientRect()
    ayuda.value = { texto, top: r.top + r.height / 2, left: (lateral?.right ?? r.right) + 8 }
  }
  if (inmediata || ayuda.value) poner()
  else esperaAyuda = window.setTimeout(poner, 350)
}
function alEnfocar(clave: string, evento: FocusEvent) {
  if ((evento.currentTarget as HTMLElement).matches(':focus-visible')) mostrarAyuda(clave, evento, true)
}
function ocultarAyuda(ya = false) {
  clearTimeout(esperaAyuda)
  clearTimeout(esperaOcultar)
  if (ya) ayuda.value = null
  else esperaOcultar = window.setTimeout(() => (ayuda.value = null), 90)
}

const publica = computed(() => ruta.meta.publica === true)
const conCorte = computed(() => ['resumen', 'validaciones', 'certificacion'].includes(String(ruta.meta.modulo)))
const NOMBRE_ROL: Record<string, string> = { admin: 'Administrador', gobierno: 'Gobierno de datos', lector: 'Lector' }
const iniciales = computed(() => (sesion.perfil?.email ?? '?').slice(0, 2).toUpperCase())
// La vista se reutiliza al cambiar solo el parámetro (otra tabla en Linaje, otro término en el Glosario).
const claveVista = computed(() => String(ruta.meta.modulo ?? ruta.path))

async function salir() {
  await sesion.cerrar()
  await router.push('/entrar')
}

/** Enlace "Saltar al contenido": lleva el foco al área principal sin tocar la URL. */
function irAlContenido() {
  document.getElementById('contenido')?.focus()
}
</script>

<template>
  <RouterView v-if="publica" />
  <div v-else class="marco">
    <a href="#contenido" class="saltar" @click.prevent="irAlContenido">Saltar al contenido</a>
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
      <nav aria-label="Módulos" data-recorrido="menu">
        <div v-for="g in grupos" :key="g.clave" class="grupo-nav" role="group" :aria-labelledby="`grupo-${g.clave}`">
          <span :id="`grupo-${g.clave}`" class="grupo" :class="g.clave"><i class="punto-grupo" aria-hidden="true" />{{ g.nombre }}</span>
          <RouterLink
            v-for="m in g.modulos"
            :key="m.clave"
            :to="`/${m.clave}`"
            :aria-label="m.nombre"
            :aria-describedby="MODULOS[m.clave] ? `desc-${m.clave}` : undefined"
            @mouseenter="mostrarAyuda(m.clave, $event)"
            @mouseleave="ocultarAyuda()"
            @focus="alEnfocar(m.clave, $event)"
            @blur="ocultarAyuda()"
          >
            <component :is="MODULOS[m.clave]?.icono" v-if="MODULOS[m.clave]" :size="18" :stroke-width="2" aria-hidden="true" />
            <span class="textos">
              <span>{{ m.nombre }}</span>
              <span v-if="MODULOS[m.clave]" :id="`desc-${m.clave}`" class="descripcion">{{ MODULOS[m.clave].descripcion }}</span>
            </span>
          </RouterLink>
        </div>
      </nav>
      <div class="pie">
        <span>Aseguradora ficticia</span>
        <span>Datos sintéticos · USMP 2026-II</span>
      </div>
    </aside>
    <Transition name="ayuda">
      <div v-if="ayuda" class="ayuda-nav" :style="{ top: `${ayuda.top}px`, left: `${ayuda.left}px` }" aria-hidden="true">{{ ayuda.texto }}</div>
    </Transition>
    <Transition name="velo">
      <div v-if="menuAbierto" class="velo" @click="menuAbierto = false" />
    </Transition>

    <div class="principal">
      <header class="barra-superior">
        <button type="button" class="icono abrir-menu" aria-label="Abrir menú" data-recorrido="menu-movil" @click="menuAbierto = true"><Menu :size="20" /></button>
        <LineaCortes v-if="conCorte" data-recorrido="linea" />
        <span v-else class="espacio" />
        <div class="fila acciones">
          <IndicadorVivo />
          <button
            id="boton-recorrido"
            type="button"
            class="icono fantasma"
            aria-label="Ver recorrido"
            title="Ver recorrido: qué muestra el portal y cómo se lee"
            @click="recorrido.abrir()"
          >
            <CircleHelp :size="18" />
          </button>
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
      <main id="contenido" class="contenido" tabindex="-1">
        <RouterView v-slot="{ Component }">
          <Transition name="vista" mode="out-in">
            <component :is="Component" :key="claveVista" />
          </Transition>
        </RouterView>
      </main>
    </div>
    <RecorridoGuiado v-if="sesion.activa && !sesion.debeCambiar" />
  </div>
</template>

<style scoped>
.marco { display: grid; grid-template-columns: 248px 1fr; min-height: 100vh; }
/* Navegación: azul marino con profundidad (degradado y un brillo arriba). */
.lateral {
  background:
    radial-gradient(120% 50% at 0% 0%, rgb(95 168 255 / 0.14) 0%, transparent 60%),
    linear-gradient(180deg, var(--nav) 0%, color-mix(in srgb, var(--nav) 82%, #000) 100%);
  border-right: 1px solid rgb(255 255 255 / 0.04);
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
nav { display: grid; gap: 14px; }
.grupo-nav { display: grid; gap: 2px; }
.grupo { display: flex; align-items: center; gap: 8px; margin: 0 12px 4px; font-size: 11.5px; font-weight: 700; color: #8a9bb5; }
/* El punto del grupo repite el color del mosaico de sus secciones. */
.punto-grupo { width: 6px; height: 6px; border-radius: 2px; background: #6cb2ff; }
.grupo.origen .punto-grupo { background: #4fd1d9; }
.grupo.admin .punto-grupo { background: #a9b9d8; }
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
  transition: background-color 0.12s ease, color 0.12s ease;
}
nav a svg { flex: none; }
nav a:hover { background: rgb(255 255 255 / 0.06); color: #fff; text-decoration: none; }
/* Activo: una pastilla iluminada con su acento a la izquierda. */
nav a.router-link-active {
  position: relative; color: var(--nav-activo);
  background: linear-gradient(90deg, rgb(95 168 255 / 0.24), rgb(95 168 255 / 0.08));
  box-shadow: inset 0 0 0 1px rgb(95 168 255 / 0.22), 0 6px 16px -10px rgb(0 0 0 / 0.6);
}
nav a.router-link-active::before {
  content: ''; position: absolute; left: 0; top: 9px; bottom: 9px; width: 3px; border-radius: 0 3px 3px 0; background: var(--nav-acento);
}
nav a.router-link-active svg { color: var(--nav-acento); }
.textos { display: grid; min-width: 0; line-height: 1.3; }
/* En escritorio la descripción la lee el lector de pantalla y se ve en el globo; en el menú móvil, debajo del nombre. */
.descripcion { position: absolute; width: 1px; height: 1px; overflow: hidden; clip-path: inset(50%); white-space: nowrap; }
.pie { margin-top: auto; display: grid; gap: 2px; font-size: 11.5px; color: #8a9bb5; padding: 0 8px; }
.cerrar-menu, .abrir-menu, .velo { display: none; }

.ayuda-nav {
  position: fixed; z-index: 50; transform: translateY(-50%); pointer-events: none;
  max-width: 240px; padding: 7px 11px; border-radius: 9px; font-size: 12.5px; font-weight: 600; line-height: 1.35;
  background: var(--tinta); color: var(--superficie); box-shadow: var(--sombra-alta);
}
.ayuda-nav::before {
  content: ''; position: absolute; left: -4px; top: 50%; width: 9px; height: 9px; border-radius: 2px;
  background: inherit; transform: translateY(-50%) rotate(45deg);
}
.ayuda-enter-active { transition: opacity 0.14s var(--ease-out), translate 0.14s var(--ease-out); }
.ayuda-leave-active { transition: opacity 0.1s ease; }
.ayuda-enter-from { opacity: 0; translate: -4px 0; }
.ayuda-leave-to { opacity: 0; }

.principal { min-width: 0; display: flex; flex-direction: column; }
.barra-superior {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 28px;
  background: color-mix(in srgb, var(--superficie) 80%, transparent);
  backdrop-filter: saturate(1.5) blur(14px);
  border-bottom: 1px solid color-mix(in srgb, var(--linea) 70%, transparent);
  box-shadow: 0 10px 24px -20px rgb(15 27 45 / 0.45);
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
  background: linear-gradient(140deg, var(--hero-3), var(--hero-1));
  color: #fff;
  box-shadow: 0 0 0 2px var(--superficie), 0 0 0 3px color-mix(in srgb, var(--marca) 40%, transparent);
  font-weight: 800;
  font-size: 12.5px;
}
.datos { display: grid; line-height: 1.2; }
.datos strong { font-size: 13px; }
.datos span { font-size: 12px; color: var(--tenue); }
.contenido { padding: 26px 28px 40px; max-width: 1320px; width: 100%; }
/* El área principal recibe el foco solo como destino del enlace "Saltar al contenido". */
.contenido:focus, .contenido:focus-visible { outline: none; }
.saltar {
  position: fixed;
  top: -60px;
  left: 12px;
  z-index: 100;
  padding: 9px 16px;
  border-radius: 10px;
  background: var(--superficie);
  color: var(--marca);
  font-weight: 700;
  box-shadow: var(--sombra-alta);
}
.saltar:focus { top: 12px; }

/* Cambio de vista: la nueva entra con un leve deslizamiento; la anterior se va más rápido. */
.vista-enter-active { transition: opacity 0.2s var(--ease-out), transform 0.2s var(--ease-out); }
.vista-leave-active { transition: opacity 0.12s ease; }
.vista-enter-from { opacity: 0; transform: translateY(8px); }
.vista-leave-to { opacity: 0; }

/* En capturas de página completa, la columna del menú sigue hasta abajo. */
@media (min-width: 961px) {
  .marco { background: linear-gradient(90deg, color-mix(in srgb, var(--nav) 82%, #000) 0 248px, transparent 248px); }
}
@media (max-width: 960px) {
  .marco { grid-template-columns: 1fr; }
  .lateral {
    position: fixed;
    inset: 0 auto 0 0;
    width: 286px;
    z-index: 30;
    transform: translateX(-100%);
    /* Cerrado no se ve ni recibe foco; visibility espera a que termine la animación. */
    visibility: hidden;
    transition: transform 0.26s var(--ease-out), visibility 0s linear 0.26s;
  }
  .lateral.abierto { transform: none; visibility: visible; box-shadow: var(--sombra-alta); transition-delay: 0s; }
  .velo { display: block; position: fixed; inset: 0; background: rgb(8 16 28 / 0.45); z-index: 25; }
  .velo-enter-active, .velo-leave-active { transition: opacity 0.22s ease; }
  .velo-enter-from, .velo-leave-to { opacity: 0; }
  .descripcion { position: static; width: auto; height: auto; overflow: visible; clip-path: none; white-space: normal; font-size: 12px; font-weight: 500; color: #93a4bf; }
  nav a.router-link-active .descripcion { color: var(--nav-tinta); }
  .ayuda-nav { display: none; }
  .cerrar-menu { display: inline-flex; color: var(--nav-tinta); border-color: transparent; background: transparent; }
  .abrir-menu { display: inline-flex; }
  .barra-superior { padding: 10px 14px; flex-wrap: wrap; }
  .datos { display: none; }
  .contenido { padding: 18px 14px; }
}
</style>
