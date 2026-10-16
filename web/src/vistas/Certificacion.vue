<script setup lang="ts">
import { Fingerprint, Lock, ShieldAlert, ShieldCheck, Stamp, TriangleAlert, Workflow } from 'lucide-vue-next'
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import MapaDias from '@/componentes/MapaDias.vue'
import Sello from '@/componentes/Sello.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora, NOMBRE_TABLA, num, pct, TABLAS } from '@/formato'
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
const filasHistoria = computed(() =>
  TABLAS.map((tabla) => ({
    clave: tabla,
    nombre: NOMBRE_TABLA[tabla],
    estados: Object.fromEntries(Object.entries(datos.value?.historia ?? {}).map(([dia, estados]) => [dia, estados[tabla]])),
  })),
)
const niveles = (t: Tabla, n: string) => t.calidad.por_nivel[n] ?? {}
const total = (t: Tabla, n: string) => Object.values(niveles(t, n)).reduce((a, b) => a + b, 0) || 1
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Certificación</h1>
        <p>
          El Quality &amp; Privacy Gate sella cada tabla: calidad en tres niveles, privacidad y trazabilidad (HU-04, HU-07,
          HU-12). Una regla CRÍTICA o ALTA en FAIL, o PII en texto claro, impide certificar y publicar.
        </p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <template v-if="datos">
        <section class="panel pila">
          <div class="fila entre">
            <h2>Historia de los sellos</h2>
            <span class="tenue pequeno">Días certificados · con observaciones · sin certificar</span>
          </div>
          <MapaDias
            :dias="Object.keys(datos.historia)"
            :filas="filasHistoria"
            :elegido="datos.fecha_corte"
            @elegir="(d) => (cortes.elegido = d)"
          />
        </section>

        <article v-for="t in datos.tablas" :key="t.tabla" class="panel ficha" :class="t.estado">
          <Sello :estado="t.estado" :tabla="NOMBRE_TABLA[t.tabla]" :detalle="`Dominio ${t.dominio}`" :tamano="150" />

          <section class="bloque">
            <h3 class="fila"><component :is="t.calidad.ok ? ShieldCheck : ShieldAlert" :size="18" :class="t.calidad.ok ? 'bien' : 'critico'" /> Calidad</h3>
            <p class="secundario"><strong class="num">{{ pct(t.calidad.pct_pass) }}</strong> de las reglas en PASS</p>
            <div v-for="n in ['N1', 'N2', 'N3']" :key="n" class="nivel" :title="`${n}: ${niveles(t, n).OK ?? 0} PASS, ${niveles(t, n).ALERTA ?? 0} alerta, ${niveles(t, n).FALLA ?? 0} FAIL`">
              <strong>{{ n }}</strong>
              <div class="pila-barra">
                <span class="seg bien" :style="{ flex: niveles(t, n).OK ?? 0 }" />
                <span class="seg aviso" :style="{ flex: niveles(t, n).ALERTA ?? 0 }" />
                <span class="seg critico" :style="{ flex: niveles(t, n).FALLA ?? 0 }" />
                <span class="seg neutro" :style="{ flex: niveles(t, n).SIN_DATOS ?? 0 }" />
              </div>
              <span class="tenue num">{{ niveles(t, n).OK ?? 0 }}/{{ total(t, n) }}</span>
            </div>
            <p v-if="t.calidad.reglas_bloqueantes.length" class="aviso-caja error">
              <ShieldAlert :size="17" /><span>Bloquean: <strong>{{ t.calidad.reglas_bloqueantes.join(', ') }}</strong></span>
            </p>
            <p v-if="t.calidad.reglas_con_observacion.length" class="tenue pequeno">
              Con observación: {{ t.calidad.reglas_con_observacion.join(', ') }}
            </p>
          </section>

          <section class="bloque">
            <h3 class="fila"><component :is="t.privacidad.ok ? Lock : ShieldAlert" :size="18" :class="t.privacidad.ok ? 'sello-c' : 'critico'" /> Privacidad</h3>
            <div v-if="t.privacidad.campos_cifrados.length" class="fila chips">
              <span v-for="c in t.privacidad.campos_cifrados" :key="c.campo" class="chip" :class="c.protegido ? 'sello' : 'critico'">
                <Lock :size="12" /> {{ c.campo }}
              </span>
            </div>
            <p v-else class="tenue pequeno">Sin campos de PII que cifrar.</p>
            <p v-for="h in t.privacidad.hallazgos" :key="h.tipo + h.columna" class="aviso-caja" :class="{ error: h.bloqueante }">
              <component :is="h.bloqueante ? ShieldAlert : TriangleAlert" :size="17" />
              <span>
                {{ HALLAZGO[h.tipo] ?? h.tipo }} en <strong>{{ h.columna }}</strong>
                <template v-if="h.tipo === 'PII_EN_CLARO'"> · {{ num(h.registros) }} registros</template>
                <template v-if="!h.bloqueante"> (observación)</template>
              </span>
            </p>
          </section>

          <section class="bloque">
            <h3 class="fila"><Fingerprint :size="18" class="marca-c" /> Trazabilidad</h3>
            <dl class="sello-datos">
              <dt>Corrida</dt><dd class="mono">{{ t.trazabilidad.id_ejecucion.slice(0, 12) }}</dd>
              <dt>Motor · reglas</dt><dd class="mono">v{{ t.trazabilidad.version_motor }} · {{ t.trazabilidad.version_reglas }}</dd>
              <dt>Cobertura</dt><dd>{{ pct(t.trazabilidad.cobertura) }} de reglas con datos</dd>
              <dt>Sellado</dt><dd>{{ hora(t.trazabilidad.certificado_en) }}</dd>
              <dt>BUSINESS</dt>
              <dd>
                <span v-if="t.trazabilidad.publicado" class="chip bien"><Stamp :size="12" /> {{ t.trazabilidad.objeto_business }}</span>
                <span v-else class="chip critico">Retenido por el Gate</span>
              </dd>
            </dl>
            <RouterLink :to="`/linaje/${t.tabla}`" class="fila enlace"><Workflow :size="16" /> Ver su linaje</RouterLink>
          </section>
        </article>
      </template>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.pequeno { font-size: 12.5px; }
.ficha { display: grid; grid-template-columns: 180px repeat(3, minmax(0, 1fr)); gap: 24px; align-items: start; border-left: 5px solid var(--aviso); }
.ficha.CERTIFICADO { border-left-color: var(--bien); }
.ficha.NO_CERTIFICADO { border-left-color: var(--critico); }
.bloque { display: grid; gap: 9px; align-content: start; }
.bloque h3 { gap: 7px; }
.bien { color: var(--bien); }
.critico { color: var(--critico); }
.sello-c { color: var(--sello); }
.marca-c { color: var(--marca); }
.nivel { display: grid; grid-template-columns: 28px 1fr 42px; gap: 8px; align-items: center; font-size: 13px; }
.pila-barra { display: flex; gap: 2px; height: 10px; border-radius: 999px; overflow: hidden; background: var(--superficie-3); }
.seg.bien { background: var(--bien); }
.seg.aviso { background: var(--aviso); }
.seg.critico { background: var(--critico); }
.seg.neutro { background: var(--linea-fuerte); }
.chips { gap: 5px; }
.pequeno { font-size: 12.5px; }
.sello-datos { display: grid; grid-template-columns: max-content 1fr; gap: 5px 12px; margin: 0; font-size: 13px; }
.sello-datos dt { color: var(--tenue); font-weight: 600; }
.sello-datos dd { margin: 0; min-width: 0; overflow-wrap: anywhere; }
.enlace { gap: 6px; font-weight: 700; font-size: 13.5px; }
@media (max-width: 1100px) {
  .ficha { grid-template-columns: 1fr 1fr; }
  .ficha :deep(.sello) { grid-row: span 2; }
}
@media (max-width: 680px) {
  .ficha { grid-template-columns: 1fr; justify-items: stretch; }
  .ficha :deep(.sello) { justify-self: center; }
}
</style>
