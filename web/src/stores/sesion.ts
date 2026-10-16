import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, apiPublica } from '@/servicios/api'
import { entrarConGoogle, firebaseConfigurado, salirFirebase, tokenFirebase, usuarioActual } from '@/servicios/firebase'

export type Modulo = { clave: string; nombre: string }
type Perfil = { email: string; rol: string; permisos: string[]; modulos: Modulo[]; debe_cambiar: boolean }
type Sesion = { token: string; expira: number; debe_cambiar: boolean }
type Guardada = { token: string; expira: number; recordar: boolean }

const CLAVE = 'dqc.sesion'

function almacen(recordar: boolean): Storage | null {
  try {
    return recordar ? window.localStorage : window.sessionStorage
  } catch {
    return null
  }
}

/** Con "mantener la sesión" el token va a localStorage; si no, dura lo que la pestaña. */
function leerGuardada(): Guardada | null {
  for (const recordar of [false, true]) {
    try {
      const a = almacen(recordar)
      const guardada = JSON.parse(a?.getItem(CLAVE) ?? 'null') as Guardada | null
      if (guardada && guardada.expira * 1000 > Date.now()) return { ...guardada, recordar }
      a?.removeItem(CLAVE)
    } catch {
      /* dato corrupto: no hay sesión guardada */
    }
  }
  return null
}

function guardar(sesion: Sesion | null, recordar = false): void {
  for (const r of [false, true]) {
    try {
      almacen(r)?.removeItem(CLAVE)
      if (sesion && r === recordar) almacen(r)?.setItem(CLAVE, JSON.stringify({ token: sesion.token, expira: sesion.expira }))
    } catch {
      /* sin almacenamiento: la sesión dura lo que dure la página */
    }
  }
}

/** Sesión del usuario: quién es, su rol y los módulos que puede ver (HU-13). */
export const useSesion = defineStore('sesion', () => {
  const guardada = leerGuardada()
  const perfil = ref<Perfil | null>(null)
  const tokenPropio = ref<string | null>(guardada?.token ?? null)
  const recordar = ref(guardada?.recordar ?? false)
  const restaurada = ref(false)

  const activa = computed(() => perfil.value !== null)
  const debeCambiar = computed(() => perfil.value?.debe_cambiar ?? false)
  // Con una contraseña temporal no se ve ningún módulo hasta cambiarla.
  const modulos = computed(() => (debeCambiar.value ? [] : (perfil.value?.modulos ?? [])))
  const conClave = computed(() => tokenPropio.value !== null)

  async function token(): Promise<string> {
    if (tokenPropio.value) return tokenPropio.value
    return tokenFirebase()
  }

  async function cargarPerfil(): Promise<void> {
    perfil.value = await api<Perfil>('/api/v1/auth/me')
  }

  async function restaurar(): Promise<void> {
    if (restaurada.value) return
    restaurada.value = true
    try {
      if (tokenPropio.value || (firebaseConfigurado && (await usuarioActual()))) await cargarPerfil()
    } catch {
      perfil.value = null
    }
  }

  function aplicar(sesion: Sesion, mantener: boolean): void {
    tokenPropio.value = sesion.token
    recordar.value = mantener
    guardar(sesion, mantener)
  }

  async function entrar(email: string, clave: string, mantener: boolean): Promise<void> {
    aplicar(await apiPublica<Sesion>('/api/v1/auth/sesion', { email, clave }), mantener)
    await cargarPerfil()
  }

  /** El token anterior queda cerrado en el servidor; se reemplaza por el que devuelve el cambio. */
  async function cambiarClave(actual: string, nueva: string): Promise<void> {
    aplicar(await api<Sesion>('/api/v1/auth/clave', { metodo: 'POST', cuerpo: { actual, nueva } }), recordar.value)
    await cargarPerfil()
  }

  async function entrarGoogle(): Promise<void> {
    tokenPropio.value = null
    guardar(null)
    await entrarConGoogle()
    await cargarPerfil()
  }

  async function cerrar(): Promise<void> {
    perfil.value = null
    if (tokenPropio.value) {
      tokenPropio.value = null
      guardar(null)
    } else if (firebaseConfigurado) {
      await salirFirebase()
    }
  }

  const puede = (permiso: string) => perfil.value?.permisos.includes(permiso) ?? false

  return { perfil, activa, debeCambiar, modulos, conClave, token, restaurar, entrar, cambiarClave, entrarGoogle, cerrar, puede }
})
