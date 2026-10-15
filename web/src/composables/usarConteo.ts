import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

/**
 * Número que sube hasta su valor (el único movimiento automático del portal).
 * Con "reducir movimiento" activado, muestra el valor final de inmediato.
 */
export function usarConteo(objetivo: Ref<number | null | undefined>, duracionMs = 900) {
  const valor = ref<number | null>(null)
  let cuadro = 0
  const reducido = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  watch(
    objetivo,
    (destino) => {
      cancelAnimationFrame(cuadro)
      if (destino === null || destino === undefined) {
        valor.value = null
        return
      }
      const desde = valor.value ?? 0
      if (reducido || desde === destino) {
        valor.value = destino
        return
      }
      const inicio = performance.now()
      const paso = (ahora: number) => {
        const t = Math.min(1, (ahora - inicio) / duracionMs)
        const suave = 1 - Math.pow(1 - t, 3)
        valor.value = desde + (destino - desde) * suave
        if (t < 1) cuadro = requestAnimationFrame(paso)
      }
      cuadro = requestAnimationFrame(paso)
    },
    { immediate: true },
  )
  onBeforeUnmount(() => cancelAnimationFrame(cuadro))
  return valor
}
