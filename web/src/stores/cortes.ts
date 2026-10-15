import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/servicios/api'

export type Corte = {
  fecha_corte: string
  id_ejecucion: string
  terminada_en: string
  global: number | null
  no_certificadas: number
}

/** Cortes con evaluación y el corte elegido, compartido por todos los módulos. */
export const useCortes = defineStore('cortes', () => {
  const lista = ref<Corte[]>([])
  const elegido = ref<string | null>(null)

  async function cargar(forzar = false): Promise<void> {
    if (lista.value.length && !forzar) return
    lista.value = await api<Corte[]>('/api/v1/cortes')
    if (!elegido.value || !lista.value.some((c) => c.fecha_corte === elegido.value)) {
      elegido.value = lista.value.at(-1)?.fecha_corte ?? null
    }
  }

  return { lista, elegido, cargar }
})
