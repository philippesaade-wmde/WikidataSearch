export interface ResponseObject {
  QID: string
  similarity_score: number
  source: string
  label: string
  description: string
  imageUrl: string | null
}
