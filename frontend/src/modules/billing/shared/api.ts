import { apiClient } from '../../../shared/api/client'
import { prepareCsrf } from '../../../shared/api/csrf'
import type { PaginatedResponse } from '../../../shared/api/pagination'
import type { BillingDashboard, BillingPatient, ChargeItem, FinancialReport, Invoice, Payment } from './types'

export async function getBillingDashboard(): Promise<BillingDashboard> { return (await apiClient.get<BillingDashboard>('/billing/dashboard/')).data }
export async function getBillingPatients(search = ''): Promise<BillingPatient[]> { return (await apiClient.get<BillingPatient[]>('/billing/patients/', { params: { search } })).data }
export async function getChargeItems(): Promise<ChargeItem[]> { return (await apiClient.get<PaginatedResponse<ChargeItem>>('/charge-items/', { params: { page_size: 100 } })).data.data }
export async function createChargeItem(payload: unknown): Promise<ChargeItem> { await prepareCsrf(); return (await apiClient.post<ChargeItem>('/charge-items/', payload)).data }
export async function updateChargeItem(id: string, payload: unknown): Promise<ChargeItem> { await prepareCsrf(); return (await apiClient.patch<ChargeItem>(`/charge-items/${id}/`, payload)).data }
export async function getInvoices(patient?: string): Promise<Invoice[]> { return (await apiClient.get<PaginatedResponse<Invoice>>('/invoices/', { params: { page_size: 100, patient } })).data.data }
export async function createInvoice(payload: unknown): Promise<Invoice> { await prepareCsrf(); return (await apiClient.post<Invoice>('/invoices/', payload)).data }
export async function addInvoiceLine(id: string, payload: unknown): Promise<Invoice> { await prepareCsrf(); return (await apiClient.post<Invoice>(`/invoices/${id}/lines/`, payload)).data }
export async function issueInvoice(id: string, dueAt: string): Promise<Invoice> { await prepareCsrf(); return (await apiClient.post<Invoice>(`/invoices/${id}/issue/`, { due_at: dueAt })).data }
export async function voidInvoice(id: string, reason: string): Promise<Invoice> { await prepareCsrf(); return (await apiClient.post<Invoice>(`/invoices/${id}/void/`, { reason })).data }
export async function getPayments(): Promise<Payment[]> { return (await apiClient.get<PaginatedResponse<Payment>>('/payments/', { params: { page_size: 100 } })).data.data }
export async function createPayment(payload: unknown): Promise<Payment> { await prepareCsrf(); return (await apiClient.post<Payment>('/payments/', payload)).data }
export async function reversePayment(id: string, reason: string): Promise<Payment> { await prepareCsrf(); return (await apiClient.post<Payment>(`/payments/${id}/reverse/`, { reason })).data }
export async function getFinancialReport(): Promise<FinancialReport> { return (await apiClient.get<FinancialReport>('/reports/financial/')).data }
