export interface ConfigDTO {
  provider: string;
  model: string;
  base_url: string;
  api_key_set: boolean;
  demo_mode: boolean;
}

export interface RunEvent {
  kind: string;
  agent?: string;
  message?: string;
  tool?: string;
  helper?: string;
  data?: Record<string, unknown>;
  ts?: string;
}

export interface CatalogItem {
  item_name: string;
  category: string;
  unit_price: number;
  stock: number;
}

export interface DiscountTier {
  min_units: number;
  pct: number;
}

export interface PolicyDTO {
  discount_tiers: DiscountTier[];
  cash_floor: number;
}

export interface FinancialReport {
  cash_balance: number;
  inventory_value: number;
  total_assets: number;
  inventory_summary: { item_name: string; stock: number; value: number }[];
  top_selling_products: Record<string, unknown>[];
}

export interface RubricDTO {
  fulfilled_count: number;
  declined_count: number;
  cash_change_count: number;
  not_all_fulfilled: boolean;
  helpers_used: string[];
  all_helpers_used: boolean;
}

export interface CheckResult {
  name: string;
  passed: boolean;
  detail: string;
}

export interface JudgeScores {
  clarity: number;
  transparency: number;
  personality: number;
  persuasiveness: number;
  rationale: string;
}

export interface EvalRequestEntry {
  request_id: number;
  request_date: string;
  fulfilled: boolean;
  deterministic: CheckResult[];
}

export interface EvalReport {
  rubric: RubricDTO;
  requests: EvalRequestEntry[];
}

export interface QuoteResult {
  fulfilled: boolean;
  total_charged?: number;
  decline_reason?: string | null;
  delivery_date?: string | null;
}

export interface RunResult {
  request_date: string;
  reply: { text: string; fulfilled: boolean };
  quote?: {
    subtotal: number;
    discount_pct: number;
    discount_amount: number;
    total: number;
    rationale: string;
  } | null;
  sale?: QuoteResult | null;
}
