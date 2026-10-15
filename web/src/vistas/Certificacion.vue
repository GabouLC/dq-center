<script setup lang="ts">
import { RouterLink } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EstadoChip from '@/componentes/EstadoChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { corte as nombreCorte, hora, NOMBRE_TABLA, num, pct, TABLAS } from '@/formato'
import { api } from '@/servicios/api'
import { useCortes } from '@/stores/cortes'

type Tabla = {
  tabla: string
  dominio: string
  estado: string
  calidad: {
    ok: boolean
    pct_pass: number | null
    reglas_bloqueantes: string[]
    reglas_con_observacion: string[]
    por_nivel: Record<string, Record<string, number>>
  }
  privacidad: {
    ok: boolean
    campos_cifrados: { campo: string; protegido: boolean }[]
    hallazgos: { tipo: string; columna: string; bloqueante: boolean; registros: number }[]
  }
  trazabilidad: {
    id_ejecucion: string
    version_motor: string
    version_reglas: string
    cobertura: number
    certificado_en: string
    publicado: boolean
    objeto_business: string | null
  }
}
type Respuesta = { fecha_corte: string; tablas: Tabla[]; historia: Record<string, Record<string, string>> }

const cortes = useCortes()
const { datos, cargando, error, recargar } = usarCarga(
  () => api<Respuesta>('/api/v1/certificacion', { params: { corte: cortes.elegido } }),
  [() => cortes.elegido],
)
const HALLAZGO: Record<string, string> = {
  PII_EN_CLARO: 'PII en texto claro',
  CAMPO_SIN_CIFRAR: 'Campo sensible sin cifrar',
  COLUMNA_SIN_CLASIFICAR: 'Columna sin clasificación DAC',
}
const niveles = (t: Tabla, n: string) => t.calidad.por_nivel[n] ?? {}
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Certificación</h1>
        <p class="muted">
          Veredicto del Quality &amp; Privacy Gate por tabla: calidad en tres niveles, privacidad y trazabilidad
          (HU-04, HU-07, HU-12). Una regla CRÍTICA o ALTA en FAIL, o PII en claro, impide certificar.
        </p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="datos">
        <section class="tarjeta pila">
          <h2>Historia de certificación</h2>
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr><th>Tabla</th><th v-for="c in Object.keys(datos.historia)" :key="c">{{ nombreCorte(c) }}</th></tr>
              </thead>
              <tbody>
                <tr v-for="t in TABLAS" :key="t">
                  <td><strong>{{ NOMBRE_TABLA[t] }}</strong></td>
                  <td v-for="(estados, c) in datos.historia" :key="c" :class="{ actual: c === datos.fecha_corte }">
                    <EstadoChip :estado="estados[t] ?? 'SIN_DATOS'" />
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <div class="grilla-tarjetas">
          <article v-for="t in datos.tablas" :key="t.tabla" class="tarjeta pila tarjeta-tabla" :class="t.estado">
            <div class="fila entre">
              <div>
                <h2>{{ NOMBRE_TABLA[t.tabla] }}</h2>
                <span class="muted">Dominio {{ t.dominio }} · {{ nombreCorte(datos.fecha_corte) }}</span>
              </div>
              <EstadoChip :estado="t.estado" />
            </div>

            <section class="bloque">
              <h3>Calidad <span :class="t.calidad.ok ? 'ok' : 'falla'">{{ t.calidad.ok ? '✓' : '✕' }}</span></h3>
              <p class="muted">{{ pct(t.calidad.pct_pass) }} de las reglas en PASS</p>
              <div class="niveles">
                <div v-for="n in ['N1', 'N2', 'N3']" :key="n" class="nivel">
                  <strong>{{ n }}</strong>
                  <span class="chip ok">{{ niveles(t, n).OK ?? 0 }}</span>
                  <span v-if="niveles(t, n).ALERTA" class="chip alerta">{{ niveles(t, n).ALERTA }}</span>
                  <span v-if="niveles(t, n).FALLA" class="chip falla">{{ niveles(t, n).FALLA }}</span>
                </div>
              </div>
              <p v-if="t.calidad.reglas_bloqueantes.length" class="aviso error">
                Bloquean: <span class="mono">{{ t.calidad.reglas_bloqueantes.join(', ') }}</span>
              </p>
              <p v-if="t.calidad.reglas_con_observacion.length" class="muted pequeno">
                Observaciones: <span class="mono">{{ t.calidad.reglas_con_observacion.join(', ') }}</span>
              </p>
            </section>

            <section class="bloque">
              <h3>Privacidad <span :class="t.privacidad.ok ? 'ok' : 'falla'">{{ t.privacidad.ok ? '✓' : '✕' }}</span></h3>
              <p v-if="t.privacidad.campos_cifrados.length" class="pequeno">
                <span v-for="c in t.privacidad.campos_cifrados" :key="c.campo" class="chip" :class="c.protegido ? 'cifrado' : 'falla'">
                  {{ c.protegido ? '🔒' : '⚠' }} {{ c.campo }}
                </span>
              </p>
              <p v-else class="muted pequeno">Sin campos que cifrar.</p>
              <ul v-if="t.privacidad.hallazgos.length" class="hallazgos">
                <li v-for="h in t.privacidad.hallazgos" :key="h.tipo + h.columna" :class="h.bloqueante ? 'falla' : 'alerta'">
                  {{ HALLAZGO[h.tipo] ?? h.tipo }} en <span class="mono">{{ h.columna }}</span>
                  <template v-if="h.tipo === 'PII_EN_CLARO'"> · {{ num(h.registros) }} registros</template>
                  <template v-if="!h.bloqueante"> (observación)</template>
                </li>
              </ul>
            </section>

            <section class="bloque">
              <h3>Trazabilidad</h3>
              <dl class="sello">
                <dt>Corrida</dt><dd class="mono">{{ t.trazabilidad.id_ejecucion.slice(0, 12) }}</dd>
                <dt>Motor · reglas</dt><dd class="mono">v{{ t.trazabilidad.version_motor }} · {{ t.trazabilidad.version_reglas }}</dd>
                <dt>Cobertura</dt><dd class="num">{{ pct(t.trazabilidad.cobertura) }} de reglas con datos</dd>
                <dt>Certificado</dt><dd>{{ hora(t.trazabilidad.certificado_en) }}</dd>
                <dt>BUSINESS</dt>
                <dd>
                  <span v-if="t.trazabilidad.publicado" class="mono">{{ t.trazabilidad.objeto_business }}</span>
                  <span v-else class="falla">No publicado</span>
                </dd>
              </dl>
              <RouterLink :to="`/linaje/${t.tabla}`">Ver linaje →</RouterLink>
            </section>
          </article>
        </div>
      </template>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.actual { background: var(--accent-soft); }
.tarjeta-tabla { border-top: 4px solid var(--alerta); }
.tarjeta-tabla.CERTIFICADO { border-top-color: var(--ok); }
.tarjeta-tabla.NO_CERTIFICADO { border-top-color: var(--falla); }
.bloque { display: grid; gap: 6px; padding-top: 12px; border-top: 1px solid var(--line); }
.niveles { display: flex; gap: 14px; flex-wrap: wrap; }
.nivel { display: flex; gap: 4px; align-items: center; }
.ok { color: var(--ok); }
.falla { color: var(--falla); }
.alerta { color: var(--alerta); }
.pequeno { font-size: 12.5px; display: flex; gap: 4px; flex-wrap: wrap; }
.hallazgos { margin: 0; padding-left: 18px; font-size: 13px; }
.sello { display: grid; grid-template-columns: max-content 1fr; gap: 4px 12px; margin: 0; font-size: 13px; }
.sello dt { color: var(--muted); }
.sello dd { margin: 0; }
</style>
