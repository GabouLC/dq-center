import { useSesion } from '@/stores/sesion'

const BASE = import.meta.env.VITE_API_URL ?? ''

export class ErrorApi extends Error {
  constructor(public estado: number, mensaje: string) {
    super(mensaje)
  }
}

type Opciones = {
  metodo?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  cuerpo?: unknown
  params?: Record<string, string | number | undefined | null>
}

/** Llama a la API con el token de la sesión. Los errores traen el mensaje de la API. */
export async function api<T>(ruta: string, { metodo = 'GET', cuerpo, params }: Opciones = {}): Promise<T> {
  const sesion = useSesion()
  const url = new URL(BASE + ruta, window.location.origin)
  for (const [clave, valor] of Object.entries(params ?? {})) {
    if (valor !== undefined && valor !== null && valor !== '') url.searchParams.set(clave, String(valor))
  }
  const respuesta = await fetch(url, {
    method: metodo,
    headers: {
      Authorization: `Bearer ${await sesion.token()}`,
      ...(cuerpo !== undefined ? { 'Content-Type': 'application/json' } : {}),
    },
    body: cuerpo !== undefined ? JSON.stringify(cuerpo) : undefined,
  })
  if (respuesta.status === 401) {
    await sesion.cerrar()
    throw new ErrorApi(401, 'La sesión venció. Vuelve a entrar.')
  }
  if (!respuesta.ok) {
    const datos = await respuesta.json().catch(() => null)
    const mensaje = Array.isArray(datos?.message) ? datos.message.join(' · ') : (datos?.message ?? respuesta.statusText)
    throw new ErrorApi(respuesta.status, String(mensaje))
  }
  return respuesta.status === 204 ? (undefined as T) : ((await respuesta.json()) as T)
}

/** Para las rutas públicas (antes de iniciar sesión). */
export async function apiPublica<T>(ruta: string): Promise<T> {
  const respuesta = await fetch(BASE + ruta)
  if (!respuesta.ok) throw new ErrorApi(respuesta.status, respuesta.statusText)
  return (await respuesta.json()) as T
}
