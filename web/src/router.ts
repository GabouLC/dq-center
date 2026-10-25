import { createRouter, createWebHistory } from 'vue-router'
import { useSesion } from '@/stores/sesion'

declare module 'vue-router' {
  interface RouteMeta {
    publica?: boolean
    modulo?: string
    /** Título de la pestaña para las rutas que no son módulos del menú. */
    titulo?: string
  }
}

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/entrar', component: () => import('@/vistas/Entrar.vue'), meta: { publica: true, titulo: 'Iniciar sesión' } },
    { path: '/clave', component: () => import('@/vistas/CambiarClave.vue'), meta: { titulo: 'Cambiar contraseña' } },
    { path: '/', redirect: '/resumen' },
    { path: '/resumen', component: () => import('@/vistas/Resumen.vue'), meta: { modulo: 'resumen' } },
    { path: '/validaciones', component: () => import('@/vistas/Validaciones.vue'), meta: { modulo: 'validaciones' } },
    { path: '/certificacion', component: () => import('@/vistas/Certificacion.vue'), meta: { modulo: 'certificacion' } },
    { path: '/fuentes', component: () => import('@/vistas/Fuentes.vue'), meta: { modulo: 'fuentes' } },
    { path: '/contratos', component: () => import('@/vistas/Contratos.vue'), meta: { modulo: 'contratos' } },
    { path: '/linaje/:tabla?', component: () => import('@/vistas/Linaje.vue'), meta: { modulo: 'linaje' } },
    { path: '/glosario/:id?', component: () => import('@/vistas/Glosario.vue'), meta: { modulo: 'glosario' } },
    { path: '/reglas', component: () => import('@/vistas/Reglas.vue'), meta: { modulo: 'reglas' } },
    { path: '/ejecuciones', component: () => import('@/vistas/Ejecuciones.vue'), meta: { modulo: 'ejecuciones' } },
    { path: '/usuarios', component: () => import('@/vistas/Usuarios.vue'), meta: { modulo: 'usuarios' } },
    { path: '/auditoria', component: () => import('@/vistas/Auditoria.vue'), meta: { modulo: 'auditoria' } },
    { path: '/:pathMatch(.*)*', redirect: '/resumen' },
  ],
})

// Acceso cerrado por defecto: sin sesión se va a /entrar; con contraseña temporal, a /clave;
// sin el módulo, al primero permitido.
router.beforeEach(async (destino) => {
  const sesion = useSesion()
  await sesion.restaurar()
  if (destino.meta.publica) return sesion.activa ? '/resumen' : true
  if (!sesion.activa) return { path: '/entrar', query: { destino: destino.fullPath } }
  if (sesion.debeCambiar && destino.path !== '/clave') return { path: '/clave', query: { destino: destino.fullPath } }
  const modulo = destino.meta.modulo
  if (modulo && !sesion.modulos.some((m) => m.clave === modulo)) return `/${sesion.modulos[0]?.clave ?? 'resumen'}`
  return true
})

// Título de la pestaña: el mismo nombre del módulo que muestra el menú (viene de la API).
router.afterEach((destino) => {
  const nombre = useSesion().modulos.find((m) => m.clave === destino.meta.modulo)?.nombre ?? destino.meta.titulo
  document.title = nombre ? `${nombre} · Smart-DQ` : 'Smart-DQ · Calidad y privacidad de datos'
})
