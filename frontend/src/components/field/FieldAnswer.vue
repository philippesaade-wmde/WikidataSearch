<template>
  <div class="flex flex-col space-y-6 text-light-text dark:text-dark-text">
    <template v-if="isLoading">
      <div class="w-full h-6 rounded-sm bg-light-distinct-text dark:bg-dark-distinct-text animate-pulse" />
    </template>

    <template v-else-if="response?.length">
      <div
        v-for="(r, index) in response"
        :key="r.id"
        class="p-4 m-2 rounded-lg bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border
               hover:shadow-lg hover:bg-light-hover dark:hover:bg-dark-hover transition cursor-pointer"
      >
        <a
          :href="'https://www.wikidata.org/wiki/' + (r.id.startsWith('P') ? 'Property:' + r.id : r.id)"
          target="_blank"
          class="flex items-start gap-6"
        >
          <!-- Text Info -->
          <div class="flex-1 space-y-2">
            <div class="text-xl font-semibold">{{ r.label }} ({{ r.id }})</div>
            <div class="text-md text-light-muted dark:text-dark-muted">{{ r.description }}</div>
            <div class="text-md text-light-accent dark:text-dark-accent">Similarity Score: {{ r.similarity_score }}</div>
            <div class="text-md text-light-accent dark:text-dark-accent">Source: {{ r.source }}</div>

            <!-- Feedback Section -->
            </br>
            <div class="flex items-center gap-2 mt-2">
              <template v-if="feedbackStatus[index] === 'thanks'">
                <span class="text-sm text-light-text dark:text-dark-text">
                  ✅ Thanks for your feedback!
                </span>
              </template>
              <template v-else>
                <button
                  @click.prevent="submitFeedback(r.id, 'up', index)"
                  class="flex items-center gap-2 px-3 py-1 bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-200 rounded hover:bg-green-200 dark:hover:bg-green-800 transition"
                >
                  👍 <p class="text-sm">Helpful</p>
                </button>
                <button
                  @click.prevent="submitFeedback(r.id, 'down', index)"
                  class="flex items-center gap-2 px-3 py-1 bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 rounded hover:bg-red-200 dark:hover:bg-red-800 transition"
                >
                  👎 <p class="text-sm">Not Helpful</p>
                </button>
              </template>

              <!-- Info icon + tooltip -->
              <div
                class="relative group ml-1 inline-flex items-center"
                tabindex="0"
                aria-label="Feedback info"
                @click.stop
              >
                <Icon
                  icon="fluent:info-16-regular"
                  class="text-blue-600 dark:text-blue-400 cursor-pointer"
                />
                <div
                  class="absolute left-1/2 -translate-x-1/2 top-full mt-1 w-64 p-2
                        bg-light-menu dark:bg-dark-menu text-xs text-light-text dark:text-dark-text
                        rounded shadow-lg opacity-0 group-hover:opacity-100 group-focus-within:opacity-100
                        transition-opacity z-10 pointer-events-none"
                  role="tooltip"
                >
                  Feedback is anonymous and only used for evaluation purposes.
                </div>
              </div>
            </div>
          </div>

          <!-- Image -->
          <div v-if="r.imageUrl" class="flex-shrink-0 text-lg text-light-muted dark:text-dark-muted">
            <a
              :href="r.imagePageUrl"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="View this image on Wikimedia Commons"
            >
              <img
                class="rounded-2xl max-h-32 shadow-md border border-light-border dark:border-dark-border"
                :src="r.imageUrl"
                :alt="r.label"
              />
            </a>
            <p class="mt-1 text-xs text-center text-light-text dark:text-dark-text">
              <a
                :href="r.imagePageUrl"
                target="_blank"
                rel="noopener noreferrer"
                class="underline"
              >
                From Wikimedia Commons
              </a>
            </p>
          </div>
        </a>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Icon } from '@iconify/vue'
import type { ResponseObject } from '../../types/response-object.d.ts'

const props = defineProps<{
  response?: ResponseObject[]
  isLoading: boolean
}>()

const response = ref<ResponseObject[]>([])
// Tracks feedback status per result
const feedbackStatus = ref<string[]>([])

function chunk<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}

const fetchWikidataInfo = async () => {
  if (!props.response || props.response.length === 0) return

  const qids = props.response.map(r => r.id)
  const batches = chunk(qids, 50)

  try {
    const allEntities: Record<string, any> = {}

    await Promise.all(
      batches.map(async ids => {
        let lang = [props.response?.[0]?.lang?.toLowerCase(), 'mul', 'en']

        const url = `https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&ids=${ids.join(
          '|'
        )}&props=labels|descriptions|claims&languages=${lang.join(',')}&origin=*`

        const res = await fetch(url, {
          headers: { 'User-Agent': 'Wikidata Search (philippe.saade@wikimedia.de)' }
        })
        const data = await res.json()
        Object.assign(allEntities, data.entities || {})
      })
    )

    response.value = props.response.map(r => {
      const entity = allEntities[r.id]
      const imageName = entity?.claims?.P18?.[0]?.mainsnak?.datavalue?.value || null
      const lang = r.lang?.toLowerCase() || 'en'

      const filePathUrl = imageName
      ? `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(imageName)}`
      : undefined

      const imagePageUrl = imageName
        ? `https://commons.wikimedia.org/wiki/File:${encodeURIComponent(imageName.replace(/ /g, '_'))}`
        : undefined

      return {
        ...r,
        label:
          entity?.labels?.[lang]?.value ||
          entity?.labels?.mul?.value ||
          entity?.labels?.en?.value || 'Unknown',
        description:
          entity?.descriptions?.[lang]?.value ||
          entity?.descriptions?.mul?.value ||
          entity?.descriptions?.en?.value ||
          'No description available',
        imageUrl: filePathUrl,
        imagePageUrl: imagePageUrl,
        query: r.query // preserve the query for feedback
      }
    })

    // Initialize feedback status
    feedbackStatus.value = Array(response.value.length).fill('')
  } catch (error) {
    console.error('Error fetching Wikidata info:', error)
  }
}

// Watch for changes
watch(() => props.response, fetchWikidataInfo, { immediate: true })

// Submit feedback for a result
const submitFeedback = async (id: string, sentiment: 'up' | 'down', index: number) => {
  if (!response.value) return
  const query = response.value[index].query ?? ''

  try {
    const res = await fetch(`/feedback?query=${encodeURIComponent(query)}&id=${id}&sentiment=${sentiment}&index=${index}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })

    if (res.status === 200) {
      feedbackStatus.value[index] = 'thanks'
    } else {
      console.error('Feedback submission failed', res.status)
    }
  } catch (e) {
    console.error('Error sending feedback', e)
  }
}
</script>
