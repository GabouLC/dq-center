/** Formatos del portal: números y fechas en es-PE, horas en Lima. */

const pct1 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const entero = new Intl.NumberFormat('es-PE')
const horaLima = new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
})
const mes = new Intl.DateTimeFormat('es-PE', { month: 'short', year: 'numeric', timeZone: 'UTC' })

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${pct1.format(v)} %`)
/** Variación con signo: +2.2 % / −1.3 pts. */
export const signo = (v: number | null | undefined, sufijo = ' %') =>
  v === null || v === undefined ? '—' : `${v >= 0 ? '+' : '−'}${pct1.format(Math.abs(v))}${sufijo}`
export const num = (v: number | null | undefined) => (v === null || v === undefined ? '—' : entero.format(v))
export const hora = (iso: string | null | undefined) => (iso ? horaLima.format(new Date(iso)) : '—')
/** "2026-07-31" -> "jul. 2026" */
export const corte = (iso: string) => mes.format(new Date(`${iso}T00:00:00Z`))

export const NOMBRE_TABLA: Record<string, string> = {
  persona: 'Persona',
  poliza: 'Póliza',
  vehiculo: 'Vehículo',
  siniestro: 'Siniestro',
  pago: 'Pago',
}
export const TABLAS = Object.keys(NOMBRE_TABLA)

export const NOMBRE_DIMENSION: Record<string, string> = {
  completitud: 'Completitud',
  unicidad: 'Unicidad',
  validez: 'Validez',
  consistencia: 'Consistencia',
  integridad: 'Integridad',
  oportunidad: 'Oportunidad',
  volumetria: 'Volumetría',
}

export const NOMBRE_CERTIFICACION: Record<string, string> = {
  CERTIFICADO: 'Certificada',
  CERTIFICADO_CON_OBSERVACIONES: 'Con observaciones',
  NO_CERTIFICADO: 'No certificada',
}
