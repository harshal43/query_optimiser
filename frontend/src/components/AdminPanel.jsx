import { useState, useEffect, useCallback } from 'react';
import { getAdminConfig, saveAdminConfig } from '../services/api.js';

const ADVISOR_RULES = [
  { key: 'detect_select_star',                label: 'Detect SELECT *' },
  { key: 'detect_unnecessary_distinct',        label: 'Detect unnecessary DISTINCT' },
  { key: 'detect_cartesian_joins',             label: 'Detect Cartesian joins' },
  { key: 'suggest_partition_pruning',          label: 'Suggest partition pruning' },
  { key: 'suggest_clustering',                 label: 'Suggest clustering' },
  { key: 'suggest_removing_redundant_order_by',label: 'Suggest removing redundant ORDER BY' },
  { key: 'suggest_avoiding_unnecessary_ctes',  label: 'Suggest avoiding unnecessary CTEs' },
];

const OPTIMIZER_RULES = [
  { key: 'rewrite_union_to_union_all',    label: 'Rewrite UNION to UNION ALL' },
  { key: 'push_predicates_earlier',       label: 'Push predicates earlier' },
  { key: 'simplify_case_expressions',     label: 'Simplify CASE expressions' },
  { key: 'remove_redundant_order_by',     label: 'Remove redundant ORDER BY' },
  { key: 'eliminate_unnecessary_distinct',label: 'Eliminate unnecessary DISTINCT' },
  { key: 'simplify_nested_subqueries',    label: 'Simplify nested subqueries' },
];

const DEFAULT_CONFIG = {
  advisor_rules: {
    detect_select_star: true,
    detect_unnecessary_distinct: true,
    detect_cartesian_joins: true,
    suggest_partition_pruning: true,
    suggest_clustering: true,
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
  },
  optimization_goal: 'lowest_credits',
  aggressiveness: 'moderate',
  additional_llm_instructions: '',
};

export default function AdminPanel() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState(''); // '' | 'saved' | 'error'

  useEffect(() => {
    getAdminConfig()
      .then(setConfig)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const setAdvisorRule = useCallback((key, val) => {
    setConfig((prev) => ({ ...prev, advisor_rules: { ...prev.advisor_rules, [key]: val } }));
  }, []);

  const setOptimizerRule = useCallback((key, val) => {
    setConfig((prev) => ({ ...prev, optimizer_rules: { ...prev.optimizer_rules, [key]: val } }));
  }, []);

  const setTop = useCallback((key, val) => {
    setConfig((prev) => ({ ...prev, [key]: val }));
  }, []);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setSaveStatus('');
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

      {/* Advisor Rules */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>
          Advisor Agent Rules
          <span className="badge" style={{ marginLeft: 8 }}>AGENT 1</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {ADVISOR_RULES.map(({ key, label }) => (
            <CheckRow
              key={key}
              label={label}
              checked={config.advisor_rules[key] ?? false}
              onChange={(v) => setAdvisorRule(key, v)}
            />
          ))}
        </div>
      </div>

      {/* Optimizer Rules */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 16 }}>
          Optimizer Agent Rules
          <span className="badge" style={{ marginLeft: 8, background: 'rgba(63,185,80,0.15)', color: 'var(--success)' }}>AGENT 2</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 10 }}>
          {OPTIMIZER_RULES.map(({ key, label }) => (
            <CheckRow
              key={key}
              label={label}
              checked={config.optimizer_rules[key] ?? false}
              onChange={(v) => setOptimizerRule(key, v)}
            />
          ))}
        </div>
      </div>

      {/* Shared Settings */}
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

      {/* Additional LLM Instructions */}
      <div className="card">
        <div className="card-title" style={{ marginBottom: 12 }}>Additional LLM Instructions</div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 10, fontFamily: 'var(--sans)' }}>
          Appended to both agents' system prompts at runtime. Examples: "Preserve query readability." · "Do not rewrite JOIN structure." · "Avoid materialized view recommendations."
        </div>
        <textarea
          value={config.additional_llm_instructions}
          onChange={(e) => setTop('additional_llm_instructions', e.target.value)}
          placeholder="Enter additional instructions for both agents..."
          rows={5}
          style={{
            width: '100%', boxSizing: 'border-box',
            background: 'var(--bg)', border: '1px solid var(--border-2)',
            borderRadius: 'var(--radius)', color: 'var(--text)',
            fontFamily: 'var(--sans)', fontSize: 13, padding: '10px 12px',
            resize: 'vertical', lineHeight: 1.6, outline: 'none',
          }}
        />
      </div>

      {/* Save */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <button
          className="btn-optimize"
          onClick={handleSave}
          disabled={saving}
          style={{ minWidth: 140, justifyContent: 'center' }}
        >
          {saving ? <><span className="spinner" /> Saving...</> : 'Save Configuration'}
        </button>
        {saveStatus === 'saved' && (
          <span style={{ fontSize: 13, color: 'var(--success)', fontFamily: 'var(--sans)' }}>
            ✓ Configuration saved — takes effect on next analysis
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
