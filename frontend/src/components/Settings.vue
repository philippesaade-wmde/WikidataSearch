<template>
  <div class="absolute z-10 bg-light-content dark:bg-dark-content w-screen h-screen overflow-auto">
    <!-- Close button -->
    <div class="flex justify-end p-4">
      <Icon
        class="text-3xl"
        :class="{
          'text-light-disabled-text dark:text-dark-disabled-text': !canClose,
          'cursor-pointer text-light-text dark:text-dark-text hover:text-light-distinct-text dark:hover:text-dark-distinct-text transition-colors':
            canClose
        }"
        icon="fluent:dismiss-24-filled"
        @click="canClose && $emit('close')"
      />
    </div>

    <div class="max-w-screen-lg mx-auto px-4 sm:px-8 md:px-12 space-y-12 pb-16">

      <!-- Header -->
      <div class="flex flex-col sm:flex-row items-center gap-6 text-center sm:text-left">
        <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="shrink-0">
          <img
            src="https://upload.wikimedia.org/wikipedia/commons/0/01/Wikidata_Embedding_Project_Logo.png"
            alt="Wikidata Embedding Project Logo"
            class="h-20 object-contain"
          />
        </a>
        <div>
          <h1 class="text-3xl sm:text-4xl font-bold">
            <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank" class="hover:underline">
              Wikidata Embedding Project
            </a>
          </h1>
          <p class="text-lg text-light-text dark:text-dark-text leading-relaxed mt-2">
            <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank"
               class="text-blue-600 dark:text-blue-400 hover:underline">
              The Wikidata Embedding Project
            </a>
            aims to build a vector database on top of Wikidata, enabling semantic search that retrieves items based on contextual meaning.
          </p>
        </div>
      </div>

      <!-- Divider -->
      <hr class="border-light-distinct-text dark:border-dark-distinct-text opacity-20" />

      <p class="!mt-1 text-sm text-red-500">&nbsp;</p>

      <!-- Loading -->
      <div v-if="isChecking" class="text-center py-8">
        <div class="inline-block animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
        <p class="mt-4 text-light-text dark:text-dark-text">Checking API access...</p>
      </div>

      <!-- Secret input -->
      <div v-else-if="secretRequired" class="flex flex-col sm:flex-row gap-4 items-center">
        <div class="relative flex-grow">
          <Icon
            class="absolute left-3 top-3 text-xl"
            :class="{
              'text-light-text dark:text-dark-text': inputText.length > 0
            }"
            icon="fluent:lock-closed-24-filled"
          />
          <input
            v-model="inputText"
            type="password"
            class="w-full pl-10 pr-4 h-14 rounded-lg border border-light-distinct-text dark:border-dark-distinct-text bg-light-menu dark:bg-dark-menu text-light-text dark:text-dark-text focus:ring-2 focus:ring-blue-500 outline-none text-lg"
            :placeholder="$t('enter-api-secret')"
            autocomplete="off"
            @input="storeSecret"
            @keyup.enter="handleEnter"
          />
        </div>
        <button
          class="px-8 py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-lg"
          @click="handleEnter"
        >
          Start
        </button>
      </div>

      <!-- No secret required -->
      <div v-else class="flex justify-center">
        <button
          class="px-10 py-4 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors text-xl"
          @click="$emit('close')"
        >
          Start
        </button>
      </div>

      <p class="!mt-1 text-sm text-red-500">{{ errorMessage }}&nbsp;</p>

      <!-- Divider -->
      <hr class="border-light-distinct-text dark:border-dark-distinct-text opacity-20" />

      <!-- Newsletter Signup -->
      <section class="mt-8">
        <h2 class="text-2xl font-bold mb-6">Stay Updated</h2>

        <div class="flex flex-col sm:flex-row gap-4 mb-2">
          <input
            v-model="email"
            type="email"
            class="flex-grow px-4 h-12 rounded-lg border border-light-distinct-text dark:border-dark-distinct-text bg-light-menu dark:bg-dark-menu text-light-text dark:text-dark-text focus:ring-2 focus:ring-blue-500 outline-none"
            placeholder="you@example.com"
            :disabled="emailSent"
          />
          <button
            class="px-6 py-2 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="!validEmail || !consentGiven || emailSent"
            @click="subscribe"
          >
            {{ emailSent ? 'Subscribed' : 'Subscribe' }}
          </button>
        </div>

        <!-- Consent Checkbox -->
        <div class="flex items-center gap-2 mb-2">
          <input type="checkbox" id="consent" v-model="consentGiven" :disabled="emailSent" class="accent-blue-600" />
          <label for="consent" class="text-sm text-light-text dark:text-dark-text">
            I agree to receive updates and surveys about the Wikidata Vector Database.
          </label>
        </div>

        <p class="!mt-1 text-sm" :class="emailSuccess ? 'text-green-500' : 'text-red-500'">
          {{ emailMessage }}&nbsp;
        </p>
      </section>

      <!-- Feedback / User Survey -->
      <section class="mt-8">
        <h2 class="text-2xl font-bold mb-4">Help Us Improve</h2>
        <p class="text-light-text dark:text-dark-text mb-4">
          Share your thoughts and projects if you’re using the Wikidata vector database!
        </p>

        <a href="https://wikimedia.sslsurvey.de/Wikidata-Vector-DB-Feedback-Alpha-release" target="_blank" class="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">
          Take the Survey
        </a>

      <p class="!mt-1 text-sm text-red-500">&nbsp;</p>
      </section>

      <!-- Partners Section -->
      <section>
        <h2 class="text-2xl font-bold mb-6">Partners</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <!-- Jina AI -->
          <a
            href="https://jina.ai/"
            target="_blank"
            class="bg-white dark:bg-dark-menu px-20 py-4 rounded-xl shadow-md hover:shadow-lg transition-shadow flex items-center justify-center"
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
            class="bg-white dark:bg-dark-menu px-20 py-4 rounded-xl shadow-md hover:shadow-lg transition-shadow flex items-center justify-center"
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

      <p class="!mt-1 text-sm text-red-500">&nbsp;</p>
      </section>

      <!-- Contributors -->
      <section>
        <h2 class="text-2xl font-bold mb-6">Contributors</h2>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <!-- Philippe -->
          <div class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow">
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
              >Philippe Saadé</a>
              <p class="text-sm text-light-text dark:text-dark-text">AI/ML Project Manager, WMDE</p>
            </div>
          </div>

          <!-- Robert -->
          <div class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow">
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
              >Robert Timm</a>
              <p class="text-sm text-light-text dark:text-dark-text">Senior Software Engineer, Wikibase Suite, WMDE</p>
            </div>
          </div>

          <!-- Jonathan -->
          <div class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow">
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
              >Jonathan Fraine</a>
              <p class="text-sm text-light-text dark:text-dark-text">Co-Head of Software Development, CTO, WMDE</p>
            </div>
          </div>

          <!-- Andrew -->
          <div class="flex items-start p-4 rounded-xl shadow-md bg-light-menu dark:bg-dark-menu hover:shadow-lg transition-shadow">
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
              >Andrew Tavis McAllister</a>
              <p class="text-sm text-light-text dark:text-dark-text">Data Analyst, WMDE</p>
            </div>
          </div>
        </div>

      <p class="!mt-1 text-sm text-red-500">&nbsp;</p>
      </section>

      <!-- Resources -->
      <section>
        <h2 class="text-2xl font-bold mb-6">Resources</h2>
        <div class="flex flex-wrap gap-4">
          <a href="/docs" target="_blank" class="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">
            API Documentation
          </a>
          <a href="https://www.wikidata.org/wiki/Wikidata:Embedding_Project" target="_blank"
             class="px-6 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition">
            Wikidata Embedding Project
          </a>
        </div>

      <p class="!mt-1 text-sm text-red-500">&nbsp;</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { ref, defineEmits, onMounted, computed } from 'vue'

const emit = defineEmits(['close'])
const inputText = ref(apiSecret() || '')
const errorMessage = ref('')
const isChecking = ref(false)
const secretRequired = ref(true)

const canClose = computed(() => !isChecking.value && (!secretRequired.value || apiSecret()))

onMounted(async () => { await checkApiAccess() })

function storeSecret() { sessionStorage.setItem('api-secret', inputText.value) }
function apiSecret() { const secret = sessionStorage.getItem('api-secret'); return secret?.length ? secret : null }

async function checkApiAccess() {
  isChecking.value = true
  errorMessage.value = ''
  try {
    const response = await fetch(`/item/query/?query=`)
    secretRequired.value = response.status === 401
  } catch {
    secretRequired.value = true
  } finally {
    isChecking.value = false
  }
}

async function validateSecret() {
  errorMessage.value = ''
  try {
    const response = await fetch(`/item/query/?query=`, { headers: { 'x-api-secret': inputText.value } })
    if (response.status === 401) errorMessage.value = 'Invalid API secret. Please try again.'
    else storeSecret()
  } catch { errorMessage.value = 'Network error. Please try again later.' }
}

async function handleEnter() { await validateSecret(); if (!errorMessage.value) emit('close') }

const email = ref('')
const emailMessage = ref('')
const emailSuccess = ref(false)
const emailSent = ref(false)
const consentGiven = ref(false)

const validEmail = computed(() => /\S+@\S+\.\S+/.test(email.value))

async function subscribe() {
  emailMessage.value = ''
  emailSuccess.value = false
  try {
    const response = await fetch('/subscribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value })
    })

    if (response.ok) {
      emailMessage.value = '✅ You are now subscribed!'
      emailSuccess.value = true
      emailSent.value = true
      email.value = ''
    } else {
      emailMessage.value = '❌ Subscription failed. Please try again later.'
    }
  } catch {
    emailMessage.value = '❌ Network error. Please try again.'
  }
}
</script>
