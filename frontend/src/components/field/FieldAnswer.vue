<template>
  <div class="flex items-start space-x-6 text-light-text dark:text-dark-text">
    <!-- Icon Section -->
    <div
      class="p-2 text-2xl rounded-full bg-light-menu dark:bg-dark-menu h-min elem-shadow-sm"
      :class="{ 'animate-pulse': isLoading }"
    >
      <Icon icon="ooui:logo-wikimedia" />
    </div>

    <!-- Content Section -->
    <div class="flex-1">
      <template v-if="isLoading">
        <div class="w-2/3 h-6 rounded-sm bg-light-distinct-text dark:bg-dark-distinct-text animate-pulse" />
      </template>

      <template v-else-if="response?.length">
        <div
          v-for="r in response"
          :key="r.QID"
          class="p-4 m-2 rounded-lg bg-light-bg dark:bg-dark-bg border border-light-border dark:border-dark-border
                hover:shadow-lg hover:bg-light-hover dark:hover:bg-dark-hover transition cursor-pointer"
        >
          <a :href="'https://www.wikidata.org/wiki/' + r.QID" target="_blank" class="flex items-center gap-6">
            <!-- Text Info -->
            <div class="flex-1 space-y-2">
              <div class="text-xl font-semibold">
                {{ r.label }} ({{ r.QID }})
              </div>
              <div class="text-md text-light-muted dark:text-dark-muted">
                {{ r.description }}
              </div>
              <div class="text-md text-light-accent dark:text-dark-accent">
                Similarity Score: {{ r.similarity_score }}
              </div>
            </div>

            <div class="text-lg text-light-muted dark:text-dark-muted">
              <div v-if="r.imageUrl" class="flex-shrink-0">
                <img class="rounded-2xl max-h-32 shadow-md border border-light-border dark:border-dark-border" :src="r.imageUrl" :alt="r.label" />
              </div>
            </div>
          </a>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { Icon } from '@iconify/vue'
import type { ResponseObject } from '../../types/response-object.d.ts'

const props = defineProps<{
  response?: ResponseObject[]
  isLoading: boolean
}>()

const response = ref<ResponseObject[]>([])

function chunk<T>(arr: T[], size: number): T[][] {
  const result: T[][] = []
  for (let i = 0; i < arr.length; i += size) {
    result.push(arr.slice(i, i + size))
  }
  return result
}

const fetchWikidataInfo = async () => {
  if (!props.response || props.response.length === 0) return

  const qids = props.response.map(r => r.QID)
  const batches = chunk(qids, 50)

  try {
    const allEntities: Record<string, any> = {}

    await Promise.all(
      batches.map(async ids => {
        const url = `https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&ids=${ids.join(
          '|'
        )}&props=labels|descriptions|claims&languages=en&origin=*`

        const res = await fetch(url, {
          headers: {
            'User-Agent': 'Wikidata Search (philippe.saade@wikimedia.de)'
          }
        })
        const data = await res.json()
        Object.assign(allEntities, data.entities || {})
      })
    )

    response.value = props.response.map(r => {
      const entity = allEntities[r.QID]
      const imageName =
        entity?.claims?.P18?.[0]?.mainsnak?.datavalue?.value || null

      return {
        ...r,
        label: entity?.labels?.en?.value || 'Unknown',
        description: entity?.descriptions?.en?.value || 'No description available',
        imageUrl: imageName
          ? `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(
              imageName
            )}`
          : null
      }
    })
  } catch (error) {
    console.error('Error fetching Wikidata info:', error)
  }
}


// Fetch when response changes
watch(() => props.response, fetchWikidataInfo, { immediate: true })
</script>
