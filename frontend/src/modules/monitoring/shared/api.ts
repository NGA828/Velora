import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { MonitoringThread } from './types'

export async function getMonitoringThreads(patient?: string): Promise<MonitoringThread[]> {
  return (await apiClient.get<PaginatedResponse<MonitoringThread>>('/monitoring-threads/', { params: { patient, page_size: 100 } })).data.data
}
export async function createMonitoringThread(payload: unknown): Promise<MonitoringThread> {
  await prepareCsrf(); return (await apiClient.post<MonitoringThread>('/monitoring-threads/', payload)).data
}
export async function addMonitoringQuestion(thread: string, payload: unknown): Promise<MonitoringThread> {
  await prepareCsrf(); return (await apiClient.post<MonitoringThread>(`/monitoring-threads/${thread}/questions/`, payload)).data
}
export async function answerMonitoringQuestion(thread: string, question: string, answer: unknown): Promise<MonitoringThread> {
  await prepareCsrf(); return (await apiClient.post<MonitoringThread>(`/monitoring-threads/${thread}/questions/${question}/answer/`, { answer })).data
}
export async function closeMonitoringThread(thread: string): Promise<MonitoringThread> {
  await prepareCsrf(); return (await apiClient.post<MonitoringThread>(`/monitoring-threads/${thread}/close/`)).data
}
