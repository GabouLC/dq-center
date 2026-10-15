<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { api } from '@/servicios/api'
import { useSesion } from '@/stores/sesion'

type Termino = { id: string; termino: string; definicion: string; dominio: string; sinonimos?: string[]; campos?: string[] }

const DOMINIOS = ['Póliza', 'Persona', 'Calidad', 'Privacidad']
const ruta = useRoute()
const router = useRouter()
const sesion = useSesion()
const q = ref('')
const dominio = ref('')
const buscado = ref('')
let espera: ReturnType<typeof setTimeout> | undefined
watch(q, (v) => {
  clearTimeout(espera)
  espera = setTimeout(() => (buscado.value = v), 250)
})

const { datos, cargando, error, recargar } = usarCarga(
  () => api<Termino[]>('/api/v1/glosario', { params: { q: buscado.value, dominio: dominio.value } }),
  [buscado, dominio],
)
const elegido = computed(() => datos.value?.find((t) => t.id === ruta.params.id) ?? datos.value?.[0] ?? null)

// Edición (gobierno y admin)
const editando = ref(false)
const borrador = ref<Termino | null>(null)
const errorGuardar = ref<string | null>(null)
function editar(t: Termino | null) {
  borrador.value = t ? { ...t, sinonimos: [...(t.sinonimos ?? [])], campos: [...(t.campos ?? [])] } : { id: '', termino: '', definicion: '', dominio: 'Póliza', sinonimos: [], campos: [] }
  errorGuardar.value = null
  editando.value = true
}
async function guardar() {
  if (!borrador.value) return
  const id = borrador.value.id || borrador.value.termino.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  try {
    await api(`/api/v1/glosario/${id}`, { metodo: 'PUT', cuerpo: { ...borrador.value, id } })
    editando.value = false
    await recargar()
    await router.push(`/glosario/${id}`)
  } catch (e) {
    errorGuardar.value = e instanceof Error ? e.message : String(e)
  }
}
const lista = (texto: string) => texto.split(',').map((s) => s.trim()).filter(Boolean)
</script>

<template>
  <div class="pila">
    <div class="encabezado">
      <div>
        <h1>Glosario de negocio</h1>
        <p class="muted">Qué significa cada término y dónde vive en los datos (HU-10).</p>
      </div>
      <button v-if="sesion.puede('editar_glosario')" type="button" class="primario" @click="editar(null)">Nuevo término</button>
    </div>

    <div class="fila">
      <input v-model="q" type="search" placeholder="Buscar: prima, DNI, vigencia…" aria-label="Buscar término" class="buscador" />
      <button type="button" :class="{ primario: !dominio }" @click="dominio = ''">Todos</button>
      <button v-for="d in DOMINIOS" :key="d" type="button" :class="{ primario: dominio === d }" @click="dominio = d">{{ d }}</button>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <div class="disposicion">
        <nav class="tarjeta lista" aria-label="Términos">
          <p v-if="!datos?.length" class="muted">Ningún término coincide.</p>
          <RouterLink
            v-for="t in datos ?? []"
            :key="t.id"
            :to="`/glosario/${t.id}`"
            :class="{ activo: elegido?.id === t.id }"
          >
            <strong>{{ t.termino }}</strong>
            <span class="muted pequeno">{{ t.dominio }}</span>
          </RouterLink>
        </nav>

        <article v-if="editando && borrador" class="tarjeta pila">
          <h2>{{ borrador.id ? 'Editar término' : 'Nuevo término' }}</h2>
          <label class="campo">Término <input v-model="borrador.termino" required /></label>
          <label class="campo">Dominio
            <select v-model="borrador.dominio"><option v-for="d in DOMINIOS" :key="d">{{ d }}</option></select>
          </label>
          <label class="campo">Definición <textarea v-model="borrador.definicion" rows="4" /></label>
          <label class="campo">Sinónimos (separados por coma)
            <input :value="borrador.sinonimos?.join(', ')" @change="borrador.sinonimos = lista(($event.target as HTMLInputElement).value)" />
          </label>
          <label class="campo">Campos relacionados (tabla.campo, separados por coma)
            <input :value="borrador.campos?.join(', ')" @change="borrador.campos = lista(($event.target as HTMLInputElement).value)" />
          </label>
          <p v-if="errorGuardar" class="aviso error">{{ errorGuardar }}</p>
          <div class="fila">
            <button type="button" class="primario" @click="guardar">Guardar</button>
            <button type="button" @click="editando = false">Cancelar</button>
          </div>
        </article>

        <article v-else-if="elegido" class="tarjeta pila">
          <div class="fila entre">
            <div>
              <span class="chip acento">{{ elegido.dominio }}</span>
              <h2 class="titulo">{{ elegido.termino }}</h2>
            </div>
            <button v-if="sesion.puede('editar_glosario')" type="button" @click="editar(elegido)">Editar</button>
          </div>
          <p class="definicion">{{ elegido.definicion }}</p>
          <p v-if="elegido.sinonimos?.length" class="muted">También: {{ elegido.sinonimos.join(', ') }}</p>
          <div v-if="elegido.campos?.length" class="pila campos">
            <h3>Dónde está en los datos</h3>
            <div class="fila">
              <RouterLink v-for="c in elegido.campos" :key="c" :to="`/linaje/${c.split('.')[0]}`" class="chip mono">{{ c }}</RouterLink>
            </div>
          </div>
        </article>
      </div>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.buscador { min-width: 280px; flex: 1; max-width: 420px; }
.disposicion { display: grid; grid-template-columns: 300px 1fr; gap: 16px; align-items: start; }
.lista { display: grid; gap: 2px; padding: 8px; max-height: 70vh; overflow: auto; }
.lista a { display: grid; padding: 8px 10px; border-radius: 8px; color: var(--fg); text-decoration: none; }
.lista a:hover { background: var(--surface-2); }
.lista a.activo { background: var(--accent-soft); }
.pequeno { font-size: 12px; }
.titulo { font-size: 20px; margin-top: 6px; }
.definicion { font-size: 15px; max-width: 70ch; }
.campos { gap: 8px; }
@media (max-width: 800px) {
  .disposicion { grid-template-columns: 1fr; }
  .lista { max-height: 240px; }
}
</style>
