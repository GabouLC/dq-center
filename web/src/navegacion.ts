import {
  BadgeCheck, BookOpen, Database, FileText, LayoutDashboard, ListChecks, PlayCircle, ScrollText, SlidersHorizontal, Users, Workflow,
} from 'lucide-vue-next'
import type { Component } from 'vue'

/**
 * Cómo se presenta cada módulo: a qué grupo del menú pertenece, su ícono, una
 * descripción corta (menú) y la pregunta que responde (encabezado de la vista).
 * Los módulos visibles y sus nombres vienen de la API (/auth/me); aquí solo se ordenan.
 */
export type InfoModulo = { grupo: string; icono: Component; descripcion: string; pregunta: string }

/** «¿Cómo se lee?»: una marca visual de la página (muestras de color o forma) y qué significa. */
export type Muestra =
  | 'bien' | 'aviso' | 'critico' | 'neutro' | 'umbral' | 'punto' | 'finde' | 'candado' | 'limite'
  | 'publico' | 'sensible' | 'cifrado' | 'marca'
export type Clave = { texto: string; muestras?: Muestra[] }

export const GRUPOS = [
  { clave: 'dia', nombre: 'Calidad del día' },
  { clave: 'origen', nombre: 'Origen y gobierno' },
  { clave: 'admin', nombre: 'Administración' },
] as const

export const MODULOS: Record<string, InfoModulo> = {
  resumen: {
    grupo: 'dia', icono: LayoutDashboard,
    descripcion: 'El estado del día en un vistazo',
    pregunta: '¿Puedo confiar en los datos de este día?',
  },
  validaciones: {
    grupo: 'dia', icono: ListChecks,
    descripcion: 'Qué reglas fallaron y dónde',
    pregunta: '¿Qué reglas fallaron y en qué registros?',
  },
  certificacion: {
    grupo: 'dia', icono: BadgeCheck,
    descripcion: 'Qué tablas pasaron a negocio',
    pregunta: '¿Qué tablas pasaron el control y cuáles se retuvieron?',
  },
  fuentes: {
    grupo: 'origen', icono: Database,
    descripcion: 'Llegada y volumen de los archivos',
    pregunta: '¿Llegaron los archivos completos y a tiempo?',
  },
  contratos: {
    grupo: 'origen', icono: FileText,
    descripcion: 'Lo acordado con cada dueño',
    pregunta: '¿Qué se acordó entregar y a quién afecta una falla?',
  },
  linaje: {
    grupo: 'origen', icono: Workflow,
    descripcion: 'El recorrido de cada campo',
    pregunta: '¿De dónde sale cada dato y qué le pasa en el camino?',
  },
  glosario: {
    grupo: 'origen', icono: BookOpen,
    descripcion: 'Qué significa cada término',
    pregunta: '¿Qué significa cada término?',
  },
  reglas: {
    grupo: 'admin', icono: SlidersHorizontal,
    descripcion: 'Qué se revisa y con qué umbral',
    pregunta: '¿Qué se revisa y con qué umbral?',
  },
  ejecuciones: {
    grupo: 'admin', icono: PlayCircle,
    descripcion: 'Cuándo se evaluó cada día',
    pregunta: '¿Cuándo se evaluó cada día?',
  },
  usuarios: {
    grupo: 'admin', icono: Users,
    descripcion: 'Quién entra y con qué rol',
    pregunta: '¿Quién entra y con qué permisos?',
  },
  auditoria: {
    grupo: 'admin', icono: ScrollText,
    descripcion: 'Quién hizo qué y cuándo',
    pregunta: '¿Quién hizo qué y cuándo?',
  },
}
