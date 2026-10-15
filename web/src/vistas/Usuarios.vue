<script setup lang="ts">
import { BookOpen, CircleCheck, CircleX, ShieldCheck, SlidersHorizontal, UserMinus, UserPlus } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { api } from '@/servicios/api'
import { useSesion } from '@/stores/sesion'

type Usuario = { email: string; rol: string }

const ROLES: [string, string, string, unknown][] = [
  ['lector', 'Lector', 'Consulta indicadores; los campos sensibles aparecen ocultos.', ShieldCheck],
  ['gobierno', 'Gobierno de datos', 'Ve los campos sensibles y edita el glosario.', BookOpen],
  ['admin', 'Administrador', 'Configura reglas, lanza corridas y gestiona usuarios.', SlidersHorizontal],
]
const sesion = useSesion()
const { datos, cargando, error, recargar } = usarCarga(() => api<Usuario[]>('/api/v1/admin/usuarios'))
const nuevoEmail = ref('')
const nuevoRol = ref('lector')
const mensaje = ref<{ tipo: 'bien' | 'error'; texto: string } | null>(null)
const porRol = computed(() => Object.fromEntries(ROLES.map(([r]) => [r, (datos.value ?? []).filter((u) => u.rol === r).length])))

async function guardar(email: string, rol: string) {
  mensaje.value = null
  try {
    await api(`/api/v1/admin/usuarios/${encodeURIComponent(email)}`, { metodo: 'PUT', cuerpo: { rol } })
    mensaje.value = { tipo: 'bien', texto: `${email} ahora tiene el rol ${rol}.` }
    nuevoEmail.value = ''
  } catch (e) {
    mensaje.value = { tipo: 'error', texto: e instanceof Error ? e.message : String(e) }
  }
  await recargar()
}

async function quitar(email: string) {
  if (!window.confirm(`¿Quitar el acceso de ${email}?`)) return
  try {
    await api(`/api/v1/admin/usuarios/${encodeURIComponent(email)}`, { metodo: 'DELETE' })
    mensaje.value = { tipo: 'bien', texto: `${email} ya no tiene acceso.` }
  } catch (e) {
    mensaje.value = { tipo: 'error', texto: e instanceof Error ? e.message : String(e) }
  }
  await recargar()
}
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Usuarios y roles</h1>
        <p>Acceso cerrado por defecto: una cuenta sin rol no ve ningún módulo. Cada cambio queda en la auditoría.</p>
      </div>
    </div>

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

    <p v-if="mensaje" class="aviso-caja" :class="mensaje.tipo" role="status">
      <component :is="mensaje.tipo === 'bien' ? CircleCheck : CircleX" :size="17" />{{ mensaje.texto }}
    </p>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="panel lista">
        <div class="tabla-envoltura">
          <table>
            <thead><tr><th>Usuario</th><th>Rol</th><th /></tr></thead>
            <tbody>
              <tr v-for="u in datos ?? []" :key="u.email">
                <td>
                  <span class="fila persona">
                    <span class="avatar">{{ u.email.slice(0, 2).toUpperCase() }}</span>
                    {{ u.email }}
                    <span v-if="u.email === sesion.perfil?.email" class="chip marca">tú</span>
                  </span>
                </td>
                <td>
                  <select :value="u.rol" :aria-label="`Rol de ${u.email}`" @change="guardar(u.email, ($event.target as HTMLSelectElement).value)">
                    <option v-for="[r, n] in ROLES" :key="r" :value="r">{{ n }}</option>
                  </select>
                </td>
                <td class="der">
                  <button v-if="u.email !== sesion.perfil?.email" type="button" class="peligro" @click="quitar(u.email)">
                    <UserMinus :size="15" /> Quitar acceso
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.roles { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
.rol { display: grid; grid-template-columns: 44px 1fr auto; gap: 12px; align-items: center; padding: 16px; }
.rol p { font-size: 12.5px; }
.icono-rol { display: grid; place-items: center; width: 44px; height: 44px; border-radius: 12px; background: var(--marca-suave); color: var(--marca); }
.cuenta { font-size: 24px; font-weight: 800; }
.alta { align-items: end; gap: 14px; }
.alta > svg { margin-bottom: 8px; }
.marca-c { color: var(--marca); }
.lista { padding: 6px 8px; }
.persona { gap: 10px; flex-wrap: nowrap; }
.avatar { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--superficie-3); font-size: 11.5px; font-weight: 800; flex: none; }
</style>
