export interface Pagination {
  count: number
  page: number
  pages: number
  page_size: number
  next: string | null
  previous: string | null
}

export interface PaginatedResponse<T> {
  data: T[]
  pagination: Pagination
}
