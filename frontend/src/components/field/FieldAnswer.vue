<template>
  <div class="flex space-x-6 text-light-text dark:text-dark-text">
    <div
      class="p-2 text-2xl rounded-full bg-light-menu dark:bg-dark-menu h-min elem-shadow-sm"
      :class="{ 'animate-pulse': isLoading }"
    >
      <Icon icon="ooui:logo-wikimedia" />
    </div>
    <div v-if="isLoading" class="w-full m-auto animate-pulse">
      <div class="w-2/3 h-6 rounded-sm bg-light-distinct-text dark:bg-dark-distinct-text" />
    </div>
    <div v-else>
      <div v-if="response">
        <div v-for="r in response" :key="r.QID">
          <a :href="'https://www.wikidata.org/wiki/' + r.QID" class="flex p-2">
            <div class="flex-1">
              <div class="text-2xl">
                {{ r.label }} ({{ r.QID }})
              </div>
              <div class="text-lg">
                {{ r.description }}
              </div>
              <div class="text-lg">
                {{ r.similarity_score }}
              </div>
            </div>
            <div class="text-lg px-2">
              <img class="rounded-2xl" :src="r.image" />
            </div>
          </a>
        </div>
      </div>
      <div v-else class="text-lg">
        {{ $t('no-response-message') }}
      </div>
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