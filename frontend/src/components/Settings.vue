<template>
  <div class="absolute z-10 bg-light-content dark:bg-dark-content w-screen h-screen">
    <div class="flex flex-row-reverse">
      <Icon
        class="text-4xl m-2"
        :class="{
          'text-light-disabled-text dark:text-dark-disabled-text': !apiSecret(),
          'cursor-pointer text-light-text dark:text-dark-text hover:text-light-distinct-text dark:hover:text-dark-distinct-text': apiSecret()
        }"
        icon="fluent:dismiss-24-filled"
        @click="apiSecret() && $emit('close')"
      />
    </div>

    <div class="px-24 py-4 pb-24 max-w-3xl">
      <div class="text-4xl flex">
        <Icon class="mr-3 mb-4" icon="fluent:settings-24-filled" />
        Settings
      </div>
      <div>
      </div>
      <div class="relative flex items-center text-2xl rounded-lg bg-light-menu dark:bg-dark-menu elem-shadow-sm p-2">
        <Icon
          class="absolute left-3"
          :class="{
            'text-light-text dark:text-dark-text hover:text-light-distinct-text dark:hover:text-dark-distinct-text hover:cursor-pointer':
              inputText.length > 0
          }"
          icon="fluent:lock-closed-24-filled"
          size="2em"
        />

        <input
          v-model="inputText"
          type="password"
          class="w-full pl-12 pr-4 bg-transparent rounded-lg h-11 placeholder:text-light-distinct-text dark:placeholder:text-dark-distinct-text text-light-text dark:text-dark-text"
          :placeholder="$t('enter-api-secret')"
          autocomplete="off"
          @input="storeSecret"
          @keyup.enter="handleEnter"
        />

        <button
          class="ml-4 px-4 py-1 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
          @click="handleEnter"
        >
          Save
        </button>
      </div>
      <p v-if="errorMessage" class="text-red-500 mt-2">{{ errorMessage }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref, defineEmits } from 'vue'

const emit = defineEmits(['close'])
const inputText = ref(apiSecret() || '')
const errorMessage = ref('')

function storeSecret() {
  sessionStorage.setItem('api-secret', inputText.value)
}

function apiSecret() {
  const apiSecret = sessionStorage.getItem('api-secret')
  return apiSecret && apiSecret.length ? apiSecret : null
}

async function validateSecret() {
  errorMessage.value = '' // Clear previous errors
  try {
    const response = await fetch(`http://localhost:8000/item/query?query=`, {
      headers: { 'x-api-secret': inputText.value }
    })
    if (response.status === 401) {
      errorMessage.value = 'Invalid API secret. Please try again.'
    } else {
      storeSecret()
    }
  } catch (error) {
    errorMessage.value = 'Network error. Please try again later.'
  }
}

async function handleEnter() {
  await validateSecret()
  if (!errorMessage.value) {
    emit('close')
  }
}
</script>
