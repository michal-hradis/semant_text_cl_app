import { computed, onBeforeUnmount, ref, watch } from 'vue';

/**
 * One voice comment recording per annotation session (see docs/voice_comments.md).
 *
 * - `enabled` is the annotator's on/off choice; it persists across texts and reloads.
 * - Turning recording off discards the current recording; it is not restarted for
 *   the same text (no re-recording), only from the next text on.
 * - Recording stops automatically after `maxSeconds`; the audio so far is kept.
 * - Times are in ms on the session clock supplied by `now()`.
 */

export interface FinishedRecording {
  blob: Blob;
  startMs: number;
  endMs: number;
}

interface Options {
  now: () => number;
  onEvent: (type: string) => void;
}

const LS_ENABLED = 'voice_recording_enabled';
const LS_LANGUAGE = 'voice_language';
const LS_CONSENT = 'voice_consent_v1';

const readLs = (key: string): string | null => {
  try { return localStorage.getItem(key); } catch { return null; }
};
const writeLs = (key: string, value: string) => {
  try { localStorage.setItem(key, value); } catch { /* ignore */ }
};

const pickMimeType = (): string => {
  const candidates = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'];
  return candidates.find((t) => MediaRecorder.isTypeSupported(t)) ?? '';
};

export function useVoiceRecorder({ now, onEvent }: Options) {
  const supported = typeof window !== 'undefined'
    && typeof window.MediaRecorder !== 'undefined'
    && !!navigator.mediaDevices?.getUserMedia;

  const serverEnabled = ref(false);
  const maxSeconds = ref(300);
  const languages = ref<string[]>(['cs', 'sk']);

  const consented = ref(readLs(LS_CONSENT) === '1');
  const enabled = ref(consented.value && readLs(LS_ENABLED) === '1');
  const language = ref(readLs(LS_LANGUAGE) ?? 'cs');
  const recording = ref(false);
  const capReached = ref(false);
  const elapsedMs = ref(0);

  watch(enabled, (v) => writeLs(LS_ENABLED, v ? '1' : '0'));
  watch(language, (v) => writeLs(LS_LANGUAGE, v));

  const available = computed(() => supported && serverEnabled.value);

  let stream: MediaStream | null = null;
  let recorder: MediaRecorder | null = null;
  let chunks: Blob[] = [];
  let startMs = 0;
  let endMs = 0;
  let stopped: Promise<void> | null = null;
  let capTimer: ReturnType<typeof setTimeout> | null = null;
  let ticker: ReturnType<typeof setInterval> | null = null;
  // Set when this text's recording was discarded; blocks re-recording the same text.
  let discardedThisText = false;
  // Bumped on every new text / discard so a late getUserMedia result is ignored.
  let generation = 0;

  const configure = (cfg: { enabled: boolean; max_seconds: number; languages: string[] }) => {
    serverEnabled.value = cfg.enabled;
    maxSeconds.value = cfg.max_seconds;
    languages.value = cfg.languages;
    if (!languages.value.includes(language.value)) language.value = languages.value[0] ?? 'cs';
  };

  const clearTimers = () => {
    if (capTimer) { clearTimeout(capTimer); capTimer = null; }
    if (ticker) { clearInterval(ticker); ticker = null; }
  };

  const releaseStream = () => {
    stream?.getTracks().forEach((t) => t.stop());
    stream = null;
  };

  /** Stop capturing (keeps the data). Resolves when the recorder has flushed. */
  const stopCapture = (eventType: string): Promise<void> => {
    if (recorder && recorder.state !== 'inactive') {
      endMs = now();
      recorder.stop();
      onEvent(eventType);
    }
    recording.value = false;
    clearTimers();
    return stopped ?? Promise.resolve();
  };

  /** Start recording for the current text, if enabled and not yet recorded/discarded. */
  const start = async (): Promise<void> => {
    if (!available.value || !enabled.value || !consented.value) return;
    if (recorder || discardedThisText) return;
    const gen = generation;
    if (!stream) {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
    if (gen !== generation || !enabled.value || recorder) return;

    const mimeType = pickMimeType();
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorder = rec;
    chunks = [];
    capReached.value = false;
    elapsedMs.value = 0;
    stopped = new Promise<void>((resolve) => { rec.onstop = () => resolve(); });
    rec.ondataavailable = (e) => { if (e.data.size > 0 && recorder === rec) chunks.push(e.data); };
    rec.onstart = () => {
      if (recorder !== rec) return;
      startMs = now();
      recording.value = true;
      onEvent('recording_started');
      ticker = setInterval(() => { elapsedMs.value = now() - startMs; }, 250);
      capTimer = setTimeout(() => {
        capReached.value = true;
        void stopCapture('recording_max_reached');
      }, maxSeconds.value * 1000);
    };
    rec.start(1000);
  };

  /** Stop and return this text's recording (null if none). Call at submit. */
  const finish = async (): Promise<FinishedRecording | null> => {
    const rec = recorder;
    if (!rec) return null;
    await stopCapture('recording_stopped');
    recorder = null;
    stopped = null;
    const type = rec.mimeType || chunks[0]?.type || 'audio/webm';
    const blob = new Blob(chunks, { type });
    chunks = [];
    if (blob.size === 0) return null;
    return { blob, startMs, endMs };
  };

  /** Drop the current recording without keeping any data. */
  const discard = (eventType: string | null) => {
    generation += 1;
    const rec = recorder;
    recorder = null;
    stopped = null;
    chunks = [];
    clearTimers();
    recording.value = false;
    if (rec && rec.state !== 'inactive') {
      rec.ondataavailable = null;
      rec.stop();
    }
    if (rec && eventType) onEvent(eventType);
    return !!rec;
  };

  /** A new text is shown: forget the previous (unsubmitted) recording and allow a new one. */
  const resetForNewText = () => {
    discard(null);
    discardedThisText = false;
    capReached.value = false;
    elapsedMs.value = 0;
  };

  const giveConsent = () => {
    consented.value = true;
    writeLs(LS_CONSENT, '1');
  };

  /** Turn recording on (starts now unless this text's recording was discarded) or off (discards). */
  const setEnabled = async (value: boolean): Promise<void> => {
    if (!value) {
      if (discard('recording_discarded')) discardedThisText = true;
      enabled.value = false;
      releaseStream();
      return;
    }
    enabled.value = true;
    try {
      await start();
    } catch (err) {
      enabled.value = false;
      releaseStream();
      throw err;
    }
  };

  onBeforeUnmount(() => {
    discard(null);
    releaseStream();
  });

  return {
    available, enabled, language, languages, consented, recording, capReached, elapsedMs, maxSeconds,
    configure, start, finish, resetForNewText, setEnabled, giveConsent,
  };
}
