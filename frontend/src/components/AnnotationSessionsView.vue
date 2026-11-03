<template>
  <div class="q-pa-md">
    <div v-if="loading" class="row justify-center q-my-lg"><q-spinner-dots size="40px" color="primary" /></div>
    <div v-else-if="sessions.length === 0" class="text-grey-6 q-my-lg text-center">
      No annotation sessions recorded for this text.
    </div>

    <q-list v-else bordered separator class="rounded-borders">
      <q-expansion-item
        v-for="s in sessions" :key="s.session_id"
        expand-separator
        :default-opened="sessions.length === 1"
      >
        <template #header>
          <q-item-section avatar>
            <q-icon :name="s.voice_comment ? 'mic' : 'mic_off'" :color="s.voice_comment ? 'primary' : 'grey-5'" />
          </q-item-section>
          <q-item-section>
            <q-item-label>{{ s.display_name }}</q-item-label>
            <q-item-label caption>
              {{ new Date(s.submitted_at).toLocaleString() }} ·
              {{ fmtMs(sessionDuration(s)) }} ·
              {{ s.annotations.map((a) => `${taskName(a.task_id)}: ${a.selected_classes.map((c) => classLabel(a.task_id, c)).join(', ')}`).join(' | ') }}
            </q-item-label>
          </q-item-section>
          <q-item-section v-if="s.voice_comment" side>
            <q-badge :color="statusColor(s.voice_comment.transcription_status)" :label="s.voice_comment.transcription_status" />
          </q-item-section>
        </template>

        <q-card flat>
          <q-card-section v-if="s.voice_comment" class="q-pb-none">
            <div class="row items-center q-gutter-sm q-mb-sm">
              <audio
                v-if="audioUrls[s.voice_comment.id]"
                :ref="(el) => setAudioEl(s.voice_comment!.id, el)"
                :src="audioUrls[s.voice_comment.id]"
                controls preload="metadata" style="width: 100%; max-width: 520px"
              />
              <q-btn
                v-else dense outline color="primary" icon="play_arrow" label="Load audio"
                :loading="loadingAudio[s.voice_comment.id]"
                @click="loadAudio(s.voice_comment.id)"
              />
              <span class="text-caption text-grey-7">
                {{ LANGUAGE_NAMES[s.voice_comment.language] ?? s.voice_comment.language }} ·
                {{ fmtMs(s.voice_comment.end_ms - s.voice_comment.start_ms) }} ·
                {{ (s.voice_comment.size_bytes / 1024).toFixed(0) }} kB
                <template v-if="s.voice_comment.transcription_model"> · {{ s.voice_comment.transcription_model }}</template>
              </span>
              <q-space />
              <q-btn
                v-if="s.voice_comment.transcription_status !== 'pending'"
                flat dense size="sm" icon="refresh" label="Transcribe again"
                @click="retranscribe(s.voice_comment.id)"
              />
            </div>
            <div v-if="s.voice_comment.transcript" class="transcript text-body2 q-pa-sm q-mb-sm">{{ s.voice_comment.transcript }}</div>
            <div v-else-if="s.voice_comment.transcription_status === 'pending'" class="text-caption text-grey-6 q-mb-sm">
              Transcription pending (attempt {{ s.voice_comment.transcription_attempts }}).
            </div>
            <div v-if="s.voice_comment.transcription_error" class="text-caption text-negative q-mb-sm">
              {{ s.voice_comment.transcription_error }}
            </div>
          </q-card-section>

          <q-card-section>
            <div class="text-subtitle2 q-mb-xs">Timeline</div>
            <q-markup-table flat dense separator="horizontal" class="timeline">
              <thead>
                <tr>
                  <th class="text-right" style="width: 80px">Text time</th>
                  <th v-if="s.voice_comment" class="text-right" style="width: 90px">Audio</th>
                  <th class="text-left" style="width: 170px">Event</th>
                  <th class="text-left">Detail</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, i) in timeline(s)" :key="i" :class="row.kind === 'speech' ? 'speech-row' : ''">
                  <td class="text-right text-grey-7">{{ fmtMs(row.t_ms) }}</td>
                  <td v-if="s.voice_comment" class="text-right">
                    <a
                      v-if="row.audio_ms !== null"
                      href="#" class="text-primary"
                      @click.prevent="seek(s.voice_comment!.id, row.audio_ms)"
                    >{{ fmtMs(row.audio_ms) }}</a>
                  </td>
                  <td>{{ row.label }}</td>
                  <td>{{ row.detail }}</td>
                </tr>
              </tbody>
            </q-markup-table>
          </q-card-section>
        </q-card>
      </q-expansion-item>
    </q-list>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue';
import { useQuasar } from 'quasar';
import { apiService } from 'src/services/api';
import { AnnotationSessionEntry, TaskDefinition } from 'src/types/api';

const props = defineProps<{ textId: string; tasks: TaskDefinition[] }>();
const $q = useQuasar();

const LANGUAGE_NAMES: Record<string, string> = { cs: 'Czech', sk: 'Slovak' };

const EVENT_LABELS: Record<string, string> = {
  text_shown: 'Text shown',
  task_shown: 'Task shown',
  class_selected: 'Class selected',
  class_deselected: 'Class deselected',
  description_shown: 'Prompt opened',
  description_hidden: 'Prompt closed',
  recording_started: 'Recording started',
  recording_stopped: 'Recording stopped',
  recording_max_reached: 'Recording max length',
  recording_discarded: 'Recording discarded',
  page_hidden: 'Page hidden',
  page_visible: 'Page visible',
  submitted: 'Submitted',
  submit_failed: 'Submit failed',
};

interface TimelineRow {
  kind: 'event' | 'speech';
  t_ms: number;
  audio_ms: number | null;
  label: string;
  detail: string;
}

const sessions = ref<AnnotationSessionEntry[]>([]);
const loading = ref(false);
const audioUrls = ref<Record<string, string>>({});
const loadingAudio = ref<Record<string, boolean>>({});
const audioEls: Record<string, HTMLAudioElement> = {};

const taskName = (taskId: string) => props.tasks.find((t) => t.id === taskId)?.name ?? taskId;
const classLabel = (taskId: string, classId: string) =>
  props.tasks.find((t) => t.id === taskId)?.classes.find((c) => c.id === classId)?.label_cs ?? classId;

const fmtMs = (ms: number) => {
  const total = Math.max(0, ms) / 1000;
  const m = Math.floor(total / 60);
  const s = (total - m * 60).toFixed(1).padStart(4, '0');
  return `${m}:${s}`;
};

const statusColor = (status: string) => (status === 'done' ? 'positive' : status === 'failed' ? 'negative' : 'grey-7');

const sessionDuration = (s: AnnotationSessionEntry) => s.events.reduce((m, e) => Math.max(m, e.t_ms), 0);

/** Events and transcript segments on one clock (ms since text shown). */
const timeline = (s: AnnotationSessionEntry): TimelineRow[] => {
  const vc = s.voice_comment;
  const toAudio = (t: number) => (vc && t >= vc.start_ms && t <= vc.end_ms ? t - vc.start_ms : null);
  const rows: TimelineRow[] = s.events.map((e) => ({
    kind: 'event',
    t_ms: e.t_ms,
    audio_ms: toAudio(e.t_ms),
    label: EVENT_LABELS[e.type] ?? e.type,
    detail: [
      e.task_id ? taskName(e.task_id) : '',
      e.task_id && e.class_id ? classLabel(e.task_id, e.class_id) : (e.class_id ?? ''),
    ].filter(Boolean).join(' → '),
  }));
  for (const seg of vc?.transcript_segments ?? []) {
    const audioMs = Math.round(seg.start * 1000);
    rows.push({ kind: 'speech', t_ms: (vc?.start_ms ?? 0) + audioMs, audio_ms: audioMs, label: 'Speech', detail: seg.text.trim() });
  }
  return rows.sort((a, b) => a.t_ms - b.t_ms);
};

const load = async () => {
  loading.value = true;
  try {
    sessions.value = await apiService.getTextSessions(props.textId);
  } finally {
    loading.value = false;
  }
};

const loadAudio = async (vcId: string) => {
  loadingAudio.value[vcId] = true;
  try {
    const blob = await apiService.getVoiceCommentAudio(vcId);
    audioUrls.value[vcId] = URL.createObjectURL(blob);
  } catch {
    $q.notify({ type: 'negative', message: 'Could not load audio.' });
  } finally {
    loadingAudio.value[vcId] = false;
  }
};

const setAudioEl = (vcId: string, el: unknown) => {
  if (el instanceof HTMLAudioElement) audioEls[vcId] = el;
};

const seek = async (vcId: string, audioMs: number) => {
  if (!audioUrls.value[vcId]) await loadAudio(vcId);
  // Wait one tick for the <audio> element to mount after loading.
  setTimeout(() => {
    const el = audioEls[vcId];
    if (!el) return;
    el.currentTime = audioMs / 1000;
    void el.play();
  }, 0);
};

const retranscribe = async (vcId: string) => {
  await apiService.retranscribeVoiceComment(vcId);
  $q.notify({ type: 'info', message: 'Queued for transcription.' });
  await load();
};

const revokeAudio = () => {
  Object.values(audioUrls.value).forEach((u) => URL.revokeObjectURL(u));
  audioUrls.value = {};
};

watch(() => props.textId, () => { revokeAudio(); void load(); }, { immediate: true });
onBeforeUnmount(revokeAudio);
</script>

<style scoped>
.transcript {
  white-space: pre-wrap;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
}
.speech-row td {
  font-style: italic;
  color: #1565c0;
}
</style>
