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
    // Sesión vencida o cerrada (cambio de contraseña, acceso retirado): de vuelta al inicio de sesión.
    const activa = sesion.activa
    await sesion.cerrar()
    if (activa) {
      const { router } = await import('@/router')
      await router.push({ path: '/entrar', query: { destino: router.currentRoute.value.fullPath, motivo: 'vencida' } })
    }
    throw new ErrorApi(401, 'La sesión venció. Vuelve a entrar.')
  }
  if (!respuesta.ok) throw await errorDe(respuesta)
  return respuesta.status === 204 ? (undefined as T) : ((await respuesta.json()) as T)
}

async function errorDe(respuesta: Response): Promise<ErrorApi> {
  const datos = await respuesta.json().catch(() => null)
  const mensaje = Array.isArray(datos?.message) ? datos.message.join(' · ') : (datos?.message ?? respuesta.statusText)
  return new ErrorApi(respuesta.status, String(mensaje))
}

/** Para las rutas públicas (antes de iniciar sesión); con cuerpo, es un POST. */
export async function apiPublica<T>(ruta: string, cuerpo?: unknown): Promise<T> {
  const respuesta = await fetch(BASE + ruta, cuerpo === undefined ? undefined : {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(cuerpo),
  })
  if (!respuesta.ok) throw await errorDe(respuesta)
  return (await respuesta.json()) as T
}
