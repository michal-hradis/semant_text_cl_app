import { api } from 'boot/axios';
import {
  AnnotationSessionEntry, AnnotationSubmit, BearerResponse, GlobalStats, LeaderboardEntry, LoginRequest,
  MyStats, NextTextResponse, TaskCoverage, TaskDefinition, TextAnnotationEntry, TextListResponse,
  UserCreate, UserRead, UserReliabilityResponse,
  VoiceCommentConfig, VoiceCommentCreated, VoiceCommentUpload,
} from 'src/types/api';

class ApiService {
  async login(credentials: LoginRequest): Promise<BearerResponse> {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    const response = await api.post<BearerResponse>('/auth/jwt/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  async getCurrentUser(): Promise<UserRead> {
    return (await api.get<UserRead>('/users/me')).data;
  }

  async register(userData: UserCreate): Promise<UserRead> {
    return (await api.post<UserRead>('/auth/register', userData)).data;
  }

  async logout(): Promise<void> {
    await api.post('/auth/jwt/logout').catch(() => undefined);
  }

  async getTasks(): Promise<TaskDefinition[]> {
    return (await api.get<TaskDefinition[]>('/api/tasks')).data;
  }

  async getAdminTasks(): Promise<TaskDefinition[]> {
    return (await api.get<TaskDefinition[]>('/api/admin/tasks')).data;
  }

  async saveAdminTask(task: TaskDefinition): Promise<void> {
    await api.put(`/api/admin/tasks/${task.id}`, task);
  }

  async createAdminTask(task: TaskDefinition): Promise<void> {
    await api.post('/api/admin/tasks', task);
  }

  async patchAdminTask(taskId: string, patch: { enabled?: boolean; deleted?: boolean }): Promise<void> {
    await api.patch(`/api/admin/tasks/${taskId}`, patch);
  }

  async importPromptTasks(): Promise<{ imported: number }> {
    return (await api.post<{ imported: number }>('/api/admin/tasks/import-prompts')).data;
  }

  async uploadTextsJsonl(jsonl: string): Promise<{ imported: number }> {
    return (await api.post<{ imported: number }>('/api/admin/texts', jsonl, { headers: { 'Content-Type': 'text/plain' } })).data;
  }

  async getAdminTexts(page = 0, q = '', pageSize = 50, taskId?: string): Promise<TextListResponse> {
    const params: Record<string, unknown> = { page, q, page_size: pageSize };
    if (taskId) params.task_id = taskId;
    return (await api.get<TextListResponse>('/api/admin/texts', { params })).data;
  }

  async patchAdminText(textId: string, suspended: boolean): Promise<void> {
    await api.patch(`/api/admin/texts/${textId}`, { suspended });
  }

  async getTextAnnotations(textId: string, taskId?: string): Promise<TextAnnotationEntry[]> {
    const params: Record<string, unknown> = {};
    if (taskId) params.task_id = taskId;
    return (await api.get<TextAnnotationEntry[]>(`/api/admin/texts/${textId}/annotations`, { params })).data;
  }

  async getNextText(taskIds: string[]): Promise<NextTextResponse | null> {
    const response = await api.post<NextTextResponse>('/api/texts/next', { task_ids: taskIds }, { validateStatus: (s) => s === 200 || s === 204 });
    return response.status === 204 ? null : response.data;
  }

  async submitAnnotations(payload: AnnotationSubmit): Promise<{ points: Record<string, number> }> {
    return (await api.post<{ points: Record<string, number> }>('/api/annotations', payload)).data;
  }

  async getGroundTruth(textId: string, taskIds: string[]): Promise<Record<string, string[]>> {
    return (await api.get<Record<string, string[]>>(`/api/texts/${textId}/ground-truth`, { params: { task_ids: taskIds } })).data;
  }

  async getMyStats(): Promise<MyStats> {
    return (await api.get<MyStats>('/api/stats/me')).data;
  }

  async getGlobalStats(): Promise<GlobalStats> {
    return (await api.get<GlobalStats>('/api/stats/global')).data;
  }

  async getLeaderboard(taskId: string, sinceDays?: number): Promise<LeaderboardEntry[]> {
    return (await api.get<LeaderboardEntry[]>(`/api/stats/leaderboard/${taskId}`, { params: sinceDays ? { since_days: sinceDays } : {} })).data;
  }

  async getOverallLeaderboard(sinceDays?: number): Promise<LeaderboardEntry[]> {
    return (await api.get<LeaderboardEntry[]>('/api/stats/leaderboard', { params: sinceDays ? { since_days: sinceDays } : {} })).data;
  }

  async uploadGroundTruth(jsonl: string): Promise<{ imported: number }> {
    return (await api.post<{ imported: number }>('/api/admin/ground-truth', jsonl, { headers: { 'Content-Type': 'text/plain' } })).data;
  }

  async uploadLlmAnnotations(jsonl: string): Promise<{ imported: number }> {
    return (await api.post<{ imported: number }>('/api/admin/llm-annotations', jsonl, { headers: { 'Content-Type': 'text/plain' } })).data;
  }

  async getAdminCoverage(): Promise<TaskCoverage[]> {
    return (await api.get<TaskCoverage[]>('/api/admin/coverage')).data;
  }

  async getAdminIrr(): Promise<UserReliabilityResponse[]> {
    return (await api.get<UserReliabilityResponse[]>('/api/admin/irr')).data;
  }

  async recomputeIrr(): Promise<void> {
    await api.post('/api/admin/irr/recompute');
  }

  async getVoiceCommentConfig(): Promise<VoiceCommentConfig> {
    return (await api.get<VoiceCommentConfig>('/api/voice-comments/config')).data;
  }

  async uploadVoiceComment(upload: VoiceCommentUpload): Promise<VoiceCommentCreated> {
    const form = new FormData();
    form.append('session_id', upload.session_id);
    form.append('language', upload.language);
    form.append('start_ms', String(Math.round(upload.start_ms)));
    form.append('end_ms', String(Math.round(upload.end_ms)));
    const ext = upload.audio.type.includes('mp4') ? 'mp4' : upload.audio.type.includes('ogg') ? 'ogg' : 'webm';
    form.append('audio', upload.audio, `recording.${ext}`);
    // Explicit multipart type overrides the instance's JSON default; axios adds the boundary.
    return (await api.post<VoiceCommentCreated>('/api/voice-comments', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })).data;
  }

  async getTextSessions(textId: string): Promise<AnnotationSessionEntry[]> {
    return (await api.get<AnnotationSessionEntry[]>(`/api/admin/texts/${textId}/sessions`)).data;
  }

  /** Audio needs the bearer token, so it is fetched as a blob instead of using <audio src>. */
  async getVoiceCommentAudio(voiceCommentId: string): Promise<Blob> {
    return (await api.get<Blob>(`/api/admin/voice-comments/${voiceCommentId}/audio`, { responseType: 'blob' })).data;
  }

  async retranscribeVoiceComment(voiceCommentId: string): Promise<void> {
    await api.post(`/api/admin/voice-comments/${voiceCommentId}/retranscribe`);
  }
}

export const apiService = new ApiService();
