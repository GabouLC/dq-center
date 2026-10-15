<script setup lang="ts">
import { ref } from 'vue'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { api } from '@/servicios/api'
import { useSesion } from '@/stores/sesion'

type Usuario = { email: string; rol: string }

const ROLES = [
  ['lector', 'Lector: consulta indicadores; los campos sensibles aparecen ocultos.'],
  ['gobierno', 'Gobierno de datos: ve los campos sensibles y edita el glosario.'],
  ['admin', 'Administrador: además configura reglas, lanza corridas y gestiona usuarios.'],
]
const sesion = useSesion()
const { datos, cargando, error, recargar } = usarCarga(() => api<Usuario[]>('/api/v1/admin/usuarios'))
const nuevoEmail = ref('')
const nuevoRol = ref('lector')
const mensaje = ref<{ tipo: 'ok' | 'error'; texto: string } | null>(null)

async function guardar(email: string, rol: string) {
  mensaje.value = null
  try {
    await api(`/api/v1/admin/usuarios/${encodeURIComponent(email)}`, { metodo: 'PUT', cuerpo: { rol } })
    mensaje.value = { tipo: 'ok', texto: `${email} ahora es ${rol}.` }
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
    mensaje.value = { tipo: 'ok', texto: `${email} ya no tiene acceso.` }
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
        <p class="muted">Acceso cerrado por defecto: una cuenta sin rol no ve ningún módulo. Cada cambio queda en la auditoría.</p>
      </div>
    </div>

    <section class="tarjeta pila">
      <h2>Dar acceso</h2>
      <form class="fila" @submit.prevent="guardar(nuevoEmail.trim().toLowerCase(), nuevoRol)">
        <label class="campo">Correo <input v-model="nuevoEmail" type="email" required placeholder="persona@dominio.com" /></label>
        <label class="campo">Rol <select v-model="nuevoRol"><option v-for="[r] in ROLES" :key="r">{{ r }}</option></select></label>
        <button type="submit" class="primario">Guardar</button>
      </form>
      <ul class="roles muted">
        <li v-for="[r, d] in ROLES" :key="r">{{ d }}</li>
      </ul>
    </section>

    <p v-if="mensaje" class="aviso" :class="{ error: mensaje.tipo === 'error' }" role="status">{{ mensaje.texto }}</p>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <section class="tarjeta tabla-envoltura">
        <table>
          <thead><tr><th>Correo</th><th>Rol</th><th /></tr></thead>
          <tbody>
            <tr v-for="u in datos ?? []" :key="u.email">
              <td>{{ u.email }} <span v-if="u.email === sesion.perfil?.email" class="chip acento">tú</span></td>
              <td>
                <select :value="u.rol" :aria-label="`Rol de ${u.email}`" @change="guardar(u.email, ($event.target as HTMLSelectElement).value)">
                  <option v-for="[r] in ROLES" :key="r">{{ r }}</option>
                </select>
              </td>
              <td class="der">
                <button v-if="u.email !== sesion.perfil?.email" type="button" class="peligro" @click="quitar(u.email)">Quitar acceso</button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.roles { margin: 0; padding-left: 18px; font-size: 13px; }
.der { text-align: right; }
form.fila { align-items: end; }
</style>
