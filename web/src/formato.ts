/** Formatos del portal: números y fechas en es-PE, horas en Lima. */

const pct1 = new Intl.NumberFormat('es-PE', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const entero = new Intl.NumberFormat('es-PE')
const horaLima = new Intl.DateTimeFormat('es-PE', {
  timeZone: 'America/Lima', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
})
const diaLargo = new Intl.DateTimeFormat('es-PE', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' })
const diaCorto = new Intl.DateTimeFormat('es-PE', { day: 'numeric', month: 'short', timeZone: 'UTC' })
const diaMedio = new Intl.DateTimeFormat('es-PE', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
const relativoFmt = new Intl.RelativeTimeFormat('es-PE', { numeric: 'auto', style: 'short' })

export const pct = (v: number | null | undefined) => (v === null || v === undefined ? '—' : `${pct1.format(v)} %`)
/** Variación con signo: +2.2 % / −1.3 pts; lo que redondea a cero se muestra sin signo. */
export const signo = (v: number | null | undefined, sufijo = ' %') => {
  if (v === null || v === undefined) return '—'
  const texto = pct1.format(Math.abs(v))
  return Number(texto.replace(',', '.')) === 0 ? `${texto}${sufijo}` : `${v > 0 ? '+' : '−'}${texto}${sufijo}`
}
export const num = (v: number | null | undefined) => (v === null || v === undefined ? '—' : entero.format(v))
export const hora = (iso: string | null | undefined) => (iso ? horaLima.format(new Date(iso)) : '—')
/** "2026-07-14" -> "mar., 14 jul. 2026" */
export const corte = (iso: string) => diaLargo.format(new Date(`${iso}T00:00:00Z`))
/** "2026-07-14" -> "14 jul." */
export const corteCorto = (iso: string) => diaCorto.format(new Date(`${iso}T00:00:00Z`))
/** "2026-07-14" -> "mar., 14 jul." */
export const corteMedio = (iso: string) => diaMedio.format(new Date(`${iso}T00:00:00Z`))
const partesDia = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' })
function partes(iso: string): Record<string, string> {
  return Object.fromEntries(partesDia.formatToParts(new Date(`${iso}T00:00:00Z`)).map((p) => [p.type, p.value]))
}
/** "2026-07-14" -> "Martes 14 de julio" (para frases) */
export function diaEnFrase(iso: string): string {
  const p = partes(iso)
  const texto = `${p.weekday} ${p.day} de ${p.month}`
  return texto.charAt(0).toUpperCase() + texto.slice(1)
}
/** "2026-07-13" -> "lunes 13" */
export function diaDeSemana(iso: string): string {
  const p = partes(iso)
  return `${p.weekday} ${p.day}`
}
/** Fin de semana: los sistemas de origen casi no generan movimiento. */
export const esFinDeSemana = (iso: string) => [0, 6].includes(new Date(`${iso}T00:00:00Z`).getUTCDay())
/** "hace 3 min", "hace 20 s" */
export function relativo(iso: string, ahora = Date.now()): string {
  const segundos = Math.round((new Date(iso).getTime() - ahora) / 1000)
  if (Math.abs(segundos) < 45) return relativoFmt.format(segundos, 'second')
  if (Math.abs(segundos) < 2700) return relativoFmt.format(Math.round(segundos / 60), 'minute')
  return relativoFmt.format(Math.round(segundos / 3600), 'hour')
}

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

/** Severidad para mostrar; la API sigue usando CRITICA, ALTA, MEDIA y BAJA. */
export const NOMBRE_SEVERIDAD: Record<string, string> = {
  CRITICA: 'Crítica',
  ALTA: 'Alta',
  MEDIA: 'Media',
  BAJA: 'Baja',
}
