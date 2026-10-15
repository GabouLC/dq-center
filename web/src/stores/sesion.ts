import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '@/servicios/api'
import { entrarConGoogle, firebaseConfigurado, salirFirebase, tokenFirebase, usuarioActual } from '@/servicios/firebase'

export type Modulo = { clave: string; nombre: string }
type Perfil = { email: string; rol: string; permisos: string[]; modulos: Modulo[] }

const CLAVE_DEMO = 'dqc.usuarioDemo'

function leerDemo(): string | null {
  try {
    return sessionStorage.getItem(CLAVE_DEMO)
  } catch {
    return null
  }
}

function guardarDemo(email: string | null): void {
  try {
    if (email) sessionStorage.setItem(CLAVE_DEMO, email)
    else sessionStorage.removeItem(CLAVE_DEMO)
  } catch {
    /* sin almacenamiento: la sesión dura lo que dure la pestaña */
  }
}

/** Sesión del usuario: quién es, su rol y los módulos que puede ver (HU-13). */
export const useSesion = defineStore('sesion', () => {
  const perfil = ref<Perfil | null>(null)
  const emailDemo = ref<string | null>(leerDemo())
  const restaurada = ref(false)

  const activa = computed(() => perfil.value !== null)
  const modulos = computed(() => perfil.value?.modulos ?? [])

  async function token(): Promise<string> {
    if (emailDemo.value) return `demo:${emailDemo.value}`
    return tokenFirebase()
  }

  async function cargarPerfil(): Promise<void> {
    perfil.value = await api<Perfil>('/api/v1/auth/me')
  }

  async function restaurar(): Promise<void> {
    if (restaurada.value) return
    restaurada.value = true
    try {
      if (emailDemo.value || (firebaseConfigurado && (await usuarioActual()))) await cargarPerfil()
    } catch {
      perfil.value = null
    }
  }

  async function entrarDemo(email: string): Promise<void> {
    emailDemo.value = email
    guardarDemo(email)
    await cargarPerfil()
  }

  async function entrarGoogle(): Promise<void> {
    emailDemo.value = null
    await entrarConGoogle()
    await cargarPerfil()
  }

  async function cerrar(): Promise<void> {
    perfil.value = null
    if (emailDemo.value) {
      emailDemo.value = null
      guardarDemo(null)
    } else if (firebaseConfigurado) {
      await salirFirebase()
    }
  }

  const puede = (permiso: string) => perfil.value?.permisos.includes(permiso) ?? false

  return { perfil, activa, modulos, token, restaurar, entrarDemo, entrarGoogle, cerrar, puede }
})
