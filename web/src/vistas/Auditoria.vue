<script setup lang="ts">
import { Ban, EyeOff, KeyRound, Lock, LogIn, Pencil, Play, Plus, PowerOff, RefreshCw, ShieldAlert, Timer } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora } from '@/formato'
import { api } from '@/servicios/api'

type Evento = { fecha: string; accion: string; email: string | null; recurso: string; detalle: string }

const ACCIONES: Record<string, { texto: string; tono: string; icono: unknown }> = {
  ACCESO_DENEGADO: { texto: 'Acceso denegado', tono: 'critico', icono: Ban },
  ACCESO_RESTRINGIDO: { texto: 'Campos ocultos', tono: 'sello', icono: EyeOff },
  RENDIMIENTO_LENTO: { texto: 'Respuesta lenta (más de 8 s)', tono: 'aviso', icono: Timer },
  DESACTIVAR: { texto: 'Desactivación', tono: 'aviso', icono: PowerOff },
  CREAR: { texto: 'Alta', tono: 'bien', icono: Plus },
  ACTUALIZAR: { texto: 'Cambio', tono: 'marca', icono: Pencil },
  EJECUTAR: { texto: 'Ejecución', tono: 'marca', icono: Play },
  INICIO_SESION: { texto: 'Inicio de sesión', tono: 'bien', icono: LogIn },
  INICIO_FALLIDO: { texto: 'Intento fallido', tono: 'aviso', icono: ShieldAlert },
  CUENTA_BLOQUEADA: { texto: 'Cuenta bloqueada', tono: 'critico', icono: Lock },
  CAMBIO_CLAVE: { texto: 'Cambio de contraseña', tono: 'marca', icono: KeyRound },
  RESTABLECER_CLAVE: { texto: 'Contraseña restablecida', tono: 'aviso', icono: KeyRound },
}
const { datos, cargando, error, recargar } = usarCarga(() => api<Evento[]>('/api/v1/admin/auditoria', { params: { limite: 500 } }))
const accion = ref('')
const acciones = computed(() => [...new Set((datos.value ?? []).map((e) => e.accion))].sort())
const cuenta = (a: string) => (datos.value ?? []).filter((e) => e.accion === a).length
const eventos = computed(() => (datos.value ?? []).filter((e) => !accion.value || e.accion === accion.value))
const info = (a: string) => ACCIONES[a] ?? { texto: a, tono: '', icono: Pencil }
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Auditoría</h1>
        <p>Quién cambió qué y cuándo, accesos denegados, campos sensibles ocultos y solicitudes de más de 8 segundos (HU-13, HU-15).</p>
      </div>
      <button type="button" @click="recargar"><RefreshCw :size="15" /> Actualizar</button>
    </div>

    <div class="segmentos" role="group" aria-label="Acción">
      <button type="button" :class="{ activo: !accion }" :aria-pressed="!accion" @click="accion = ''">Todo <span class="cuenta">{{ datos?.length ?? 0 }}</span></button>
      <button v-for="a in acciones" :key="a" type="button" :class="{ activo: accion === a }" :aria-pressed="accion === a" @click="accion = a">
        {{ info(a).texto }} <span class="cuenta">{{ cuenta(a) }}</span>
      </button>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="panel">
        <p v-if="!eventos.length" class="tenue">Sin eventos todavía. Aparecerán al cambiar reglas o usuarios, o cuando alguien intente entrar sin permiso.</p>
        <ol v-else class="linea-tiempo">
          <li v-for="(e, i) in eventos" :key="i" :class="info(e.accion).tono">
            <span class="marca-evento"><component :is="info(e.accion).icono" :size="15" /></span>
            <div class="evento">
              <div class="fila entre">
                <strong>{{ info(e.accion).texto }} · <span class="secundario">{{ e.recurso }}</span></strong>
                <span class="tenue fecha">{{ hora(e.fecha) }}</span>
              </div>
              <span class="secundario">{{ e.detalle }}</span>
              <span class="tenue pequeno">{{ e.email ?? 'sistema' }}</span>
            </div>
          </li>
        </ol>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.linea-tiempo { list-style: none; margin: 0; padding: 0; display: grid; }
.linea-tiempo li { display: grid; grid-template-columns: 34px 1fr; gap: 12px; position: relative; padding-bottom: 16px; }
.linea-tiempo li:not(:last-child)::before { content: ''; position: absolute; left: 16px; top: 32px; bottom: 0; width: 2px; background: var(--linea); }
.marca-evento { display: grid; place-items: center; width: 34px; height: 34px; border-radius: 50%; background: var(--superficie-2); color: var(--tinta-2); }
li.critico .marca-evento { background: var(--critico-suave); color: var(--critico); }
li.sello .marca-evento { background: var(--sello-suave); color: var(--sello); }
li.aviso .marca-evento { background: var(--aviso-suave); color: var(--aviso-texto); }
li.bien .marca-evento { background: var(--bien-suave); color: var(--bien); }
li.marca .marca-evento { background: var(--marca-suave); color: var(--marca); }
.evento { display: grid; gap: 2px; padding-top: 5px; }
.fecha { white-space: nowrap; font-size: 12.5px; }
.pequeno { font-size: 12px; }
</style>
