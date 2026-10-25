import { ref, watch, type Ref, type WatchSource } from 'vue'
import { useVivo } from '@/stores/vivo'

/**
 * Motivo de un error en lenguaje claro. Si el navegador no llega al servidor, fetch
 * falla con TypeError ("Failed to fetch"): eso se muestra como falta de conexión.
 */
export function mensajeDeError(e: unknown): string {
  if (e instanceof TypeError) return 'no hay conexión con el servidor.'
  return e instanceof Error ? e.message : String(e)
}

/**
 * Carga datos de la API con estado de carga y error, y los vuelve a pedir
 * cuando cambian las dependencias (por ejemplo, el corte elegido) o cuando la
 * simulación en vivo publica un corte nuevo; esa recarga es silenciosa.
 */
export function usarCarga<T>(cargar: () => Promise<T>, dependencias: WatchSource[] = []) {
  const datos = ref<T | null>(null) as Ref<T | null>
  const cargando = ref(false)
  const error = ref<string | null>(null)

  async function recargar(silenciosa = false): Promise<void> {
    if (!silenciosa) cargando.value = true
    error.value = null
    try {
      datos.value = await cargar()
    } catch (e) {
      error.value = mensajeDeError(e)
    } finally {
      cargando.value = false
    }
  }

  watch(dependencias, () => recargar(), { immediate: true })
  watch(() => useVivo().version, () => recargar(true))
  return { datos, cargando, error, recargar: () => recargar() }
}
