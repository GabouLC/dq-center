<script setup lang="ts">
import {
  BookOpen, CircleCheck, CircleX, Copy, KeyRound, ShieldCheck, SlidersHorizontal, UserMinus, UserPlus, X,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import EncabezadoSeccion from '@/componentes/EncabezadoSeccion.vue'
import EstadoVacio from '@/componentes/EstadoVacio.vue'
import { usarCarga } from '@/composables/usarCarga'
import { hora } from '@/formato'
import type { Clave } from '@/navegacion'
import { api } from '@/servicios/api'
import { useSesion } from '@/stores/sesion'

type Usuario = {
  email: string
  rol: string
  ultimo_acceso?: string | null
  bloqueada?: boolean
  clave_temporal?: boolean
  sin_clave?: boolean
}
type Temporal = { email: string; clave: string }

const ROLES: [string, string, string, unknown][] = [
  ['lector', 'Lector', 'Consulta indicadores; los campos sensibles aparecen ocultos.', ShieldCheck],
  ['gobierno', 'Gobierno de datos', 'Ve los campos sensibles y edita el glosario.', BookOpen],
  ['admin', 'Administrador', 'Configura reglas, lanza ejecuciones y gestiona usuarios.', SlidersHorizontal],
]
const nombreRol = (rol: string) => ROLES.find(([r]) => r === rol)?.[1] ?? rol
const sesion = useSesion()
const { datos, cargando, error, recargar } = usarCarga(() => api<Usuario[]>('/api/v1/admin/usuarios'))
const nuevoEmail = ref('')
const nuevoRol = ref('lector')
const mensaje = ref<{ tipo: 'bien' | 'error'; texto: string } | null>(null)
const temporal = ref<Temporal | null>(null)
const copiada = ref(false)
const porRol = computed(() => Object.fromEntries(ROLES.map(([r]) => [r, (datos.value ?? []).filter((u) => u.rol === r).length])))

function estado(u: Usuario): { texto: string; tono: string } {
  if (u.bloqueada) return { texto: 'Bloqueada', tono: 'critico' }
  if (u.sin_clave) return { texto: 'Sin contraseña', tono: '' }
  if (u.clave_temporal) return { texto: 'Contraseña temporal', tono: 'aviso' }
  return { texto: 'Activa', tono: 'bien' }
}

function fallo(e: unknown) {
  mensaje.value = { tipo: 'error', texto: e instanceof Error ? e.message : String(e) }
}

function mostrarTemporal(email: string, clave: string) {
  temporal.value = { email, clave }
  copiada.value = false
}

async function guardar(email: string, rol: string) {
  mensaje.value = null
  try {
    const r = await api<{ clave_temporal?: string }>(`/api/v1/admin/usuarios/${encodeURIComponent(email)}`, { metodo: 'PUT', cuerpo: { rol } })
    if (r.clave_temporal) mostrarTemporal(email, r.clave_temporal)
    else mensaje.value = { tipo: 'bien', texto: `${email} ahora tiene el rol ${nombreRol(rol)}.` }
    nuevoEmail.value = ''
  } catch (e) {
    fallo(e)
  }
  await recargar()
}

/**
 * Cambio de rol desde la tabla. En Windows, las flechas sobre un select cerrado disparan
 * "change": se pide confirmación y, si se cancela, el select vuelve al rol actual.
 */
async function cambiarRol(u: Usuario, evento: Event) {
  const select = evento.target as HTMLSelectElement
  const rol = select.value
  if (rol === u.rol) return
  if (!window.confirm(`¿Cambiar el rol de ${u.email} de ${nombreRol(u.rol)} a ${nombreRol(rol)}?`)) {
    select.value = u.rol
    return
  }
  await guardar(u.email, rol)
}

async function restablecer(email: string) {
  if (!window.confirm(`¿Dar a ${email} una contraseña temporal nueva? Se cerrarán sus sesiones abiertas.`)) return
  mensaje.value = null
  try {
    const r = await api<{ clave_temporal: string }>(`/api/v1/admin/usuarios/${encodeURIComponent(email)}/clave`, { metodo: 'POST' })
    mostrarTemporal(email, r.clave_temporal)
  } catch (e) {
    fallo(e)
  }
  await recargar()
}

async function quitar(email: string) {
  if (!window.confirm(`¿Quitar el acceso de ${email}?`)) return
  try {
    await api(`/api/v1/admin/usuarios/${encodeURIComponent(email)}`, { metodo: 'DELETE' })
    mensaje.value = { tipo: 'bien', texto: `${email} ya no tiene acceso; sus sesiones se cerraron.` }
    if (temporal.value?.email === email) temporal.value = null
  } catch (e) {
    fallo(e)
  }
  await recargar()
}

const LECTURA: Clave[] = [
  { texto: 'Las tarjetas de arriba dicen qué puede hacer cada rol y cuántas personas lo tienen.' },
  { muestras: ['bien', 'aviso', 'critico'], texto: 'Estado: Activa; Contraseña temporal, si aún no entró a crear la suya; Bloqueada, tras cinco intentos fallidos (dura 15 minutos).' },
  { texto: 'Restablecer la contraseña o quitar el acceso cierra las sesiones abiertas de esa persona; cada cambio queda en Auditoría.' },
]

async function copiar() {
  if (!temporal.value) return
  try {
    await navigator.clipboard.writeText(temporal.value.clave)
    copiada.value = true
  } catch {
    copiada.value = false
  }
}
</script>

<template>
  <div class="pila">
    <EncabezadoSeccion
      modulo="usuarios"
      titulo="Usuarios y roles"
      subtitulo="Acceso cerrado por defecto: solo entra quien tiene un rol. Cada alta recibe una contraseña temporal que debe cambiar al entrar."
      :lectura="LECTURA"
    />

    <section class="roles">
      <div v-for="[r, nombre, texto, icono] in ROLES" :key="r" class="panel rol">
        <span class="icono-rol"><component :is="icono" :size="20" /></span>
        <div>
          <strong>{{ nombre }}</strong>
          <p class="tenue">{{ texto }}</p>
        </div>
        <span class="cuenta">{{ porRol[r] ?? 0 }}</span>
      </div>
    </section>

    <section class="panel">
      <form class="fila alta" @submit.prevent="guardar(nuevoEmail.trim().toLowerCase(), nuevoRol)">
        <UserPlus :size="20" class="marca-c" />
        <label class="campo">Correo <input v-model="nuevoEmail" type="email" required placeholder="persona@dominio.com" /></label>
        <label class="campo">Rol <select v-model="nuevoRol"><option v-for="[r, n] in ROLES" :key="r" :value="r">{{ n }}</option></select></label>
        <button type="submit" class="primario">Dar acceso</button>
      </form>
    </section>

    <section v-if="temporal" class="panel temporal" role="status">
      <span class="icono-rol"><KeyRound :size="20" /></span>
      <div class="explica">
        <strong>Contraseña temporal de {{ temporal.email }}</strong>
        <p class="secundario">Compártela por un canal privado. Se muestra una sola vez y deberá cambiarla al entrar.</p>
      </div>
      <code class="clave">{{ temporal.clave }}</code>
      <button type="button" @click="copiar">
        <component :is="copiada ? CircleCheck : Copy" :size="15" />{{ copiada ? 'Copiada' : 'Copiar' }}
      </button>
      <button type="button" class="icono fantasma" aria-label="Ocultar la contraseña temporal" @click="temporal = null"><X :size="17" /></button>
    </section>

    <p v-if="mensaje" class="aviso-caja" :class="mensaje.tipo" :role="mensaje.tipo === 'error' ? 'alert' : 'status'">
      <component :is="mensaje.tipo === 'bien' ? CircleCheck : CircleX" :size="17" />{{ mensaje.texto }}
    </p>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" forma="lista" @reintentar="recargar">
      <section class="panel lista">
        <div class="tabla-envoltura">
          <table>
            <thead><tr><th>Usuario</th><th>Rol</th><th>Estado</th><th>Último acceso</th><th><span class="visualmente-oculto">Acciones</span></th></tr></thead>
            <tbody>
              <tr v-for="u in datos ?? []" :key="u.email">
                <td>
                  <span class="fila persona">
                    <span class="avatar" aria-hidden="true">{{ u.email.slice(0, 2).toUpperCase() }}</span>
                    {{ u.email }}
                    <span v-if="u.email === sesion.perfil?.email" class="chip marca">tú</span>
                  </span>
                </td>
                <td>
                  <select :value="u.rol" :aria-label="`Rol de ${u.email}`" @change="cambiarRol(u, $event)">
                    <option v-for="[r, n] in ROLES" :key="r" :value="r">{{ n }}</option>
                  </select>
                </td>
                <td><span class="chip" :class="estado(u).tono">{{ estado(u).texto }}</span></td>
                <td class="secundario num">{{ hora(u.ultimo_acceso) }}</td>
                <td class="der">
                  <span v-if="u.email !== sesion.perfil?.email" class="fila acciones">
                    <button type="button" @click="restablecer(u.email)"><KeyRound :size="15" /> Restablecer contraseña</button>
                    <button type="button" class="peligro" @click="quitar(u.email)"><UserMinus :size="15" /> Quitar acceso</button>
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EstadoVacio
          v-if="!datos?.length"
          titulo="Nadie tiene acceso todavía"
          texto="Da acceso con el formulario de arriba: la persona recibe una contraseña temporal que cambia al entrar."
        />
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.roles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.rol { display: grid; grid-template-columns: 44px 1fr auto; gap: 12px; align-items: center; padding: 16px; }
.rol p { font-size: 12.5px; }
.icono-rol { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; background: var(--marca-suave); color: var(--marca); flex: none; }
.cuenta { font-size: 24px; font-weight: 800; }
.alta { align-items: end; gap: 14px; }
.alta > svg { margin-bottom: 8px; }
.marca-c { color: var(--marca); }
.temporal { display: flex; flex-wrap: wrap; align-items: center; gap: 14px; padding: 16px; border: 1px solid var(--aviso); background: var(--aviso-suave); }
.temporal .icono-rol { background: var(--superficie); color: var(--aviso-texto); }
.explica { flex: 1 1 260px; }
.explica p { font-size: 12.5px; }
.clave {
  font-family: 'JetBrains Mono', ui-monospace, monospace;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.06em;
  background: var(--superficie);
  border: 1px dashed var(--linea-fuerte);
  border-radius: 10px;
  padding: 7px 12px;
  user-select: all;
}
.lista { padding: 6px 8px; }
.persona { gap: 10px; flex-wrap: nowrap; }
.acciones { gap: 6px; justify-content: flex-end; flex-wrap: nowrap; }
.avatar { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--superficie-3); font-size: 11.5px; font-weight: 800; flex: none; }
</style>
