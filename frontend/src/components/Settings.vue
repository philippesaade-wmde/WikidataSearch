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

      <div class="px-24 py-4 pb-24 max-w-4xl">
        <div class="mb-24 flex items-center gap-6">
          <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="block">
            <img
                src="https://upload.wikimedia.org/wikipedia/commons/0/01/Wikidata_Embedding_Project_Logo.png"
                alt="Wikidata Embedding Project Logo"
                class="object-contain"
              />
          </a>

            <div>
              <div class="text-4xl py-2">
                <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="block">Wikidata Embedding Project</a>
              </div>
              <div class="text-lg py-2">
                <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="text-blue-600 dark:text-blue-400 hover:underline">The Wikidata Embedding Project</a> aims to build a vector database on top of Wikidata, enabling semantic search that retrieves items based on the contextual meaning of queries.
              </div>
            </div>
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
          Enter
        </button>
      </div>

      <p class="text-red-500 mt-2">{{ errorMessage }}&nbsp;</p>

      <!-- Partners Section -->
      <div class="mt-12">
        <h2 class="text-2xl font-bold mb-4 text-light-text dark:text-dark-text">Partners</h2>
        <div class="flex flex-wrap gap-6 items-center">
          <!-- Jina AI -->
          <a
            href="https://jina.ai/"
            target="_blank"
            rel="noopener"
            class="bg-white dark:bg-dark-menu p-4 rounded-xl shadow-md hover:shadow-lg transition-shadow flex items-center justify-center w-48 h-28"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 94 40" class="max-h-12 object-contain">
              <path fill="#EB6161" d="M6.12 39.92c3.38 0 6.12-2.74 6.12-6.12s-2.74-6.12-6.12-6.12S0 30.42 0 33.8s2.74 6.12 6.12 6.12z"/>
              <path fill="#009191" fill-rule="evenodd" d="M25.4 14.52c.8 0 1.44.64 1.44 1.44l-.08 11.72c0 6.68-5.36 12.12-12.04 12.24h-.2v-12.2h.04L14.6 16c0-.8.64-1.44 1.44-1.44h9.36v-.04zm18.8 0c.8 0 1.44.64 1.44 1.44v16.4c0 .8-.64 1.44-1.44 1.44h-9.36c-.8 0-1.44-.64-1.44-1.44v-16.4c0-.8.64-1.44 1.44-1.44h9.36zm14.72-.04h.2c6 .08 10.88 4.92 11.04 10.92v6.92c0 .8-.64 1.44-1.44 1.44H53.6c-.8 0-1.44-.64-1.44-1.44v-16.4c0-.8.64-1.44 1.44-1.44h5.32zM83.68 33.6c-5.04-.32-9.08-4.52-9.08-9.64 0-5.32 4.32-9.64 9.64-9.64 5.12 0 9.32 4 9.64 9.08v8.76c0 .8-.64 1.44-1.44 1.44h-8.76z" clip-rule="evenodd"/>
              <path fill="#FBCB67" d="M39.499 12.24c3.38 0 6.12-2.74 6.12-6.12S42.879 0 39.499 0s-6.12 2.74-6.12 6.12 2.74 6.12 6.12 6.12z"/>
            </svg>
          </a>

          <!-- Datastax -->
          <a
            href="https://www.datastax.com/"
            target="_blank"
            rel="noopener"
            class="bg-white dark:bg-dark-menu p-4 rounded-xl shadow-md hover:shadow-lg transition-shadow flex items-center justify-center w-48 h-28"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 3449 322" class="max-h-12 object-contain">
              <g clip-path="url(#clip0_209_456)">
              <path fill="black" d="M1730.24 321.98V252.991H2019.03V194.537H1793.51L1715.92 137.554V56.9835L1793.51 0H2069.99V68.9885H1788.39V125.549H2013.91L2091.48 182.512V265.017L2013.91 321.98H1730.24Z"/>
              <path fill="black" d="M790.073 321.98L648.375 88.124L506.445 321.98H422.767L618.085 0H678.432L873.751 321.98H790.073Z"/>
              <path fill="black" d="M1009.53 321.98V68.9885H857.971V0H1233.53V68.9885H1081.97V321.98H1009.53Z"/>
              <path fill="black" d="M2315.27 321.98V68.9885H2163.71V0H2539.29V68.9885H2387.73V321.98H2315.27Z"/>
              <path fill="black" d="M0 321.98V0H297.991L375.576 56.9835V265.017L297.991 322H0V321.98ZM303.109 252.991V68.9885H72.4459V252.991H303.109Z"/>
              <path fill="black" d="M3015.21 321.98L3112.85 161L3015.21 0H3098.87L3196.57 161L3098.87 321.98H3015.21Z"/>
              <path fill="black" d="M3366.02 321.98L3268.29 161L3366.02 0H3449.67L3352.01 161L3449.67 321.98H3366.02Z"/>
              <path fill="black" d="M1585.05 321.98L1443.12 88.124L1301.4 321.98H1217.73L1413.04 0H1473.39L1668.71 321.98H1585.05Z"/>
              <path fill="black" d="M2890.79 321.98L2748.88 88.124L2607.16 321.98H2523.49L2718.8 0H2779.15L2974.47 321.98H2890.79Z"/>
              </g>
              <defs>
              <clipPath id="clip0_209_456">
              <rect fill="white" height="322" width="3449"/>
              </clipPath>
              </defs>
            </svg>
          </a>
        </div>
      </div>


      <!-- Contributors Section -->
      <div class="mt-10">
        <h2 class="text-2xl font-bold mb-4 text-light-text dark:text-dark-text">Contributors</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Philippe -->
          <div
            class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow"
          >
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/59/Philippe_Saade.jpg/150px-Philippe_Saade.jpg"
              alt="Philippe Saadé"
              class="w-12 h-12 rounded-full object-cover mr-4"
            />
            <div>
              <a
                href="https://www.wikidata.org/wiki/User:Philippe_Saade_(WMDE)"
                target="_blank"
                class="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline"
              >
                Philippe Saadé
              </a>
              <p class="text-sm text-light-text dark:text-dark-text">
                AI/ML Project Manager, WMDE
              </p>
            </div>
          </div>

          <!-- Robert -->
          <div
            class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow"
          >
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/thumb/5/5b/Portrait_Robert_Timm_2023.jpg/150px-Portrait_Robert_Timm_2023.jpg"
              alt="Robert Timm"
              class="w-12 h-12 rounded-full object-cover mr-4"
            />
            <div>
              <a
                href="https://www.wikidata.org/wiki/User:Robert_Timm_(WMDE)"
                target="_blank"
                class="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline"
              >
                Robert Timm
              </a>
              <p class="text-sm text-light-text dark:text-dark-text">
                Senior Software Engineer, Wikibase Suite, WMDE
              </p>
            </div>
          </div>

          <!-- Jonathan -->
          <div
            class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow"
          >
            <img
              src="https://avatars.githubusercontent.com/u/11221046"
              alt="Jonathan Fraine"
              class="w-12 h-12 rounded-full object-cover mr-4"
            />
            <div>
              <a
                href="https://meta.wikimedia.org/wiki/User:Exowanderer"
                target="_blank"
                class="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline"
              >
                Jonathan Fraine
              </a>
              <p class="text-sm text-light-text dark:text-dark-text">
                Co-Head of Software Development, CTO, WMDE
              </p>
            </div>
          </div>

          <!-- Andrew -->
          <div
            class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow"
          >
            <img
              src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/75/AndrewtavisIconRounded.png/150px-AndrewtavisIconRounded.png"
              alt="Andrew Tavis McAllister"
              class="w-12 h-12 rounded-full object-cover mr-4"
            />
            <div>
              <a
                href="https://www.wikidata.org/wiki/User:Andrew_McAllister_(WMDE)"
                target="_blank"
                class="text-lg font-semibold text-blue-600 dark:text-blue-400 hover:underline"
              >
                Andrew Tavis McAllister
              </a>
              <p class="text-sm text-light-text dark:text-dark-text">
                Data Analyst, WMDE
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- Resources Section -->
      <div class="mt-12">
        <h2 class="text-2xl font-bold mb-4 text-light-text dark:text-dark-text">Resources</h2>
        <div class="flex flex-wrap gap-4">
          <!-- API Docs -->
          <a
            href="/docs"
            target="_blank"
            rel="noopener"
            class="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-md"
          >
          API Documentation
          </a>

          <!-- Project Page -->
          <a
            href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project"
            target="_blank"
            rel="noopener"
            class="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors shadow-md"
          >
            Wikidata Embedding Project
          </a>
        </div>
      </div>

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
    const response = await fetch(`/item/query/?query=`, {
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
