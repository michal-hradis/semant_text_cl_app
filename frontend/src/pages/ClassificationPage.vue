<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Classification</div>
    <div class="q-mb-md">My total annotations: {{ myTotal }}</div>
    <div v-if="!textItem">No more texts.</div>
    <div v-else>
      <q-card class="q-mb-md"><q-card-section>{{ textItem.text }}</q-card-section></q-card>
      <div v-for="task in tasks" :key="task.id" class="q-mb-md">
        <div class="text-subtitle1">{{ task.name }}</div>
        <div class="text-caption text-grey-7 q-mb-xs">
          {{ task.multi_choice ? `Choose 1 to ${task.max_choices} options.` : 'Choose exactly 1 option.' }}
        </div>
        <q-option-group
          v-model="answers[task.id]"
          :type="task.multi_choice ? 'checkbox' : 'radio'"
          :options="task.classes.map((c) => ({ label: c.label_en, value: c.id }))"
          @update:model-value="limitMultiChoice(task)"
        />
      </div>
      <q-banner v-if="validationMessage" class="bg-orange-1 text-orange-10 q-mb-md">{{ validationMessage }}</q-banner>
      <q-btn color="primary" label="Submit" :disable="Boolean(validationMessage)" @click="submit" />
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { apiService } from 'src/services/api';
import { NextTextResponse, TaskDefinition } from 'src/types/api';

const tasks = ref<TaskDefinition[]>([]);
const textItem = ref<NextTextResponse | null>(null);
const answers = ref<Record<string, string[] | string>>({});
const myTotal = ref(0);

const selectedClasses = (task: TaskDefinition): string[] => {
  const value = answers.value[task.id];
  if (Array.isArray(value)) return value;
  return value ? [value] : [];
};

const validationMessage = computed(() => {
  if (!textItem.value) return '';
  for (const task of tasks.value) {
    const selected = selectedClasses(task);
    if (selected.length === 0) return `Please answer ${task.name}.`;
    if (!task.multi_choice && selected.length !== 1) return `${task.name} requires exactly one option.`;
    if (task.multi_choice && selected.length > task.max_choices) return `${task.name} allows at most ${task.max_choices} options.`;
  }
  return '';
});

const load = async () => {
  const ids = JSON.parse(localStorage.getItem('selected_tasks') || '[]') as string[];
  const all = await apiService.getTasks();
  tasks.value = all.filter((t) => ids.includes(t.id));
  textItem.value = await apiService.getNextText(ids);
  answers.value = {};
  for (const task of tasks.value) {
    answers.value[task.id] = task.multi_choice ? [] : '';
  }
  const stats = await apiService.getMyStats();
  myTotal.value = stats.total;
};

onMounted(load);

const limitMultiChoice = (task: TaskDefinition) => {
  if (!task.multi_choice) return;
  const selected = selectedClasses(task);
  if (selected.length > task.max_choices) {
    answers.value[task.id] = selected.slice(0, task.max_choices);
  }
};

const submit = async () => {
  if (!textItem.value || validationMessage.value) return;
  const now = new Date().toISOString();
  await apiService.submitAnnotations({
    text_id: textItem.value.id,
    annotations: tasks.value.map((t) => ({
      task_id: t.id,
      selected_classes: selectedClasses(t),
      start_time: now,
      end_time: now,
    })),
  });
  await load();
};
</script>
