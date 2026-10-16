<script setup lang="ts">
import { Eye, EyeOff, LockKeyhole } from 'lucide-vue-next'
import { ref } from 'vue'

/** Contraseña con botón para mostrarla y aviso de Bloq Mayús. */
const modelo = defineModel<string>({ required: true })
defineProps<{ id: string; etiqueta: string; autocomplete: 'current-password' | 'new-password' }>()

const visible = ref(false)
const mayusculas = ref(false)
const revisar = (e: KeyboardEvent) => (mayusculas.value = e.getModifierState?.('CapsLock') ?? false)
</script>

<template>
  <div class="campo-entrada">
    <label :for="id" class="etiqueta">{{ etiqueta }}</label>
    <div class="caja-entrada">
      <LockKeyhole :size="17" aria-hidden="true" />
      <input
        :id="id"
        v-model="modelo"
        :type="visible ? 'text' : 'password'"
        :autocomplete="autocomplete"
        :aria-describedby="mayusculas ? `${id}-mayus` : undefined"
        spellcheck="false"
        required
        @keydown="revisar"
        @keyup="revisar"
        @blur="mayusculas = false"
      />
      <button
        type="button"
        class="icono fantasma ver"
        :aria-label="visible ? 'Ocultar contraseña' : 'Mostrar contraseña'"
        :aria-pressed="visible"
        :title="visible ? 'Ocultar' : 'Mostrar'"
        @click="visible = !visible"
      >
        <component :is="visible ? EyeOff : Eye" :size="17" />
      </button>
    </div>
    <p v-if="mayusculas" :id="`${id}-mayus`" class="mayus">Bloq Mayús está activado</p>
  </div>
</template>

<style scoped>
.mayus { font-size: 12px; font-weight: 600; color: var(--aviso-texto); }
</style>
