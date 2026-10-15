<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import DacChip from '@/componentes/DacChip.vue'
import { usarCarga } from '@/composables/usarCarga'
import { NOMBRE_TABLA, pct } from '@/formato'
import { api } from '@/servicios/api'

type Campo = {
  nombre: string
  tipo: string
  obligatorio: boolean
  dac: string
  cifrado?: string
  descripcion: string
  reglas: string[]
  en_esquema: boolean
  tipo_real: string | null
  protegido: boolean
}
type Contrato = {
  tabla: string
  dominio: string
  dueno: string
  descripcion: string
  consumidores: string[]
  campos: Campo[]
  cobertura: number
  fuera_de_contrato: string[]
  reglas_en_falla: string[]
  reglas_en_alerta: string[]
  consumidores_afectados: string[]
  consumidores_en_riesgo: string[]
}

const { datos, cargando, error, recargar } = usarCarga(() => api<Contrato[]>('/api/v1/contratos'))
const abierto = ref<string | null>('persona')
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Contrato de datos</h1>
        <p class="muted">
          Lo pactado con el dueño de cada tabla: campos, tipos, obligatoriedad y clasificación DAC (HU-05). La cobertura
          es el porcentaje de campos vigilados por al menos una regla activa; el impacto, qué consumidores sufren si falla
          una regla (último corte).
        </p>
      </div>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <article v-for="c in datos ?? []" :key="c.tabla" class="tarjeta pila">
        <button type="button" class="cabecera" :aria-expanded="abierto === c.tabla" @click="abierto = abierto === c.tabla ? null : c.tabla">
          <div>
            <h2>{{ NOMBRE_TABLA[c.tabla] }} <span class="muted">· {{ c.dominio }}</span></h2>
            <span class="muted">{{ c.descripcion }} Dueño: {{ c.dueno }}</span>
          </div>
          <div class="fila">
            <span class="cobertura">
              <span class="muted">Cobertura</span>
              <span class="barra"><span :style="{ width: `${c.cobertura}%`, background: 'var(--accent)' }" /></span>
              <strong class="num">{{ pct(c.cobertura) }}</strong>
            </span>
            <span class="chip falla" v-if="c.consumidores_afectados.length">Impacto</span>
            <span class="chip alerta" v-else-if="c.consumidores_en_riesgo.length">En riesgo</span>
            <span class="chip ok" v-else>Sin impacto</span>
          </div>
        </button>

        <template v-if="abierto === c.tabla">
          <p v-if="c.fuera_de_contrato.length" class="aviso">
            Columnas que llegaron sin estar en el contrato: <span class="mono">{{ c.fuera_de_contrato.join(', ') }}</span>.
            Hay que acordarlas con el dueño y clasificarlas.
          </p>
          <p v-if="c.consumidores_afectados.length" class="aviso error">
            {{ c.reglas_en_falla.join(', ') }} en FAIL afecta a: {{ c.consumidores_afectados.join(', ') }}.
          </p>
          <p v-else-if="c.consumidores_en_riesgo.length" class="aviso">
            {{ c.reglas_en_alerta.length }} reglas en alerta ponen en riesgo a: {{ c.consumidores_en_riesgo.join(', ') }}.
          </p>
          <p v-else class="muted">Consumidores: {{ c.consumidores.join(', ') }}.</p>

          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr><th>Campo</th><th>Tipo</th><th>Obligatorio</th><th>DAC</th><th>Reglas que lo vigilan</th><th>En MASTER</th></tr>
              </thead>
              <tbody>
                <tr v-for="f in c.campos" :key="f.nombre">
                  <td>
                    <RouterLink :to="`/linaje/${c.tabla}`" class="mono">{{ f.nombre }}</RouterLink>
                    <p class="muted pequeno">{{ f.descripcion }}</p>
                  </td>
                  <td class="mono">{{ f.tipo }}</td>
                  <td>{{ f.obligatorio ? 'Sí' : 'No' }}</td>
                  <td><DacChip :dac="f.dac" /></td>
                  <td class="mono pequeno">{{ f.reglas.join(', ') || '—' }}</td>
                  <td>
                    <span v-if="!f.en_esquema" class="chip falla">Falta</span>
                    <span v-else-if="f.dac === 'SENSIBLE_CIFRADO'" class="chip" :class="f.protegido ? 'cifrado' : 'falla'">
                      {{ f.protegido ? '🔒 cifrado' : '⚠ en claro' }}
                    </span>
                    <span v-else class="mono muted">{{ f.tipo_real }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </article>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.cabecera {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  width: 100%;
}
.cobertura { display: inline-flex; align-items: center; gap: 8px; }
.cobertura .barra { width: 110px; }
.pequeno { font-size: 12.5px; }
</style>
