<template>
  <q-page class="q-pa-md">
    <div class="text-h5 q-mb-md">Admin</div>

    <q-card class="q-mb-lg">
      <q-card-section>
        <div class="text-h6">Task definitions</div>
        <div class="text-body2 text-grey-7">
          Import prompt markdown, then edit the task name, prompt, enabled state, and available choices.
          Multi-choice tasks allow annotators to select up to the configured maximum number of classes.
        </div>
      </q-card-section>
      <q-card-actions>
        <q-btn color="primary" label="Import prompts/*.md as tasks" @click="importPrompts" />
        <q-btn flat color="primary" label="Reload tasks" @click="loadTasks" />
      </q-card-actions>
    </q-card>

    <q-card v-for="task in tasks" :key="task.id" class="q-mb-md">
      <q-card-section>
        <div class="row q-col-gutter-md">
          <div class="col-12 col-md-3">
            <q-input v-model="task.id" label="Task ID" readonly />
          </div>
          <div class="col-12 col-md-5">
            <q-input v-model="task.name" label="Task name" />
          </div>
          <div class="col-12 col-md-2">
            <q-toggle v-model="task.enabled" label="Enabled" />
          </div>
          <div class="col-12 col-md-2">
            <q-toggle v-model="task.multi_choice" label="Multi-choice" @update:model-value="normalizeMaxChoices(task)" />
          </div>
        </div>

        <div class="row q-col-gutter-md q-mt-sm">
          <div class="col-12 col-md-3">
            <q-input
              v-model.number="task.max_choices"
              type="number"
              label="Max choices"
              :min="1"
              :max="task.classes.length"
              :disable="!task.multi_choice"
              @update:model-value="normalizeMaxChoices(task)"
            />
          </div>
        </div>

        <q-input v-model="task.description_md" type="textarea" label="Prompt markdown" autogrow class="q-mt-md" />

        <div class="text-subtitle2 q-mt-md">Choices</div>
        <div v-for="(choice, index) in task.classes" :key="`${task.id}-${index}`" class="row q-col-gutter-sm q-mb-sm items-center">
          <div class="col-12 col-md-3">
            <q-input v-model="choice.id" label="Class ID" dense />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model="choice.label_en" label="English label" dense />
          </div>
          <div class="col-12 col-md-3">
            <q-input v-model="choice.label_cs" label="Czech label" dense />
          </div>
          <div class="col-12 col-md-3">
            <q-btn flat color="negative" icon="delete" label="Remove" :disable="task.classes.length === 1" @click="removeChoice(task, index)" />
          </div>
        </div>
        <q-btn flat color="primary" icon="add" label="Add choice" @click="addChoice(task)" />
      </q-card-section>
      <q-card-actions align="right">
        <q-btn color="primary" label="Save task" @click="saveTask(task)" />
      </q-card-actions>
    </q-card>

    <q-card class="q-mt-lg">
      <q-card-section>
        <div class="text-h6">Upload texts</div>
        <q-input v-model="jsonl" type="textarea" label="Paste JSONL texts" autogrow class="q-mt-md" />
      </q-card-section>
      <q-card-actions>
        <q-btn color="secondary" label="Upload texts" @click="uploadTexts" />
      </q-card-actions>
    </q-card>

    <div class="q-mt-md">{{ msg }}</div>
  </q-page>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { TaskDefinition } from 'src/types/api';
import { apiService } from 'src/services/api';

const jsonl = ref('');
const msg = ref('');
const tasks = ref<TaskDefinition[]>([]);

const cloneTask = (task: TaskDefinition): TaskDefinition => JSON.parse(JSON.stringify(task)) as TaskDefinition;

const loadTasks = async () => {
  tasks.value = (await apiService.getAdminTasks()).map(cloneTask);
};

const normalizeMaxChoices = (task: TaskDefinition) => {
  if (!task.multi_choice) {
    task.max_choices = 1;
    return;
  }
  const maxAllowed = Math.max(task.classes.length, 1);
  task.max_choices = Math.min(Math.max(Number(task.max_choices) || 1, 1), maxAllowed);
};

const addChoice = (task: TaskDefinition) => {
  task.classes.push({ id: 'new_class', label_en: 'New class', label_cs: 'nová třída' });
  normalizeMaxChoices(task);
};

const removeChoice = (task: TaskDefinition, index: number) => {
  task.classes.splice(index, 1);
  normalizeMaxChoices(task);
};

const validateTask = (task: TaskDefinition): string | null => {
  if (!task.name.trim()) return 'Task name is required.';
  if (!task.description_md.trim()) return 'Prompt markdown is required.';
  if (task.classes.length === 0) return 'At least one choice is required.';
  const ids = task.classes.map((choice) => choice.id.trim());
  if (ids.some((id) => !id)) return 'Every choice must have a class ID.';
  if (new Set(ids).size !== ids.length) return 'Choice class IDs must be unique.';
  return null;
};

const saveTask = async (task: TaskDefinition) => {
  normalizeMaxChoices(task);
  const error = validateTask(task);
  if (error) {
    msg.value = error;
    return;
  }
  await apiService.saveAdminTask(task);
  msg.value = `Saved task ${task.id}`;
  await loadTasks();
};

const importPrompts = async () => {
  const result = await apiService.importPromptTasks();
  msg.value = `Imported ${result.imported} tasks`;
  await loadTasks();
};

const uploadTexts = async () => {
  await apiService.uploadTextsJsonl(jsonl.value);
  msg.value = 'Texts uploaded';
};

onMounted(loadTasks);
</script>
