export const ROLES = ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER'] as const
export type Role = (typeof ROLES)[number]

export const EQUIPMENT_CONDITIONS = ['NORMAL', 'FAULT', 'UNCERTAIN'] as const
export type EquipmentCondition = (typeof EQUIPMENT_CONDITIONS)[number]

export const DATA_QUALITY_STATES = ['VALID', 'SENSOR_INVALID'] as const
export type DataQuality = (typeof DATA_QUALITY_STATES)[number]

export const PREDICTION_DECISIONS = ['NORMAL', 'FAULT', 'UNCERTAIN', 'SENSOR_INVALID'] as const
export type PredictionDecision = (typeof PREDICTION_DECISIONS)[number]

export const CONNECTIVITY_STATES = [
  'ONLINE',
  'OFFLINE_BUFFERING',
  'SYNCING',
  'SYNCED',
  'SYNC_ERROR',
] as const
export type ConnectivityStatus = (typeof CONNECTIVITY_STATES)[number]

export const PROVENANCE_KINDS = ['SIMULATED', 'EXPERIMENTAL'] as const
export type Provenance = (typeof PROVENANCE_KINDS)[number]

export const ALERT_CATEGORIES = ['FAULT', 'UNCERTAIN', 'SENSOR_INVALID'] as const
export type AlertCategory = (typeof ALERT_CATEGORIES)[number]

export const ALERT_SEVERITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const
export type AlertSeverity = (typeof ALERT_SEVERITIES)[number]

export const ALERT_STATUSES = ['OPEN', 'ACKNOWLEDGED', 'REVIEWED', 'CLOSED', 'DISMISSED'] as const
export type AlertStatus = (typeof ALERT_STATUSES)[number]

export const REVIEW_ACTIONS = [
  'ACKNOWLEDGE',
  'REVIEW',
  'CONFIRM_LABEL',
  'CORRECT_LABEL',
  'ADD_NOTE',
  'CLOSE',
] as const
export type ReviewAction = (typeof REVIEW_ACTIONS)[number]

export const PUMP_TYPES = ['CENTRIFUGAL', 'POSITIVE_DISPLACEMENT', 'OTHER'] as const
export type PumpType = (typeof PUMP_TYPES)[number]

export const PUMP_STATUSES = ['ACTIVE', 'MAINTENANCE', 'RETIRED'] as const
export type PumpStatus = (typeof PUMP_STATUSES)[number]

export const SENSOR_TYPES = ['VIBRATION', 'RPM', 'TEMPERATURE'] as const
export type SensorType = (typeof SENSOR_TYPES)[number]

export const MOUNTING_AXES = [
  'AXIAL',
  'RADIAL_X',
  'RADIAL_Y',
  'RADIAL_Z',
  'UNKNOWN',
] as const
export type MountingAxis = (typeof MOUNTING_AXES)[number]

export const SESSION_STATUSES = ['ACTIVE', 'COMPLETED', 'ABORTED'] as const
export type SessionStatus = (typeof SESSION_STATUSES)[number]

export const MODEL_STATUSES = ['REGISTERED', 'VALIDATED', 'ACTIVE', 'RETIRED', 'REJECTED'] as const
export type ModelStatus = (typeof MODEL_STATUSES)[number]

export const MODEL_RUNTIMES = [
  'ONNX',
  'SKLEARN',
  'TFLITE',
  'BASELINE',
  'LINEAR_JSON',
] as const
export type ModelRuntime = (typeof MODEL_RUNTIMES)[number]

export const REPORT_TYPES = [
  'MONITORING_SUMMARY',
  'ALERT_HISTORY',
  'MODEL_EVALUATION',
  'SENSOR_HEALTH',
  'ENGINEERING_REVIEW',
  'EXPERIMENTAL_DATA_EXPORT',
] as const
export type ReportType = (typeof REPORT_TYPES)[number]


export const REPORT_STATUSES = ['QUEUED', 'RUNNING', 'COMPLETED', 'FAILED'] as const
export type ReportStatus = (typeof REPORT_STATUSES)[number]

export interface ReportJob {
  id: string
  report_type: ReportType
  status: ReportStatus
  requested_by_name: string | null
  parameters: Record<string, unknown>
  includes_simulated_data: boolean
  file_name: string | null
  file_sha256: string | null
  error_message: string | null
  created_at: string
  completed_at: string | null
}

export interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: Role
  is_active: boolean
  must_change_password: boolean
  created_at: string
  last_login_at: string | null
}

export interface OperatingRegime {
  id: string
  code: string
  name: string
  description: string
  is_active: boolean
}

export interface Sensor {
  id: string
  sensor_code: string
  pump_id: string | null
  pump_code: string | null
  sensor_type: SensorType
  manufacturer: string | null
  model_name: string | null
  mounting_axis: MountingAxis
  mounting_position: string
  sampling_rate_hz: number
  is_active: boolean
  installed_at: string | null
  created_at: string
  updated_at: string
}

export interface SensorCreate {
  sensor_code: string
  sensor_type: SensorType
  manufacturer?: string | null
  model_name?: string | null
  mounting_axis: MountingAxis
  mounting_position: string
  sampling_rate_hz: number
  is_active?: boolean
  installed_at?: string | null
}

export interface SensorRegister extends SensorCreate {
  pump_id?: string | null
}

export interface SensorUpdate {
  pump_id?: string | null
  sensor_type?: SensorType
  manufacturer?: string | null
  model_name?: string | null
  mounting_axis?: MountingAxis
  mounting_position?: string
  sampling_rate_hz?: number
  is_active?: boolean
}

export interface Pump {
  id: string
  pump_code: string
  name: string
  pump_type: PumpType
  location: string
  rated_speed_rpm: number
  default_regime: OperatingRegime | null
  status: PumpStatus
  notes: string | null
  sensors: Sensor[]
  registered_at: string
  created_at: string
  updated_at: string
}

export interface PumpCreate {
  pump_code: string
  name: string
  pump_type: PumpType
  location: string
  rated_speed_rpm: number
  default_regime_id?: string | null
  status: PumpStatus
  notes?: string | null
  sensor?: SensorCreate | null
}

export interface PumpUpdate {
  name?: string
  pump_type?: PumpType
  location?: string
  rated_speed_rpm?: number
  default_regime_id?: string | null
  status?: PumpStatus
  notes?: string | null
}

export type SamplingStatus = 'NO_DATA' | 'RECENT' | 'STALE' | 'SENSOR_INVALID'

export interface WindowPoint {
  window_id: string
  session_id: string
  pump_id: string
  pump_code: string
  sensor_id: string
  sensor_code: string
  window_index: number
  window_start: string
  window_end: string
  quality_status: DataQuality
  data_provenance: Provenance
  scenario: string | null
  sample_count: number
  rms: number | null
  peak_abs: number | null
  validation_issue_codes: string[]
}

export interface LiveWindow extends WindowPoint {
  sampling_rate_hz: number
  units: string | null
  waveform: number[] | null
  validation_summary: Record<string, unknown> | null
}

export interface SensorHealth {
  sensor_id: string
  sensor_code: string
  pump_id: string | null
  pump_code: string | null
  sensor_type: SensorType
  is_active: boolean
  sampling_rate_hz: number
  total_windows: number
  valid_windows: number
  invalid_windows: number
  missing_window_gaps: number
  last_reading_at: string | null
  last_valid_reading_at: string | null
  freshness_seconds: number | null
  latest_quality: DataQuality | null
  data_quality: DataQuality | null
  sampling_status: SamplingStatus
  connection_state: 'NO_LIVE_CHANNEL'
  latest_rms: number | null
  latest_peak_abs: number | null
  latest_scenario: string | null
  provenance: Provenance | null
  latest_validation_issues: Array<Record<string, unknown>>
}

export interface SessionSummary {
  id: string
  pump_id: string
  pump_code: string
  sensor_id: string
  sensor_code: string
  scenario: string | null
  status: SessionStatus
  data_provenance: Provenance
  sampling_rate_hz: number
  started_at: string
  ended_at: string | null
  window_count: number
  started_by_name: string | null
}

export interface LiveSnapshot {
  pump_id: string
  pump_code: string
  pump_name: string
  sensor_id: string
  sensor_code: string
  sensor_type: SensorType
  latest_window: LiveWindow | null
  recent_windows: WindowPoint[]
  latest_prediction: Prediction | null
  session: SessionSummary | null
  sensor_health: SensorHealth
  equipment_condition: EquipmentCondition | null
  condition_available: boolean
  data_quality: DataQuality | null
  edge_connectivity: ConnectivityStatus | null
  edge_note: string
  data_mode: 'SIMULATED_REPLAY' | 'NO_DATA'
  buffering_state: string | null
  generated_at: string
}

export interface ModelSummary {
  id: string
  model_code: string
  name: string
  version: string
  status: ModelStatus
  balanced_accuracy: number | null
  macro_f1: number | null
  evaluation_dataset: string | null
  evaluated_at: string | null
  data_provenance: Provenance | null
}

export interface EvaluationSummary {
  id: string
  model_version_id: string
  dataset_name: string
  dataset_version: string
  data_provenance: Provenance
  balanced_accuracy: number | null
  macro_f1: number | null
  sample_count: number
  evaluated_at: string
  is_verified: boolean
}

export interface MonitoringOverview {
  pumps_total: number
  pumps_active: number
  sensors_total: number
  sensors_active: number
  active_alerts: number
  sessions_total: number
  windows_total: number
  valid_windows: number
  invalid_windows: number
  latest_session: SessionSummary | null
  latest_window: LiveWindow | null
  latest_prediction: Prediction | null
  trend: WindowPoint[]
  sensors_with_data: number
  sensors_stale: number
  sensors_invalid: number
  sensors_no_data: number
  equipment_condition: EquipmentCondition | null
  condition_available: boolean
  data_quality: DataQuality | null
  edge_connectivity: ConnectivityStatus | null
  edge_note: string
  data_mode: 'SIMULATED_REPLAY' | 'NO_DATA'
  active_model: ModelSummary | null
  latest_evaluation: EvaluationSummary | null
  recent_sessions: SessionSummary[]
  generated_at: string
}

export interface PredictionModel {
  id: string
  model_code: string
  name: string
  version: string
  runtime: ModelRuntime
}

export interface Prediction {
  id: string
  event_id: string
  pump_id: string
  pump_code: string
  sensor_id: string
  sensor_code: string
  session_id: string
  signal_window_id: string
  model: PredictionModel | null
  operating_regime: OperatingRegime | null
  decision: PredictionDecision
  data_quality: DataQuality
  equipment_condition: EquipmentCondition | null
  decision_score: number | null
  uncertainty_score: number | null
  explanation: string
  latency_ms: number | null
  inferred_at: string
  data_provenance: Provenance
  created_at: string
  window_start: string
  window_end: string
  window_quality: DataQuality
  sample_count: number
  features: Record<string, unknown> | null
  scenario: string | null
}

export interface Alert {
  id: string
  event_id: string
  pump_id: string
  pump_code: string
  sensor_id: string
  sensor_code: string
  prediction_id: string | null
  signal_window_id: string | null
  window_start: string | null
  window_end: string | null
  category: AlertCategory
  severity: AlertSeverity
  status: AlertStatus
  title: string
  description: string
  decision: PredictionDecision | null
  data_quality: DataQuality | null
  decision_score: number | null
  uncertainty_score: number | null
  model_name: string | null
  model_version: string | null
  data_provenance: Provenance
  assigned_reviewer_id: string | null
  assigned_reviewer_name: string | null
  acknowledged_at: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
  review_count: number
}

export interface AlertReview {
  id: string
  alert_id: string
  reviewer_id: string
  reviewer_name: string
  action: ReviewAction
  reviewed_label: PredictionDecision | null
  notes: string
  label_source: 'ENGINEER_REVIEW'
  is_verified_ground_truth: boolean
  created_at: string
}

export interface AlertDetail extends Alert {
  prediction: Prediction | null
  reviews: AlertReview[]
}

export interface AlertReviewCreate {
  alert_id: string
  action: Exclude<ReviewAction, 'ACKNOWLEDGE'>
  reviewed_label?: PredictionDecision | null
  notes?: string
}


export type CopilotMonitoringMode = 'SIMULATED' | 'EXPERIMENTAL'

export interface CopilotPageContext {
  route: string
  screenName: string
  selectedPumpId?: string | null
  selectedSensorId?: string | null
  selectedAlertId?: string | null
  activeModelVersion?: string | null
  operatingRegime?: string | null
  monitoringMode: CopilotMonitoringMode
  connectivityStatus: string
}

export const COPILOT_ACTION_TYPES = [
  'NAVIGATE_TO_SCREEN',
  'SELECT_PUMP',
  'OPEN_ALERT_DETAILS',
  'HIGHLIGHT_SENSOR',
  'OPEN_HISTORICAL_TRENDS',
  'SET_MONITORING_TIME_RANGE',
  'OPEN_REPORT',
  'SHOW_CONFIRMATION_DIALOG',
] as const
export type CopilotActionType = (typeof COPILOT_ACTION_TYPES)[number]

export interface CopilotAction {
  type: CopilotActionType
  payload: Record<string, unknown>
}

export interface CopilotAvailability {
  enabled: boolean
  provider: string
  model: string | null
  mode: 'deterministic' | 'remote_llm' | 'deterministic_fallback' | 'unavailable'
  mcpAvailable: boolean
  mcpTransport: string
  message: string
}

export interface CopilotToolRun {
  id: string
  toolName: string
  status: 'EXECUTING' | 'EXECUTED' | 'FAILED' | 'PENDING_APPROVAL' | 'REJECTED'
  requiresApproval: boolean
  arguments: Record<string, unknown>
  result: Record<string, unknown> | null
  error: string | null
  createdAt: string
  completedAt: string | null
}

export interface CopilotApproval {
  id: string
  toolName: string
  status: string
  arguments: Record<string, unknown>
  summary: string
  createdAt: string
}

export interface CopilotAssistantMessage {
  id: string
  role: 'ASSISTANT'
  content: string
  actions: CopilotAction[]
  suggestedQuestions: string[]
  toolRunIds: string[]
  approvalId: string | null
  createdAt: string
}

export interface CopilotChatRequest {
  message: string
  conversationId?: string | null
  context: CopilotPageContext
}

export interface CopilotChatResponse {
  conversationId: string
  assistantMessage: CopilotAssistantMessage
  toolRuns: CopilotToolRun[]
  approval: CopilotApproval | null
  availability: CopilotAvailability
}

export interface CopilotStatus {
  enabled: boolean
  provider: string
  model: string | null
  providerConfigured: boolean
  mcpAvailable: boolean
  mcpTransport: string
  toolCount: number
  message: string
}

export interface CopilotToolRequest {
  arguments: Record<string, unknown>
  context: CopilotPageContext
  conversationId?: string | null
}

export interface CopilotToolResponse {
  conversationId: string | null
  toolRun: CopilotToolRun
  actions: CopilotAction[]
}

export interface CopilotApprovalDecisionResponse {
  approval: CopilotApproval
  toolRun: CopilotToolRun
  actions: CopilotAction[]
  message: string
  availability: CopilotAvailability
}

export interface CopilotConversationMessage {
  id: string
  role: string
  content: string
  createdAt: string
  actions: CopilotAction[]
  approvalId: string | null
}

export interface CopilotConversation {
  id: string
  title: string
  context: Record<string, unknown>
  createdAt: string
  updatedAt: string
  messages: CopilotConversationMessage[]
  toolRuns: CopilotToolRun[]
  pendingApprovals: CopilotApproval[]
}

export interface ModelEvaluation {
  id: string
  model_version_id: string
  dataset_name: string
  dataset_version: string
  data_provenance: Provenance
  evaluation_protocol: string
  split_description: string
  sample_count: number
  balanced_accuracy: number | null
  macro_f1: number | null
  metrics: Record<string, unknown> | null
  confusion_matrix: Record<string, unknown> | null
  risk_coverage: Record<string, unknown> | null
  calibration: Record<string, unknown> | null
  is_verified: boolean
  verified_by_name: string | null
  verified_at: string | null
  evaluated_by: string
  evaluated_at: string
  notes: string | null
}

export interface ModelVersion {
  id: string
  model_code: string
  name: string
  version: string
  algorithm: string
  runtime: ModelRuntime
  feature_contract: Record<string, unknown>
  training_dataset_version: string
  evaluation_dataset: string
  deployment_compatibility: Record<string, unknown>
  artifact_path: string
  artifact_sha256: string
  status: ModelStatus
  registered_by_name: string | null
  registered_at: string
  validated_at: string | null
  activated_at: string | null
  retired_at: string | null
  notes: string | null
  latest_evaluation: ModelEvaluation | null
}

export interface ModelDetail extends ModelVersion {
  evaluations: ModelEvaluation[]
}

export interface AcquisitionSession {
  id: string
  pump_id: string
  pump_code: string
  sensor_id: string
  sensor_code: string
  regime: OperatingRegime | null
  started_by_id: string | null
  started_by_name: string | null
  sampling_rate_hz: number
  data_provenance: Provenance
  random_seed: number | null
  scenario: string | null
  status: SessionStatus
  source_device_id: string | null
  started_at: string
  ended_at: string | null
  notes: string | null
  window_count: number
  created_at: string
}

export interface AuthSession {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  user: User
}

export interface LoginRequest {
  identifier: string
  password: string
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiErrorDetail {
  field?: string
  message?: string
  type?: string
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    request_id?: string | null
    details?: ApiErrorDetail[]
  }
}

export interface HealthStatus {
  status: 'ok' | 'degraded'
  service: string
  version: string
  environment: string
  database: 'ok' | 'unavailable'
  timestamp: string
}

export interface SystemInfo {
  project: string
  version: string
  environment: string
  api_prefix: string
  auth_scheme: string
  access_token_minutes: number
  refresh_token_days: number
  database_dialect: string
  role: Role
  data_mode: string
}


