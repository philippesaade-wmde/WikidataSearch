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
          <a :href="'https://www.wikidata.org/wiki/' + r.QID" class="flex items-center gap-6">
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

            <!-- Image (Larger) -->
            <div v-if="r.image" class="flex-shrink-0">
              <img class="rounded-2xl max-h-32 shadow-md border border-light-border dark:border-dark-border" 
                   :src="r.image" :alt="r.label" />
            </div>
          </a>
        </div>
      </template>

      <!-- No Response Message -->
      <template v-else>
        <div class="text-lg text-light-muted dark:text-dark-muted">
          {{ $t('no-response-message') }}
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Icon } from '@iconify/vue'
import type { ResponseObject } from '../../types/response-object.d.ts'

defineProps<{
  response?: ResponseObject[]
  isLoading: boolean
}>()
</script>
