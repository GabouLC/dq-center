import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'
import { useSesion } from '@/stores/sesion'

export type Evento = {
  id: number
  cuando: string
  tipo: string
  tono: 'info' | 'bien' | 'aviso' | 'critico'
  titulo: string
  detalle: string | null
  tabla: string | null
  fecha_corte: string | null
}
type Estado = {
  activo: boolean
  pausado?: boolean
  intervalo?: number
  proximo_en?: number | null
  ultimo_corte?: string | null
  corte_en_curso?: string | null
  archivos_recibidos?: number
  archivos_pendientes?: number
  dias_pendientes?: number
  version: number
}

const CADA_MS = 4000

/**
 * Simulación en vivo: consulta la API cada pocos segundos, junta la actividad y,
 * cuando se publica un corte nuevo, sube `version` para que las vistas se recarguen.
 */
export const useVivo = defineStore('vivo', () => {
  const estado = ref<Estado | null>(null)
  const eventos = ref<Evento[]>([]) // del más nuevo al más viejo
  const avisos = ref<Evento[]>([])
  const version = ref(0)
  const proximoEn = ref<number | null>(null)
  const panelAbierto = ref(false)
  let ultimo = 0
  let consulta: ReturnType<typeof setInterval> | null = null
  let reloj: ReturnType<typeof setInterval> | null = null

  async function consultar(): Promise<void> {
    const sesion = useSesion()
    if (!sesion.activa || sesion.debeCambiar) return
    try {
      const { eventos: nuevos, ...resto } = await api<Estado & { eventos: Evento[] }>('/api/v1/vivo', { params: { desde: ultimo } })
      if (estado.value && resto.version !== estado.value.version) await corteNuevo()
      estado.value = resto
      proximoEn.value = resto.proximo_en ?? null
      if (nuevos.length) {
        const primeraVez = ultimo === 0
        ultimo = nuevos[nuevos.length - 1].id
        eventos.value = [...nuevos].reverse().concat(eventos.value).slice(0, 80)
        if (!primeraVez) avisar(nuevos.filter((e) => e.tono === 'critico' || e.tipo === 'certificacion'))
      }
    } catch {
      /* sin conexión: se reintenta en el siguiente ciclo */
    }
  }

  /** Recarga la lista de cortes y, si el usuario miraba el último, lo lleva al nuevo. */
  async function corteNuevo(): Promise<void> {
    const cortes = useCortes()
    const miraElUltimo = !cortes.elegido || cortes.elegido === cortes.lista.at(-1)?.fecha_corte
    await cortes.cargar(true)
    if (miraElUltimo) cortes.elegido = cortes.lista.at(-1)?.fecha_corte ?? null
    version.value++
  }

  function avisar(lista: Evento[]): void {
    for (const e of lista.slice(-3)) {
      avisos.value = [...avisos.value, e].slice(-3)
      setTimeout(() => (avisos.value = avisos.value.filter((a) => a.id !== e.id)), 7000)
    }
  }

  function iniciar(): void {
    if (consulta) return
    void consultar()
    consulta = setInterval(consultar, CADA_MS)
    reloj = setInterval(() => {
      if (proximoEn.value !== null) proximoEn.value = Math.max(0, proximoEn.value - 1)
    }, 1000)
  }

  function detener(): void {
    if (consulta) clearInterval(consulta)
    if (reloj) clearInterval(reloj)
    consulta = reloj = null
    estado.value = null
    eventos.value = []
    ultimo = 0
  }

  async function pausar(pausado: boolean): Promise<void> {
    await api('/api/v1/vivo/pausa', { metodo: 'POST', cuerpo: { pausado } })
    await consultar()
  }

  async function adelantar(): Promise<void> {
    await api('/api/v1/vivo/adelantar', { metodo: 'POST' })
    setTimeout(consultar, 1200)
  }

  const descartar = (id: number) => (avisos.value = avisos.value.filter((a) => a.id !== id))

  return { estado, eventos, avisos, version, proximoEn, panelAbierto, iniciar, detener, pausar, adelantar, descartar }
})
