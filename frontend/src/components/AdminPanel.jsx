import { useState, useEffect, useCallback } from 'react';
import { getAdminConfig, saveAdminConfig } from '../services/api.js';

const ADVISOR_RULES = [
  { key: 'detect_select_star',                 label: 'Detect SELECT *' },
  { key: 'detect_unnecessary_distinct',         label: 'Detect unnecessary DISTINCT' },
  { key: 'detect_cartesian_joins',              label: 'Detect Cartesian joins' },
  { key: 'detect_redundant_joins',              label: 'Detect redundant joins' },
  { key: 'detect_unused_ctes',                  label: 'Detect unused CTEs' },
  { key: 'suggest_partition_pruning',           label: 'Suggest partition pruning' },
  { key: 'suggest_clustering',                  label: 'Suggest clustering' },
  { key: 'suggest_column_pruning',              label: 'Suggest column pruning' },
  { key: 'suggest_filter_pushdown',             label: 'Suggest filter pushdown' },
  { key: 'suggest_result_cache_usage',          label: 'Suggest result cache usage' },
  { key: 'suggest_removing_redundant_order_by', label: 'Suggest removing redundant ORDER BY' },
  { key: 'suggest_avoiding_unnecessary_ctes',   label: 'Suggest avoiding unnecessary CTEs' },
];

const OPTIMIZER_RULES = [
  { key: 'rewrite_union_to_union_all',     label: 'Rewrite UNION to UNION ALL' },
  { key: 'push_predicates_earlier',        label: 'Push predicates earlier' },
  { key: 'simplify_case_expressions',      label: 'Simplify CASE expressions' },
  { key: 'remove_redundant_order_by',      label: 'Remove redundant ORDER BY' },
  { key: 'eliminate_unnecessary_distinct', label: 'Eliminate unnecessary DISTINCT' },
  { key: 'simplify_nested_subqueries',     label: 'Simplify nested subqueries' },
  { key: 'remove_unused_columns',          label: 'Remove unused columns' },
  { key: 'rewrite_correlated_subqueries',  label: 'Rewrite correlated subqueries' },
];

const SAFETY_RULES = [
  { key: 'preserve_query_semantics', label: 'Preserve query semantics' },
  { key: 'preserve_output_order',    label: 'Preserve output order' },
];

const OUTPUT_RULES = [
  { key: 'generate_change_summary', label: 'Generate change summary' },
];

const DEFAULT_CONFIG = {
  advisor_rules: {
    detect_select_star: true,
    detect_unnecessary_distinct: true,
    detect_cartesian_joins: true,
    detect_redundant_joins: true,
    detect_unused_ctes: true,
    suggest_partition_pruning: true,
    suggest_clustering: true,
    suggest_column_pruning: true,
    suggest_filter_pushdown: true,
    suggest_result_cache_usage: true,
    suggest_removing_redundant_order_by: true,
    suggest_avoiding_unnecessary_ctes: false,
  },
  optimizer_rules: {
    rewrite_union_to_union_all: true,
    push_predicates_earlier: true,
    simplify_case_expressions: true,
    remove_redundant_order_by: false,
    eliminate_unnecessary_distinct: true,
    simplify_nested_subqueries: true,
    remove_unused_columns: true,
    rewrite_correlated_subqueries: true,
  },
  safety_rules: {
    preserve_query_semantics: true,
    preserve_output_order: true,
  },
  output_rules: {
    generate_change_summary: true,
  },
  optimization_goal: 'lowest_credits',
  aggressiveness: 'moderate',
  additional_llm_instructions: '',
};

export default function AdminPanel() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');

  useEffect(() => {
    getAdminConfig()
      .then((remote) => setConfig({ ...DEFAULT_CONFIG, ...remote }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const setAdvisorRule    = useCallback((key, val) => setConfig((p) => ({ ...p, advisor_rules:   { ...p.advisor_rules,   [key]: val } })), []);
  const setOptimizerRule  = useCallback((key, val) => setConfig((p) => ({ ...p, optimizer_rules: { ...p.optimizer_rules, [key]: val } })), []);
  const setSafetyRule     = useCallback((key, val) => setConfig((p) => ({ ...p, safety_rules:    { ...p.safety_rules,    [key]: val } })), []);
  const setOutputRule     = useCallback((key, val) => setConfig((p) => ({ ...p, output_rules:    { ...p.output_rules,    [key]: val } })), []);
  const setTop            = useCallback((key, val) => setConfig((p) => ({ ...p, [key]: val })), []);

  const handleSave = useCallback(async () => {
    setSaving(true); setSaveStatus('');
    try {
      await saveAdminConfig(config);
      setSaveStatus('saved');
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
      setTimeout(() => setSaveStatus(''), 3000);
    }
  }, [config]);

  const handleReset = useCallback(() => {
    setConfig(DEFAULT_CONFIG);
    setSaveStatus('');
  }, []);

  if (loading) {
    return (
      <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: 32, justifyContent: 'center' }}>
        <span className="spinner" style={{ width: 20, height: 20, borderWidth: 3, borderColor: 'rgba(88,166,255,0.2)', borderTopColor: 'var(--accent)' }} />
        <span style={{ fontSize: 13, color: 'var(--text-dim)', fontFamily: 'var(--sans)' }}>Loading configuration...</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {/* 1. Advisor Rules */}
      <RuleCard
        title="Advisor Agent Rules"
        badge={{ label: 'AGENT 1', style: {} }}
        rules={ADVISOR_RULES}
        values={config.advisor_rules}
        onChange={setAdvisorRule}
      />

      {/* 2. Optimizer Rules */}
      <RuleCard
        title="Optimizer Agent Rules"
        badge={{ label: 'AGENT 2', style: { background: 'rgba(63,185,80,0.15)', color: 'var(--success)' } }}
        rules={OPTIMIZER_RULES}
        values={config.optimizer_rules}
        onChange={setOptimizerRule}
      />

      {/* 3. Safety Rules */}
      <RuleCard
        title="Safety Rules"
        badge={{ label: 'GUARDRAILS', style: { background: 'rgba(255,166,0,0.15)', color: '#f0a500' } }}
        rules={SAFETY_RULES}
        values={config.safety_rules}
        onChange={setSafetyRule}
        hint="When enabled, the optimizer is instructed to preserve these properties even when making aggressive rewrites."
      />

      {/* 4. Output Rules */}
      <RuleCard
        title="Output Rules"
        badge={{ label: 'OUTPUT', style: { background: 'rgba(163,113,247,0.15)', color: '#a371f7' } }}
        rules={OUTPUT_RULES}
        values={config.output_rules}
        onChange={setOutputRule}
        hint="Controls what additional content the optimizer agent includes in its response."
      />

      {/* 5. Shared Settings */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>Shared Optimization Settings</div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
          <div className="field" style={{ minWidth: 220, flex: 1, marginBottom: 0 }}>
            <label>Optimization Goal</label>
            <select value={config.optimization_goal} onChange={(e) => setTop('optimization_goal', e.target.value)}>
              <option value="lowest_credits">Lowest Credits</option>
              <option value="fastest_performance">Fastest Performance</option>
              <option value="balanced">Balanced</option>
            </select>
          </div>
          <div className="field" style={{ minWidth: 220, flex: 1, marginBottom: 0 }}>
            <label>Optimization Aggressiveness</label>
            <select value={config.aggressiveness} onChange={(e) => setTop('aggressiveness', e.target.value)}>
              <option value="conservative">Conservative</option>
              <option value="moderate">Moderate</option>
              <option value="aggressive">Aggressive</option>
            </select>
          </div>
        </div>
      </div>

      {/* 6. Additional LLM Instructions */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 12 }}>Additional LLM Instructions</div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 10, fontFamily: 'var(--sans)' }}>
          Appended to both agents' system prompts at runtime.
        </div>
        <textarea
          value={config.additional_llm_instructions}
          onChange={(e) => setTop('additional_llm_instructions', e.target.value)}
          placeholder={"Preserve readability.\nAvoid join restructuring.\nPrefer simple rewrites."}
          rows={4}
          style={{
            width: '100%', boxSizing: 'border-box',
            background: 'var(--bg)', border: '1px solid var(--border-2)',
            borderRadius: 'var(--radius)', color: 'var(--text)',
            fontFamily: 'var(--sans)', fontSize: 13, padding: '10px 12px',
            resize: 'vertical', lineHeight: 1.6, outline: 'none',
          }}
        />
      </div>

      {/* 7+8. Save + Reset */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <button
          className="btn-optimize"
          onClick={handleSave}
          disabled={saving}
          style={{ minWidth: 160, justifyContent: 'center' }}
        >
          {saving ? <><span className="spinner" /> Saving...</> : 'Save Configuration'}
        </button>
        <button
          className="btn btn-secondary"
          onClick={handleReset}
          disabled={saving}
          style={{ fontSize: 13, padding: '8px 18px' }}
        >
          Reset Defaults
        </button>
        {saveStatus === 'saved' && (
          <span style={{ fontSize: 13, color: 'var(--success)', fontFamily: 'var(--sans)' }}>
            ✓ Saved — takes effect on next analysis
          </span>
        )}
        {saveStatus === 'error' && (
          <span style={{ fontSize: 13, color: '#f85149', fontFamily: 'var(--sans)' }}>
            ✗ Failed to save. Check backend connection.
          </span>
        )}
      </div>
    </div>
  );
}

function RuleCard({ title, badge, rules, values, onChange, hint }) {
  return (
    <div className="card">
      <div className="card-title" style={{ marginBottom: hint ? 8 : 16 }}>
        {title}
        {badge && (
          <span className="badge" style={{ marginLeft: 8, ...badge.style }}>{badge.label}</span>
        )}
      </div>
      {hint && (
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 14, fontFamily: 'var(--sans)' }}>
          {hint}
        </div>
      )}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 10 }}>
        {rules.map(({ key, label }) => (
          <CheckRow
            key={key}
            label={label}
            checked={values?.[key] ?? false}
            onChange={(v) => onChange(key, v)}
          />
        ))}
      </div>
    </div>
  );
}

function CheckRow({ label, checked, onChange }) {
  return (
    <label style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '8px 12px',
      borderRadius: 'var(--radius)',
      border: `1px solid ${checked ? 'var(--accent-dim)' : 'var(--border-2)'}`,
      background: checked ? 'rgba(88,166,255,0.06)' : 'var(--surface-2)',
      cursor: 'pointer', transition: 'border-color 0.15s, background 0.15s',
      userSelect: 'none',
    }}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        style={{ accentColor: 'var(--accent)', cursor: 'pointer', flexShrink: 0, width: 14, height: 14 }}
      />
      <span style={{ fontSize: 12, color: checked ? 'var(--text)' : 'var(--text-muted)', fontFamily: 'var(--sans)' }}>
        {label}
      </span>
    </label>
  );
}
