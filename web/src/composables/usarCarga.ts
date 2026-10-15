import { ref, watch, type Ref, type WatchSource } from 'vue'

/**
 * Carga datos de la API con estado de carga y error, y los vuelve a pedir
 * cuando cambian las dependencias (por ejemplo, el corte elegido).
 */
export function usarCarga<T>(cargar: () => Promise<T>, dependencias: WatchSource[] = []) {
  const datos = ref<T | null>(null) as Ref<T | null>
  const cargando = ref(false)
  const error = ref<string | null>(null)

  async function recargar(): Promise<void> {
    cargando.value = true
    error.value = null
    try {
      datos.value = await cargar()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      cargando.value = false
    }
  }

  watch(dependencias, recargar, { immediate: true })
  return { datos, cargando, error, recargar }
}
