export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type QueryStatus = 'pending_review' | 'approved' | 'rejected' | 'ab_testing'
export type ABTestStatus = 'shadow' | 'active' | 'completed' | 'rolled_back'
export type UserAction = 'approved' | 'rejected' | 'modified'

export interface Query {
  query_id: string
  query_text: string
  query_hash: string
  query_preview: string | null
  team_id: string | null
  warehouse: string | null
  warehouse_size: string | null
  classification: string | null
  severity: Severity | null
  issue_type: string | null
  execution_metrics: Record<string, unknown>
  ingestion_timestamp: string
  source: string
  status: QueryStatus
}

export interface Optimization {
  optimization_id: string
  query_id: string
  diagnosis: Record<string, unknown>
  variants: unknown[]
  cost_predictions: Record<string, unknown>
  validation_results: Record<string, unknown>
  recommended_variant: string | null
  user_selected_variant: string | null
  status: string
  created_at: string
  updated_at: string
}

export interface ABTest {
  test_id: string
  query_id: string
  optimization_id: string | null
  traffic_split: { control: number; optimized: number }
  control_metrics: Record<string, unknown>
  variant_metrics: Record<string, unknown>
  status: ABTestStatus
  p_value: number | null
  started_at: string
  completed_at: string | null
}

export interface Team {
  team_id: string
  name: string
  warehouse: string
  warehouse_size: string
  enforcement_level: string
  ab_test_config: Record<string, unknown>
  standardization_rules: Record<string, unknown>
  created_at: string
}

export interface HealthCheck {
  status: 'ready' | 'degraded'
  checks: {
    db: string
    faiss: string
    snowflake: string
  }
}

export interface ApiResponse<T> {
  success: boolean
  data: T | null
  meta: { timestamp: string; request_id: string }
  error: { code: string; message: string } | null
}
