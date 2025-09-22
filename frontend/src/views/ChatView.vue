<template>
  <main class="w-screen min-h-screen bg-light-content dark:bg-dark-content overflow-auto">

    <!-- Settings Modal -->
    <Settings v-if="showSettings" @close="showSettings = false" />

    <!-- Settings Icon -->
    <Icon
      class="text-4xl absolute right-4 top-4 cursor-pointer text-light-text dark:text-dark-text hover:text-light-distinct-text dark:hover:text-dark-distinct-text transition-colors"
      icon="fluent:line-horizontal-3-24-filled"
      @click="showSettings = true"
    />

    <div class="max-w-screen-2xl mx-auto px-4 sm:px-8 md:px-12 py-12 space-y-12">

      <!-- Header -->
      <div class="flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left justify-center">
        <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="shrink-0">
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/0/01/Wikidata_Embedding_Project_Logo.png"
            alt="Wikidata Embedding Project Logo"
            class="h-24 object-contain"
          />
        </a>
        <div>
          <h1 class="text-5xl font-bold py-2">
            <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="hover:underline block">
              Wikidata Embedding Project
            </a>
          </h1>
        </div>
      </div>

      <!-- Input + Send Button -->
      <div class="flex justify-center w-full">
        <div class="flex flex-col w-full md:w-4/5 space-y-4">

          <div class="relative flex text-2xl rounded-lg bg-light-menu dark:bg-dark-menu elem-shadow-sm">
            <input
              v-model="inputText"
              type="text"
              class="w-full pl-4 bg-transparent rounded-lg h-12 placeholder:text-light-distinct-text dark:placeholder:text-dark-distinct-text text-light-text dark:text-dark-text"
              :placeholder="$t('chat-prompt')"
              autocomplete="off"
              @keyup.enter="inputText.length > 0 ? search() : {}"
              @focus="inputFocused = true"
              @blur="inputFocused = false"
            />
            <Icon
              class="absolute -translate-y-1/2 right-3 top-1/2"
              :class="{
                'text-light-text dark:text-dark-text': inputFocused && inputText.length === 0,
                'text-light-text dark:text-dark-text hover:text-light-distinct-text dark:hover:text-dark-distinct-text hover:cursor-pointer':
                  inputFocused && inputText.length > 0,
                'text-light-distinct-text dark:text-dark-distinct-text': !inputFocused
              }"
              icon="fluent:send-24-filled"
              size="2em"
              @click="inputText.length > 0 ? search() : {}"
            />
          </div>

          <!-- Controls -->
          <div class="flex items-center justify-between gap-4 flex-wrap text-sm text-light-text dark:text-dark-text">

            <!-- Language Selector -->
            <div class="flex flex-col md:flex-row items-start md:items-center gap-4 text-sm text-light-text dark:text-dark-text">

              <!-- Radios for vectordb_langs -->
              <div class="flex gap-4 items-center flex-wrap">
                <label
                  v-for="lang in vectordbLangs"
                  :key="lang"
                  class="flex items-center gap-1 cursor-pointer px-2 py-1 border rounded-lg hover:bg-light-menu dark:hover:bg-dark-menu transition-colors"
                >
                  <input type="radio" :value="lang" v-model="selectedLanguage" class="accent-blue-600" />
                  {{ lang.toUpperCase() }}
                </label>
              </div>

              <!-- Dropdown for other languages -->
              <div v-if="otherLanguages.length > 0" class="flex items-center gap-2 relative group">
                <select
                  v-model="selectedLanguage"
                  class="rounded-lg border border-light-distinct-text dark:border-dark-distinct-text bg-light-menu dark:bg-dark-menu text-light-text dark:text-dark-text h-8 px-2"
                >
                  <option v-for="lang in otherLanguages" :key="lang" :value="lang">
                    {{ lang.toUpperCase() }}
                  </option>
                </select>

                <!-- Info Icon Tooltip -->
                <div>
                  <Icon
                    icon="fluent:info-16-regular"
                    class="text-blue-600 dark:text-blue-400 cursor-pointer ml-1"
                  />
                  <div
                    class="absolute left-1/2 -translate-x-1/2 top-full mt-1 w-80 p-3 bg-light-menu dark:bg-dark-menu text-sm text-light-text dark:text-dark-text rounded shadow-lg opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none"
                  >
                    <p class="font-semibold mb-3">Language Selection Info</p>
                    <p class="mb-2">
                      <strong>Radio buttons</strong> represent languages with dedicated vector datasets. Selecting one queries vectors in that language.
                    </p>
                    <p class="mb-2">
                      <strong>Dropdown menu</strong> shows other languages without dedicated vectors. Selecting one will translate your query to English and search the full vector database.
                    </p>
                    <p>
                      The <strong>'ALL'</strong> option queries the full vector database regardless of language. More languages will be added as dedicated vectors in future releases.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <!-- Items / Properties toggle -->
            <div class="flex items-center gap-2">
              <div class="inline-flex h-8 rounded-lg overflow-hidden border border-light-distinct-text dark:border-dark-distinct-text">
                <button
                  class="px-3 h-full flex items-center text-base font-medium"
                  :class="searchType === 'item'
                    ? 'bg-light-menu dark:bg-dark-menu text-light-text dark:text-dark-text'
                    : 'bg-transparent text-light-distinct-text dark:text-dark-distinct-text'"
                  @click="searchType = 'item'"
                  type="button"
                >
                  Items
                </button>
                <button
                  class="px-3 h-full flex items-center text-base font-medium"
                  :class="searchType === 'property'
                    ? 'bg-light-menu dark:bg-dark-menu text-light-text dark:text-dark-text'
                    : 'bg-transparent text-light-distinct-text dark:text-dark-distinct-text'"
                  @click="searchType = 'property'"
                  type="button"
                >
                  Properties
                </button>
              </div>
            </div>

          </div>

          <!-- Prototype Warning -->
          <p class="text-sm text-light-text dark:text-dark-text">
            ⚠️ This tool is in early testing, and results may be incomplete or inaccurate. Your queries are sent to a third-party service (JinaAI) for processing, and we store them for up to 90 days for quality improvements. We welcome your feedback! Please help us improve by filling out
            <a href="https://wikimedia.sslsurvey.de/Wikidata-Vector-DB-Feedback-Alpha-release" target="_blank"
               class="text-blue-600 dark:text-blue-400 hover:underline">
              our survey
            </a>.
          </p>

          <!-- Error Message -->
          <p v-if="error && error.length" class="mt-0 text-sm text-red-500">{{ error }}</p>

        </div>
      </div>

      <!-- Response -->
      <div v-if="response" class="flex justify-center w-full">
        <div class="flex flex-col w-full md:w-4/5 space-y-7">
          <FieldAnswer :response="response" :isLoading="false" />
        </div>
      </div>

      <!-- Loading -->
      <div v-else-if="displayResponse && !response" class="flex justify-center w-full">
        <div class="flex flex-col w-full md:w-4/5 space-y-5">
          <FieldAnswer :isLoading="true" />
        </div>
      </div>

    </div>
  </main>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref, onMounted } from 'vue'
import FieldAnswer from '../components/field/FieldAnswer.vue'
import type { ResponseObject } from '../types/response-object.d.ts'
import Settings from '../components/Settings.vue'

const inputText = ref('')
const response = ref<ResponseObject[]>()
const error = ref<string>()
const displayResponse = ref(false)
const inputFocused = ref(false)
const showSettings = ref(true)
const searchType = ref<'item' | 'property'>('item')

// Languages
const vectordbLangs = ref<string[]>([])
const otherLanguages = ref<string[]>([])
const selectedLanguage = ref<string>('All')

function apiSecret() {
  const secret = sessionStorage.getItem('api-secret')
  return secret?.length ? secret : null
}

// Fetch /languages on mount
onMounted(async () => {
  try {
    const res = await fetch('/languages')
    const data = await res.json()
    vectordbLangs.value = ['all', ...data.vectordb_langs]
    otherLanguages.value = data.other_langs
    if (!vectordbLangs.value.includes(selectedLanguage.value.toLowerCase())) {
      selectedLanguage.value = 'ALL'
    }
  } catch (e) {
    console.error('Failed to fetch languages', e)
  }
})

async function search() {
  response.value = undefined
  error.value = undefined
  displayResponse.value = true

  const secret = apiSecret()
  let lang = selectedLanguage.value.toLowerCase() || 'all'

  try {
    const base = searchType.value === 'property' ? '/property/query' : '/item/query'
    const fetchResult = await fetch(
      `${base}/?query=${encodeURIComponent(inputText.value)}&rerank=True&lang=${lang}`,
      {
        headers: secret ? { 'x-api-secret': secret } : {}
      }
    )

    if (fetchResult.status === 401) {
      showSettings.value = true
      displayResponse.value = false
      return
    }

    const jsonResponse = await fetchResult.json()

    if (!lang || lang === 'all') {
      lang = 'en'
    }

    // Add the user query and lang to each result for feedback tracking
    response.value = jsonResponse.map((r: any) => ({
      ...r,
      id: r.QID ?? r.PID,
      query: inputText.value,
      lang: lang
    }))
  } catch (e) {
    displayResponse.value = false
    console.error(e)
    error.value = 'Sorry. Failed to retrieve response.'
  }
}
</script>
