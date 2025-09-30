export interface ResponseObject {
  id: string
  similarity_score: number
  source: string
  label: string
  description: string
  imageUrl: string | undefined
  imagePageUrl: string | undefined
  query: string | null
  lang: string | null
}
