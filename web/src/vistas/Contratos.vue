<script setup lang="ts">
import { ChevronDown, CircleAlert, FileText, ShieldCheck, TriangleAlert, Users } from 'lucide-vue-next'
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import Anillo from '@/componentes/Anillo.vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import DacChip from '@/componentes/DacChip.vue'
import EncabezadoSeccion from '@/componentes/EncabezadoSeccion.vue'
import EstadoVacio from '@/componentes/EstadoVacio.vue'
import { usarCarga } from '@/composables/usarCarga'
import { NOMBRE_TABLA } from '@/formato'
import type { Clave } from '@/navegacion'
import { api } from '@/servicios/api'

type Campo = {
  nombre: string
  tipo: string
  obligatorio: boolean
  dac: string
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
const cuenta = (c: Contrato, dac: string) => c.campos.filter((f) => f.dac === dac).length
const DAC = [['PUBLICO', 'Público', 'var(--linea-fuerte)'], ['SENSIBLE', 'Sensible', 'var(--aviso)'], ['SENSIBLE_CIFRADO', 'Sensible cifrado', 'var(--sello)']]
const plural = (n: number, uno: string, varios: string) => (n === 1 ? uno : varios)

const LECTURA: Clave[] = [
  { texto: 'El anillo dice cuántos campos del contrato vigila al menos una regla de calidad (cobertura).' },
  { muestras: ['publico', 'sensible', 'cifrado'], texto: 'La barra reparte los campos por sensibilidad (DAC): Público, Sensible y Sensible cifrado, que nunca se muestra en claro.' },
  { muestras: ['critico', 'aviso', 'bien'], texto: 'Afecta a consumidores: alguna regla del contrato falla en el último día de datos. En riesgo: alguna está en alerta. Sin impacto: todas cumplen.' },
  { texto: 'Abre una tabla para ver cada campo, su tipo, qué reglas lo vigilan y cómo llegó a MASTER.' },
]
</script>

<template>
  <div class="pila">
    <EncabezadoSeccion
      modulo="contratos"
      titulo="Contrato de datos"
      subtitulo="Lo pactado con el dueño de cada tabla: campos, tipos y clasificación de sensibilidad (DAC), qué reglas los vigilan y qué consumidores sufren si una falla."
      :lectura="LECTURA"
    />

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" forma="tarjetas" @reintentar="recargar">
      <article v-for="c in datos ?? []" :key="c.tabla" class="panel contrato" :class="{ abierto: abierto === c.tabla }">
        <h2 class="titulo-contrato">
          <button type="button" class="cabecera" :aria-expanded="abierto === c.tabla" @click="abierto = abierto === c.tabla ? null : c.tabla">
            <Anillo :parte="c.campos.filter((f) => f.reglas.length).length" :total="c.campos.length" etiqueta="campos vigilados" :tamano="96" />
            <span class="identidad">
              <span class="nombre-tabla">{{ NOMBRE_TABLA[c.tabla] }} <span class="tenue">· {{ c.dominio }}</span></span>
              <span class="secundario">{{ c.descripcion }}</span>
              <span class="tenue pequeno">Dueño: {{ c.dueno }}</span>
            </span>
            <span class="dac">
              <span class="distribucion" :title="DAC.map(([k, n]) => `${n}: ${cuenta(c, k)}`).join(' · ')">
                <span v-for="[k, , color] in DAC" :key="k" :style="{ flex: cuenta(c, k), background: color }" />
              </span>
              <span class="fila leyenda">
                <span v-for="[k, n, color] in DAC" :key="k"><i :style="{ background: color }" />{{ n }} {{ cuenta(c, k) }}</span>
              </span>
            </span>
            <span class="impacto">
              <span v-if="c.consumidores_afectados.length" class="chip critico"><CircleAlert :size="13" /> Afecta a consumidores</span>
              <span v-else-if="c.consumidores_en_riesgo.length" class="chip aviso"><TriangleAlert :size="13" /> En riesgo</span>
              <span v-else class="chip bien"><ShieldCheck :size="13" /> Sin impacto</span>
              <ChevronDown :size="18" class="flecha" />
            </span>
          </button>
        </h2>

        <div v-if="abierto === c.tabla" class="pila cuerpo">
          <p v-if="c.fuera_de_contrato.length" class="aviso-caja">
            <TriangleAlert :size="17" />
            <span>Llegó sin estar en el contrato: <strong>{{ c.fuera_de_contrato.join(', ') }}</strong>. Hay que acordarla con el dueño y clasificarla.</span>
          </p>
          <p v-if="c.consumidores_afectados.length" class="aviso-caja error">
            <CircleAlert :size="17" />
            <span>
              <strong>{{ c.reglas_en_falla.join(', ') }}</strong>
              {{ plural(c.reglas_en_falla.length, 'falla y afecta a', 'fallan y afectan a') }} {{ c.consumidores_afectados.join(', ') }}.
            </span>
          </p>
          <p v-else-if="c.consumidores_en_riesgo.length" class="aviso-caja">
            <Users :size="17" />
            <span>
              {{ c.reglas_en_alerta.length }}
              {{ plural(c.reglas_en_alerta.length, 'regla en alerta pone', 'reglas en alerta ponen') }} en riesgo a
              {{ c.consumidores_en_riesgo.join(', ') }}.
            </span>
          </p>
          <div class="tabla-envoltura">
            <table>
              <thead>
                <tr><th>Campo</th><th>Tipo</th><th>Obligatorio</th><th>Clasificación</th><th>Reglas que lo vigilan</th><th>En MASTER</th></tr>
              </thead>
              <tbody>
                <tr v-for="f in c.campos" :key="f.nombre">
                  <td>
                    <RouterLink :to="`/linaje/${c.tabla}`"><strong>{{ f.nombre }}</strong></RouterLink>
                    <p class="tenue pequeno">{{ f.descripcion }}</p>
                  </td>
                  <td><span class="chip">{{ f.tipo }}</span></td>
                  <td>{{ f.obligatorio ? 'Sí' : 'No' }}</td>
                  <td><DacChip :dac="f.dac" /></td>
                  <td class="pequeno">
                    <span v-if="!f.reglas.length" class="tenue">Ninguna</span>
                    <span v-for="r in f.reglas" :key="r" class="regla">{{ r }}</span>
                  </td>
                  <td>
                    <span v-if="!f.en_esquema" class="chip critico">Falta</span>
                    <span v-else-if="f.dac === 'SENSIBLE_CIFRADO'" class="chip" :class="f.protegido ? 'sello' : 'critico'">{{ f.protegido ? 'Cifrado' : 'Sin cifrar' }}</span>
                    <span v-else class="tenue">{{ f.tipo_real }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>
      <section v-if="datos && !datos.length" class="panel">
        <EstadoVacio
          :icono="FileText"
          titulo="Todavía no hay contratos"
          texto="Cuando se registre el contrato de una tabla con su dueño, aquí verás sus campos, su clasificación y quién depende de ella."
        />
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.contrato { padding: 14px 20px; transition: box-shadow 0.15s ease, border-color 0.15s ease; }
.contrato.abierto { box-shadow: var(--sombra-alta); }
.cabecera {
  display: grid;
  grid-template-columns: 96px minmax(220px, 1.6fr) minmax(180px, 1fr) auto;
  gap: 20px;
  align-items: center;
  width: 100%;
  border: 0;
  border-radius: 12px;
  background: none;
  padding: 0;
  text-align: left;
  font-weight: 400;
}
.cabecera:hover { color: inherit; }
/* Botón ancho: se hunde apenas al presionar. */
.cabecera:active { transform: scale(0.995); }
@media (hover: hover) and (pointer: fine) {
  .contrato:not(.abierto):hover { border-color: var(--linea-fuerte); }
}
/* El h2 solo da la estructura; el aspecto lo pone el botón y sus partes. */
.titulo-contrato { font: inherit; letter-spacing: normal; }
.identidad { display: grid; gap: 3px; }
.nombre-tabla { font-size: 17px; font-weight: 700; letter-spacing: -0.01em; }
.dac { display: grid; gap: 6px; }
.distribucion { display: flex; gap: 2px; height: 12px; border-radius: 999px; overflow: hidden; }
.leyenda { gap: 12px; font-size: 12px; color: var(--tinta-2); font-weight: 600; }
.leyenda i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: -1px; }
.impacto { display: flex; align-items: center; gap: 10px; }
.flecha { color: var(--tenue); transition: transform 0.2s var(--ease-out); }
.contrato.abierto .flecha { transform: rotate(180deg); }
.cuerpo { margin-top: 16px; }
.pequeno { font-size: 12.5px; }
.regla { display: inline-block; margin: 1px 6px 1px 0; font-weight: 700; color: var(--tinta-2); }
@media (max-width: 900px) {
  .cabecera { grid-template-columns: 80px 1fr; }
  .dac, .impacto { grid-column: 1 / -1; }
}
</style>
