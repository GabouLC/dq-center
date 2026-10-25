import { ref, watch, type Ref } from 'vue'
import { useSesion } from '@/stores/sesion'

/** Clave de una preferencia de este usuario en el navegador: dqc.<nombre>.<correo>. */
function claveDe(nombre: string): string {
  return `dqc.${nombre}.${useSesion().perfil?.email ?? 'anonimo'}`
}

export function leerPreferencia<T>(nombre: string, defecto: T): T {
  try {
    const guardada = localStorage.getItem(claveDe(nombre))
    return guardada === null ? defecto : (JSON.parse(guardada) as T)
  } catch {
    return defecto
  }
}

export function guardarPreferencia(nombre: string, valor: unknown): void {
  try {
    localStorage.setItem(claveDe(nombre), JSON.stringify(valor))
  } catch {
    /* sin almacenamiento: la preferencia dura lo que la página */
  }
}

/** Preferencia de este usuario que se recuerda entre visitas (por ejemplo, un panel abierto). */
export function usarPreferencia<T>(nombre: string, defecto: T): Ref<T> {
  const valor = ref(leerPreferencia(nombre, defecto)) as Ref<T>
  watch(valor, (v) => guardarPreferencia(nombre, v), { deep: true })
  return valor
}
