<template>
  <q-page class="q-pa-md">
    <div v-if="loading" class="flex flex-center" style="min-height: 400px">
      <q-spinner color="primary" size="3em" />
    </div>

    <div v-else-if="ratingRequest">
      <!-- Chunk Text Display -->
      <q-card class="q-mb-md">
        <q-card-section>
          <div class="text-h6 q-mb-md">Text to Rate:</div>
          <div class="text-body1">{{ ratingRequest.chunk.text }}</div>
        </q-card-section>
        <q-card-section>
          <div class="text-caption">
            Pages: {{ ratingRequest.chunk.from_page }} -
            {{ ratingRequest.chunk.to_page }} | Language:
            {{ ratingRequest.chunk.language }}
          </div>
        </q-card-section>
      </q-card>

      <!-- Progress -->
      <q-linear-progress
        :value="progress"
        color="primary"
        class="q-mb-md"
        size="20px"
      >
        <div class="absolute-full flex flex-center">
          <q-badge
            color="white"
            text-color="primary"
            :label="`${currentPairIndex + 1} / ${totalPairs}`"
          />
        </div>
      </q-linear-progress>

      <!-- Current Title Pair Rating -->
      <q-card v-if="currentPair">
        <q-card-section>
          <div class="text-h6 q-mb-md">
            Query: {{ currentPair[0].query }}
          </div>

          <!-- Title 1 -->
          <div class="q-mb-lg">
            <q-card
              flat
              bordered
              :class="{
                'bg-blue-1': currentRating.titles[0].preferred,
              }"
            >
              <q-card-section>
                <div class="row items-center q-mb-md">
                  <q-checkbox
                    v-model="currentRating.titles[0].preferred"
                    @update:model-value="onTitleSelect(0)"
                    class="q-mr-md"
                  />
                  <div class="text-body1 col">
                    {{ currentPair[0].generated_title }}
                  </div>
                </div>

                <div class="q-gutter-sm">
                  <q-checkbox
                    v-model="currentRating.titles[0].is_irrelevant"
                    label="Irrelevant"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[0].is_gibberish"
                    label="Nonsense"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[0].is_relevant"
                    label="Relevant"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[0].is_hallucination"
                    label="Hallucination"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[0].is_long"
                    label="Long"
                    color="primary"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- Title 2 -->
          <div class="q-mb-lg">
            <q-card
              flat
              bordered
              :class="{
                'bg-blue-1': currentRating.titles[1].preferred,
              }"
            >
              <q-card-section>
                <div class="row items-center q-mb-md">
                  <q-checkbox
                    v-model="currentRating.titles[1].preferred"
                    @update:model-value="onTitleSelect(1)"
                    class="q-mr-md"
                  />
                  <div class="text-body1 col">
                    {{ currentPair[1].generated_title }}
                  </div>
                </div>

                <div class="q-gutter-sm">
                  <q-checkbox
                    v-model="currentRating.titles[1].is_irrelevant"
                    label="Irrelevant"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[1].is_gibberish"
                    label="Nonsense"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[1].is_relevant"
                    label="Relevant"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[1].is_hallucination"
                    label="Hallucination"
                    color="primary"
                  />
                  <q-checkbox
                    v-model="currentRating.titles[1].is_long"
                    label="Long"
                    color="primary"
                  />
                </div>
              </q-card-section>
            </q-card>
          </div>

          <!-- Done Button -->
          <div class="flex justify-center">
            <q-btn
              label="DONE"
              color="primary"
              size="lg"
              :disable="!isCurrentRatingValid"
              @click="onDone"
            />
          </div>
        </q-card-section>
      </q-card>

      <!-- Completion Message -->
      <q-card v-else-if="allPairsCompleted">
        <q-card-section class="text-center">
          <div class="text-h5 q-mb-md">All ratings completed!</div>
          <div class="text-body1 q-mb-md">
            Submitting your ratings...
          </div>
          <q-spinner color="primary" size="2em" />
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useQuasar } from 'quasar';
import { apiService } from 'src/services/api';
import {
  RatingRequest,
  TitleImport,
  RatedTitle,
  SingleRating,
  RatingResponseNew,
} from 'src/types/api';
import { v4 as uuidv4 } from 'uuid';

const $q = useQuasar();

const loading = ref(true);
const ratingRequest = ref<RatingRequest | null>(null);
const currentPairIndex = ref(0);
const completedRatings = ref<SingleRating[]>([]);
const currentRating = ref<{
  titles: Array<RatedTitle>;
  start_time: Date;
}>({
  titles: [],
  start_time: new Date(),
});

const currentPair = computed(() => {
  if (!ratingRequest.value) return null;
  if (currentPairIndex.value >= ratingRequest.value.titles_lists.length) {
    return null;
  }
  return ratingRequest.value.titles_lists[currentPairIndex.value];
});

const totalPairs = computed(() => {
  return ratingRequest.value?.titles_lists.length || 0;
});

const progress = computed(() => {
  if (totalPairs.value === 0) return 0;
  return currentPairIndex.value / totalPairs.value;
});

const allPairsCompleted = computed(() => {
  return currentPairIndex.value >= totalPairs.value;
});

const isCurrentRatingValid = computed(() => {
  if (currentRating.value.titles.length !== 2) return false;

  // Check if exactly one title is selected
  const selectedCount = currentRating.value.titles.filter(
    (t) => t.preferred
  ).length;
  return selectedCount === 1;
});

const initializeCurrentRating = (pair: TitleImport[]) => {
  currentRating.value = {
    titles: pair.map((title) => ({
      ...title,
      preferred: false,
      is_irrelevant: false,
      is_gibberish: false,
      is_relevant: false,
      is_hallucination: false,
      is_long: false,
    })),
    start_time: new Date(),
  };
};

const onTitleSelect = (index: number) => {
  // Ensure only one title is selected
  currentRating.value.titles.forEach((title, i) => {
    if (i !== index) {
      title.preferred = false;
    }
  });
};

const onDone = () => {
  if (!isCurrentRatingValid.value) return;

  const endTime = new Date();

  // Create rating record
  const rating: SingleRating = {
    titles: currentRating.value.titles,
    start_time: currentRating.value.start_time.toISOString(),
    end_time: endTime.toISOString(),
  };

  completedRatings.value.push(rating);

  // Move to next pair
  currentPairIndex.value++;

  if (allPairsCompleted.value) {
    submitAllRatings();
  } else if (currentPair.value) {
    initializeCurrentRating(currentPair.value);
  }
};

const submitAllRatings = async () => {
  if (!ratingRequest.value) return;

  try {
    const response: RatingResponseNew = {
      id: uuidv4(),
      request_id: ratingRequest.value.id,
      start_time: completedRatings.value[0].start_time,
      end_time:
        completedRatings.value[completedRatings.value.length - 1].end_time,
      ratings: completedRatings.value,
    };

    await apiService.submitRatingResponse(response);

    $q.notify({
      type: 'positive',
      message: 'Ratings submitted successfully!',
    });

    // Load next rating request
    await loadRatingRequest();
  } catch (error) {
    const err = error as { response?: { data?: { detail?: string } } };
    $q.notify({
      type: 'negative',
      message: err.response?.data?.detail || 'Failed to submit ratings',
    });
  }
};

const loadRatingRequest = async () => {
  loading.value = true;
  try {
    ratingRequest.value = await apiService.getRatingRequest();
    currentPairIndex.value = 0;
    completedRatings.value = [];

    if (currentPair.value) {
      initializeCurrentRating(currentPair.value);
    }
  } catch (error) {
    const err = error as { response?: { data?: { detail?: string } } };
    $q.notify({
      type: 'negative',
      message:
        err.response?.data?.detail || 'Failed to load rating request',
    });
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadRatingRequest();
});
</script>

<style scoped>
.bg-blue-1 {
  background-color: #e3f2fd;
}
</style>
