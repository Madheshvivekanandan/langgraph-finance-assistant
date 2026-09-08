/** RFC 9457 problem+json body returned by every API error. */
export interface ProblemDetail {
  type: string
  title: string
  status: number
  detail: string
  code: string
}
