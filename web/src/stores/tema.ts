import { defineStore } from 'pinia'
import { ref, watchEffect } from 'vue'

type Tema = 'claro' | 'oscuro' | 'sistema'
const CLAVE = 'dqc.tema'

function leer(): Tema {
  try {
    const valor = localStorage.getItem(CLAVE)
    return valor === 'claro' || valor === 'oscuro' ? valor : 'sistema'
  } catch {
    return 'sistema'
  }
}

/** Tema claro/oscuro elegido por el usuario; "sistema" sigue al sistema operativo. */
export const useTema = defineStore('tema', () => {
  const tema = ref<Tema>(leer())
  const oscuroSistema = window.matchMedia('(prefers-color-scheme: dark)')
  const sistemaOscuro = ref(oscuroSistema.matches)
  oscuroSistema.addEventListener('change', (e) => (sistemaOscuro.value = e.matches))

  watchEffect(() => {
    const raiz = document.documentElement
    if (tema.value === 'sistema') raiz.removeAttribute('data-theme')
    else raiz.setAttribute('data-theme', tema.value === 'oscuro' ? 'dark' : 'light')
    try {
      localStorage.setItem(CLAVE, tema.value)
    } catch {
      /* sin almacenamiento: el tema dura la sesión */
    }
  })

  const esOscuro = () => tema.value === 'oscuro' || (tema.value === 'sistema' && sistemaOscuro.value)
  function alternar() {
    tema.value = esOscuro() ? 'claro' : 'oscuro'
  }
  return { tema, esOscuro, alternar }
})
