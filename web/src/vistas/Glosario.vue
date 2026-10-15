<script setup lang="ts">
import { BookOpen, FileText, ListChecks, Lock, Pencil, Plus, Search, User, Workflow } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import BloqueCarga from '@/componentes/BloqueCarga.vue'
import { usarCarga } from '@/composables/usarCarga'
import { api } from '@/servicios/api'
import { useSesion } from '@/stores/sesion'

type Termino = { id: string; termino: string; definicion: string; dominio: string; sinonimos?: string[]; campos?: string[] }

const DOMINIOS: [string, unknown][] = [['Póliza', FileText], ['Persona', User], ['Calidad', ListChecks], ['Privacidad', Lock]]
const ICONO_DOMINIO = Object.fromEntries(DOMINIOS)
const ruta = useRoute()
const router = useRouter()
const sesion = useSesion()
const q = ref('')
const dominio = ref('')
const letra = ref('')
const buscado = ref('')
let espera: ReturnType<typeof setTimeout> | undefined
watch(q, (v) => {
  clearTimeout(espera)
  letra.value = ''
  espera = setTimeout(() => (buscado.value = v), 220)
})

const { datos, cargando, error, recargar } = usarCarga(
  () => api<Termino[]>('/api/v1/glosario', { params: { q: buscado.value } }),
  [buscado],
)
const inicial = (t: Termino) => t.termino.normalize('NFKD')[0].toUpperCase()
const filtrados = computed(() =>
  (datos.value ?? []).filter((t) => (!dominio.value || t.dominio === dominio.value) && (!letra.value || inicial(t) === letra.value)),
)
const letras = computed(() => new Set((datos.value ?? []).filter((t) => !dominio.value || t.dominio === dominio.value).map(inicial)))
const ABC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('')
const cuenta = (d: string) => (datos.value ?? []).filter((t) => t.dominio === d).length
const elegido = computed(() => filtrados.value.find((t) => t.id === ruta.params.id) ?? filtrados.value[0] ?? null)
const relacionados = computed(() =>
  elegido.value ? (datos.value ?? []).filter((t) => t.dominio === elegido.value!.dominio && t.id !== elegido.value!.id).slice(0, 8) : [],
)

// Edición (gobierno y admin)
const editando = ref(false)
const borrador = ref<Termino | null>(null)
const errorGuardar = ref<string | null>(null)
function editar(t: Termino | null) {
  borrador.value = t
    ? { ...t, sinonimos: [...(t.sinonimos ?? [])], campos: [...(t.campos ?? [])] }
    : { id: '', termino: '', definicion: '', dominio: 'Póliza', sinonimos: [], campos: [] }
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
        <p>Qué significa cada término y dónde vive en los datos (HU-10).</p>
      </div>
      <button v-if="sesion.puede('editar_glosario')" type="button" class="primario" @click="editar(null)"><Plus :size="16" /> Nuevo término</button>
    </div>

    <div class="panel buscador-grande">
      <label class="buscar"><Search :size="20" /><input v-model="q" type="search" placeholder="Busca un término: prima, DNI, vigencia, cifrado…" aria-label="Buscar término" /></label>
      <div class="fila">
        <button type="button" class="dominio" :class="{ activo: !dominio }" @click="dominio = ''"><BookOpen :size="15" /> Todos <span class="cuenta">{{ datos?.length ?? 0 }}</span></button>
        <button v-for="[d, icono] in DOMINIOS" :key="d" type="button" class="dominio" :class="{ activo: dominio === d }" @click="dominio = dominio === d ? '' : d">
          <component :is="icono" :size="15" /> {{ d }} <span class="cuenta">{{ cuenta(d) }}</span>
        </button>
      </div>
      <nav class="abc" aria-label="Índice alfabético">
        <button
          v-for="l in ABC"
          :key="l"
          type="button"
          :disabled="!letras.has(l)"
          :class="{ activo: letra === l }"
          @click="letra = letra === l ? '' : l"
        >{{ l }}</button>
      </nav>
    </div>

    <BloqueCarga :cargando="cargando" :error="error" :vacio="!datos" @reintentar="recargar">
      <div class="disposicion">
        <nav class="panel lista" aria-label="Términos">
          <p v-if="!filtrados.length" class="tenue">Ningún término coincide. Prueba con otra palabra.</p>
          <RouterLink v-for="t in filtrados" :key="t.id" :to="`/glosario/${t.id}`" :class="{ activo: elegido?.id === t.id }">
            <component :is="ICONO_DOMINIO[t.dominio]" :size="15" class="icono-dominio" />
            <span>{{ t.termino }}</span>
          </RouterLink>
        </nav>

        <article v-if="editando && borrador" class="panel pila">
          <h2>{{ borrador.id ? 'Editar término' : 'Nuevo término' }}</h2>
          <label class="campo">Término <input v-model="borrador.termino" required /></label>
          <label class="campo">Dominio
            <select v-model="borrador.dominio"><option v-for="[d] in DOMINIOS" :key="d">{{ d }}</option></select>
          </label>
          <label class="campo">Definición <textarea v-model="borrador.definicion" rows="4" /></label>
          <label class="campo">Sinónimos (separados por coma)
            <input :value="borrador.sinonimos?.join(', ')" @change="borrador.sinonimos = lista(($event.target as HTMLInputElement).value)" />
          </label>
          <label class="campo">Campos relacionados (tabla.campo, separados por coma)
            <input :value="borrador.campos?.join(', ')" @change="borrador.campos = lista(($event.target as HTMLInputElement).value)" />
          </label>
          <p v-if="errorGuardar" class="aviso-caja error">{{ errorGuardar }}</p>
          <div class="fila">
            <button type="button" class="primario" @click="guardar">Guardar término</button>
            <button type="button" class="fantasma" @click="editando = false">Cancelar</button>
          </div>
        </article>

        <article v-else-if="elegido" class="panel ficha">
          <div class="fila entre">
            <span class="chip marca"><component :is="ICONO_DOMINIO[elegido.dominio]" :size="13" /> {{ elegido.dominio }}</span>
            <button v-if="sesion.puede('editar_glosario')" type="button" class="fantasma" @click="editar(elegido)"><Pencil :size="15" /> Editar</button>
          </div>
          <h2 class="termino">{{ elegido.termino }}</h2>
          <p class="definicion">{{ elegido.definicion }}</p>
          <p v-if="elegido.sinonimos?.length" class="secundario">También se le dice: <strong>{{ elegido.sinonimos.join(', ') }}</strong></p>
          <div v-if="elegido.campos?.length" class="pila-chica">
            <h3>Dónde está en los datos</h3>
            <div class="fila">
              <RouterLink v-for="c in elegido.campos" :key="c" :to="`/linaje/${c.split('.')[0]}`" class="chip sello">
                <Workflow :size="12" /> {{ c }}
              </RouterLink>
            </div>
          </div>
          <div v-if="relacionados.length" class="pila-chica relacionados">
            <h3>Del mismo dominio</h3>
            <div class="fila">
              <RouterLink v-for="t in relacionados" :key="t.id" :to="`/glosario/${t.id}`" class="chip">{{ t.termino }}</RouterLink>
            </div>
          </div>
        </article>
      </div>
    </BloqueCarga>
  </div>
</template>

<style scoped>
.buscador-grande { display: grid; gap: 14px; }
.buscar { display: flex; align-items: center; gap: 10px; border: 2px solid var(--linea-fuerte); border-radius: 14px; padding: 4px 16px; color: var(--tenue); transition: border-color 0.12s; }
.buscar:focus-within { border-color: var(--marca); }
.buscar input { border: 0; outline: none; background: transparent; font-size: 16px; padding: 10px 0; flex: 1; min-width: 0; }
.dominio .cuenta { font-size: 11.5px; color: var(--tenue); font-weight: 800; }
.dominio.activo { background: var(--marca); color: var(--sobre-marca); border-color: var(--marca); }
.dominio.activo .cuenta { color: var(--sobre-marca); opacity: 0.8; }
.abc { display: flex; flex-wrap: wrap; gap: 4px; }
.abc button { width: 32px; height: 32px; padding: 0; justify-content: center; border-radius: 8px; font-weight: 800; font-size: 13px; }
.abc button.activo { background: var(--marca); color: var(--sobre-marca); border-color: var(--marca); }
.abc button:disabled { opacity: 0.3; }
.disposicion { display: grid; grid-template-columns: 300px 1fr; gap: 18px; align-items: start; }
.lista { display: grid; gap: 2px; padding: 8px; max-height: 64vh; overflow: auto; }
.lista a { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 10px; color: var(--tinta); font-weight: 600; text-decoration: none; }
.lista a:hover { background: var(--superficie-2); }
.lista a.activo { background: var(--marca-suave); color: var(--marca); }
.icono-dominio { color: var(--tenue); flex: none; }
.lista a.activo .icono-dominio { color: var(--marca); }
.ficha { display: grid; gap: 14px; padding: 28px; }
.termino { font-size: 32px; font-weight: 800; letter-spacing: -0.02em; }
.definicion { font-size: 18px; line-height: 1.6; max-width: 62ch; }
.relacionados { padding-top: 14px; border-top: 1px solid var(--linea); }
@media (max-width: 860px) {
  .disposicion { grid-template-columns: 1fr; }
  .lista { max-height: 240px; }
  .termino { font-size: 26px; }
  .definicion { font-size: 16px; }
}
</style>
