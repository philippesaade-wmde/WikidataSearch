<template>
  <div v-if="imageUrl" class="flex-shrink-0">
    <img class="rounded-2xl max-h-32 shadow-md border border-light-border dark:border-dark-border" :src="imageUrl" :alt="altText" />
  </div>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue';

const props = defineProps({
  qid: {
    type: String
  }
});

const imageUrl = ref('');
const altText = ref('Wikidata image');

watchEffect(async () => {
  if (!props.qid) return;
  try {
    const response = await fetch(`https://www.wikidata.org/w/api.php?action=wbgetclaims&format=json&origin=*&entity=${props.qid}&property=P18`);
    const data = await response.json();
    if (data.claims?.P18?.[0]?.mainsnak?.datavalue?.value) {
      const fileName = data.claims.P18[0].mainsnak.datavalue.value;
      imageUrl.value = `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(fileName)}`;
      altText.value = fileName;
    }
  } catch (error) {
    console.error('Failed to fetch image:', error);
  }
});
</script>