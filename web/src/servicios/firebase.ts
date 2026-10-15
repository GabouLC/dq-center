/**
 * Inicio de sesión con Google (Firebase Authentication). Solo se carga si las
 * variables VITE_FIREBASE_* están definidas; si no, el portal usa el modo demo.
 */
import type { Auth, User } from 'firebase/auth'

export const firebaseConfigurado = Boolean(import.meta.env.VITE_FIREBASE_API_KEY)

let auth: Auth | null = null

async function obtenerAuth(): Promise<Auth> {
  if (auth) return auth
  const { initializeApp } = await import('firebase/app')
  const { getAuth } = await import('firebase/auth')
  const app = initializeApp({
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  })
  auth = getAuth(app)
  return auth
}

export async function entrarConGoogle(): Promise<User> {
  const { GoogleAuthProvider, signInWithPopup } = await import('firebase/auth')
  const resultado = await signInWithPopup(await obtenerAuth(), new GoogleAuthProvider())
  return resultado.user
}

/** Espera a que Firebase restaure la sesión guardada (si la hay). */
export async function usuarioActual(): Promise<User | null> {
  const a = await obtenerAuth()
  await a.authStateReady()
  return a.currentUser
}

export async function tokenFirebase(): Promise<string> {
  const usuario = (await obtenerAuth()).currentUser
  if (!usuario) throw new Error('sin sesión de Firebase')
  return usuario.getIdToken()
}

export async function salirFirebase(): Promise<void> {
  const { signOut } = await import('firebase/auth')
  await signOut(await obtenerAuth())
}
