import { defineStore } from 'pinia'
import { ref } from 'vue'
import { guardarPreferencia, leerPreferencia } from '@/composables/usarPreferencia'

/**
 * Recorrido guiado de la primera visita. Se muestra una vez por usuario (se recuerda en este
 * navegador) y se puede volver a abrir con el botón de ayuda de la barra superior.
 */
export const useRecorrido = defineStore('recorrido', () => {
  const abierto = ref(false)

  const visto = () => leerPreferencia('recorrido-visto', false)
  function abrir(): void {
    abierto.value = true
  }
  function cerrar(): void {
    abierto.value = false
    guardarPreferencia('recorrido-visto', true)
  }
  /**
   * Primera visita: se abre solo. No en navegadores automatizados (capturas y pruebas con
   * Playwright), para que el recorrido no tape la página que se está fotografiando.
   */
  function abrirSiEsPrimeraVez(): void {
    if (!abierto.value && !visto() && !navigator.webdriver) abrir()
  }

  return { abierto, abrir, cerrar, abrirSiEsPrimeraVez }
})
