import { useState, useEffect, useCallback } from 'react';
import * as XLSX from 'xlsx';
import ConfigPanel from './components/ConfigPanel.jsx';
import BatchPanel from './components/BatchPanel.jsx';
import OriginalQueryPanel from './components/OriginalQueryPanel.jsx';
import SuggestionsPanel from './components/SuggestionsPanel.jsx';
import OptimizedQueryPanel from './components/OptimizedQueryPanel.jsx';
import CostComparison from './components/CostComparison.jsx';
import CostBreakdown from './components/CostBreakdown.jsx';
import TokenBadge from './components/TokenBadge.jsx';
import SnowflakeConnectModal from './components/SnowflakeConnectModal.jsx';
import SnowflakeDashboard from './components/SnowflakeDashboard.jsx';
import {
  fetchQueryIds, fetchQueryDetail, uploadExcel, analyzeQuery, optimizeQuery,
  analyzeCustomQuery, optimizeCustomQuery,
  connectSnowflake, checkSnowflakeStatus, disconnectSnowflake,
} from './services/api.js';

const DEFAULT_CONFIG = { model: 'claude-sonnet-4' };

export default function App() {
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [queryIds, setQueryIds] = useState([]);
  const [selectedQueryId, setSelectedQueryId] = useState('');
  const [queryDetail, setQueryDetail] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState(null);
  const [selectedNums, setSelectedNums] = useState(new Set());
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState(null);
  const [uploadedFilename, setUploadedFilename] = useState('');
  const [uploading, setUploading] = useState(false);
  const [inputMode, setInputMode] = useState('excel');
  const [customQueryText, setCustomQueryText] = useState('');
  const [customCredits, setCustomCredits] = useState('');
  const [batchPhase, setBatchPhase] = useState('idle');
  const [batchProgress, setBatchProgress] = useState(null);
  const [batchRunIds, setBatchRunIds] = useState([]);
  const [batchAnalyzeResults, setBatchAnalyzeResults] = useState({});
  const [batchSuggestionSelections, setBatchSuggestionSelections] = useState({});
  const [batchOptimizeResults, setBatchOptimizeResults] = useState({});
  const [batchViewQueryId, setBatchViewQueryId] = useState('');
  const [error, setError] = useState('');

  // Snowflake connection state
  const [sfConnected, setSfConnected]       = useState(false);
  const [sfAccount, setSfAccount]           = useState('');
  const [showSfModal, setShowSfModal]       = useState(false);
  const [sfConnecting, setSfConnecting]     = useState(false);
  const [sfConnectError, setSfConnectError] = useState('');

  useEffect(() => {
    if (!selectedQueryId) { setQueryDetail(null); setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null); return; }
    fetchQueryDetail(selectedQueryId).then((detail) => {
      setQueryDetail(detail); setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null); setError('');
    }).catch((err) => setError(`Failed to load query: ${err.message}`));
  }, [selectedQueryId]);

  const handleUpload = useCallback(async (file) => {
    setUploading(true); setError(''); setSelectedQueryId(''); setQueryDetail(null); setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null);
    setBatchPhase('idle'); setBatchRunIds([]); setBatchAnalyzeResults({}); setBatchSuggestionSelections({}); setBatchOptimizeResults({}); setBatchViewQueryId('');
    try {
      const res = await uploadExcel(file);
      setQueryIds(res.query_ids); setUploadedFilename(res.filename);
    } catch (err) { setError(`Upload failed: ${err.message}`); }
    finally { setUploading(false); }
  }, []);

  const handleConfigChange = useCallback((field, value) => { setConfig((prev) => ({ ...prev, [field]: value })); }, []);

  const handleInputModeChange = useCallback((mode) => {
    setInputMode(mode); setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null); setError('');
  }, []);

  const handleAnalyze = useCallback(async () => {
    setError(''); setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null); setAnalyzing(true);
    try {
      let res;
      if (inputMode === 'custom') { res = await analyzeCustomQuery(customQueryText, parseFloat(customCredits) || 0, config.model); }
      else { res = await analyzeQuery(selectedQueryId, config.model); }
      setAnalyzeResult(res); setSelectedNums(new Set(res.parsed_suggestions.map((s) => s.number)));
    } catch (err) { setError(`Analysis failed: ${err.message}`); }
    finally { setAnalyzing(false); }
  }, [selectedQueryId, config, inputMode, customQueryText, customCredits]);

  const handleToggleSuggestion = useCallback((number) => {
    setSelectedNums((prev) => { const next = new Set(prev); next.has(number) ? next.delete(number) : next.add(number); return next; });
  }, []);

  const handleOptimize = useCallback(async () => {
    if (!analyzeResult) return;
    const selectedTexts = analyzeResult.parsed_suggestions.filter((s) => selectedNums.has(s.number)).map((s) => s.full_text);
    if (selectedTexts.length === 0) { setError('Please select at least one suggestion before optimizing.'); return; }
    setError(''); setOptimizeResult(null); setOptimizing(true);
    try {
      let res;
      if (inputMode === 'custom') { res = await optimizeCustomQuery(customQueryText, parseFloat(customCredits) || 0, config.model, selectedTexts); }
      else { res = await optimizeQuery(selectedQueryId, config.model, selectedTexts); }
      setOptimizeResult(res);
    } catch (err) { setError(`Optimization failed: ${err.message}`); }
    finally { setOptimizing(false); }
  }, [analyzeResult, selectedNums, selectedQueryId, config, inputMode, customQueryText, customCredits]);

  const handleBatchAnalyzeAll = useCallback(async (selectedIds) => {
    setBatchPhase('analyzing');
    setBatchProgress({ completed: 0, total: selectedIds.length });
    setBatchRunIds(selectedIds);
    setBatchAnalyzeResults({});
    setBatchSuggestionSelections({});
    setBatchOptimizeResults({});
    setBatchViewQueryId('');
    setError('');

    const results = {};
    const selections = {};
    const counter = { value: 0 };

    const promises = selectedIds.map(async (qid) => {
      try {
        const res = await analyzeQuery(qid, config.model);
        results[qid] = res;
        selections[qid] = new Set(res.parsed_suggestions.map((s) => s.number));
      } catch (err) {
        results[qid] = { error: err.message };
        selections[qid] = new Set();
      }
      counter.value++;
      setBatchAnalyzeResults((prev) => ({ ...prev, [qid]: results[qid] }));
      setBatchProgress({ completed: counter.value, total: selectedIds.length });
    });

    await Promise.allSettled(promises);
    setBatchSuggestionSelections(selections);
    setBatchProgress(null);
    setBatchPhase('review');
    const firstOk = selectedIds.find((id) => !results[id]?.error);
    if (firstOk) setBatchViewQueryId(firstOk);
  }, [config]);

  const handleBatchToggleSuggestion = useCallback((number) => {
    if (!batchViewQueryId) return;
    setBatchSuggestionSelections((prev) => {
      const prevSet = prev[batchViewQueryId] ?? new Set(); const next = new Set(prevSet); next.has(number) ? next.delete(number) : next.add(number);
      return { ...prev, [batchViewQueryId]: next };
    });
  }, [batchViewQueryId]);

  const handleBatchOptimizeAll = useCallback(async () => {
    const successIds = batchRunIds.filter((id) => !batchAnalyzeResults[id]?.error);
    setBatchPhase('optimizing');
    setBatchProgress({ completed: 0, total: successIds.length });
    setBatchOptimizeResults({});
    setError('');

    const results = {};
    const counter = { value: 0 };

    const promises = successIds.map(async (qid) => {
      const sel = batchSuggestionSelections[qid] ?? new Set();
      const analyzeRes = batchAnalyzeResults[qid];
      const selectedTexts = (analyzeRes?.parsed_suggestions ?? [])
        .filter((s) => sel.has(s.number))
        .map((s) => s.full_text);
      if (selectedTexts.length === 0) {
        results[qid] = { error: 'No suggestions selected' };
      } else {
        try {
          const res = await optimizeQuery(qid, config.model, selectedTexts);
          results[qid] = res;
        } catch (err) {
          results[qid] = { error: err.message };
        }
      }
      counter.value++;
      setBatchOptimizeResults((prev) => ({ ...prev, [qid]: results[qid] }));
      setBatchProgress({ completed: counter.value, total: successIds.length });
    });

    await Promise.allSettled(promises);
    setBatchProgress(null);
    setBatchPhase('results');
    if (!batchViewQueryId || results[batchViewQueryId]?.error) {
      const firstOk = successIds.find((id) => !results[id]?.error);
      if (firstOk) setBatchViewQueryId(firstOk);
    }
  }, [batchRunIds, batchAnalyzeResults, batchSuggestionSelections, batchViewQueryId, config]);

  const handleOpenSfModal = useCallback(() => {
    setSfConnectError(''); setShowSfModal(true);
  }, []);

  const handleCloseSfModal = useCallback(() => {
    if (!sfConnecting) setShowSfModal(false);
  }, [sfConnecting]);

  const handleSnowflakeConnect = useCallback(async (credentials) => {
    setSfConnecting(true); setSfConnectError('');
    try {
      const res = await connectSnowflake(credentials);
      setSfConnected(true); setSfAccount(res.account || credentials.account);
      setShowSfModal(false);
    } catch (err) {
      setSfConnectError(err.message);
    } finally {
      setSfConnecting(false);
    }
  }, []);

  const handleSnowflakeDisconnect = useCallback(async () => {
    try { await disconnectSnowflake(); } catch (_) {}
    setSfConnected(false); setSfAccount('');
    setInputMode('excel');
  }, []);

  const handleSnowflakeCheckConnection = useCallback(async () => {
    try {
      const status = await checkSnowflakeStatus();
      if (!status.connected) {
        setSfConnected(false); setSfAccount('');
        setError('Snowflake connection lost. Please reconnect.');
      }
      return status;
    } catch (err) {
      setError(`Connection check failed: ${err.message}`);
      return { connected: false };
    }
  }, []);

  const handleSfQuerySelect = useCallback((row) => {
    setCustomQueryText(row.query_text);
    setCustomCredits(String(row.credits || 0));
    setInputMode('custom');
    setAnalyzeResult(null); setSelectedNums(new Set()); setOptimizeResult(null); setError('');
  }, []);

  const handleBatchReset = useCallback(() => {
    setBatchPhase('idle'); setBatchProgress(null); setBatchRunIds([]); setBatchAnalyzeResults({}); setBatchSuggestionSelections({}); setBatchOptimizeResults({}); setBatchViewQueryId(''); setError('');
  }, []);

  const handleBatchDownload = useCallback(() => {
    const rows = batchRunIds.filter((id) => batchOptimizeResults[id] && !batchOptimizeResults[id]?.error).map((id) => {
      const analyzeRes = batchAnalyzeResults[id]; const optRes = batchOptimizeResults[id]; const sel = batchSuggestionSelections[id] ?? new Set();
      const selectedSuggestions = (analyzeRes?.parsed_suggestions ?? []).filter((s) => sel.has(s.number)).map((s) => s.full_text).join('\n\n');
      return {
        'Query ID': id,
        'Original Query': analyzeRes?.original_query ?? '',
        'Original Credits': optRes?.cost_comparison?.original_credits ?? analyzeRes?.credits ?? 0,
        'Suggestions Applied': sel.size,
        'Applied Suggestions': selectedSuggestions,
        'Optimized Query': optRes?.optimizer_result?.optimized_query ?? '',
        'Explanation': optRes?.optimizer_result?.explanation ?? '',
        'Est. Optimized Credits': optRes?.cost_comparison?.estimated_optimized_credits ?? 0,
        'Credits Saved': optRes?.cost_comparison?.credits_saved ?? 0,
        'Savings %': optRes?.cost_comparison?.savings_percentage ?? 0,
        'Savings Reasoning': optRes?.cost_comparison?.savings_reasoning ?? '',
      };
    });
    const failedRows = batchRunIds.filter((id) => batchOptimizeResults[id]?.error || batchAnalyzeResults[id]?.error).map((id) => ({ 'Query ID': id, 'Error': batchAnalyzeResults[id]?.error || batchOptimizeResults[id]?.error, }));
    const wb = XLSX.utils.book_new();
    const ws = XLSX.utils.json_to_sheet(rows);
    ws['!cols'] = [{ wch: 15 }, { wch: 60 }, { wch: 18 }, { wch: 20 }, { wch: 80 }, { wch: 60 }, { wch: 80 }, { wch: 22 }, { wch: 15 }, { wch: 12 }, { wch: 50 }];
    XLSX.utils.book_append_sheet(wb, ws, 'Optimized Queries');
    if (failedRows.length > 0) {
      XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(failedRows), 'Errors');
    }
    XLSX.writeFile(wb, `batch_optimization_${new Date().toISOString().slice(0, 10)}.xlsx`);
  }, [batchRunIds, batchAnalyzeResults, batchSuggestionSelections, batchOptimizeResults]);

  const isBatchActive = batchPhase === 'review' || batchPhase === 'optimizing' || batchPhase === 'results';

  const panelAnalyzeResult = isBatchActive && batchViewQueryId && batchAnalyzeResults[batchViewQueryId]?.error
    ? null
    : isBatchActive && batchViewQueryId
    ? batchAnalyzeResults[batchViewQueryId]
    : (!isBatchActive ? analyzeResult : null);

  const panelSelectedNums = isBatchActive && batchViewQueryId
    ? (batchSuggestionSelections[batchViewQueryId] ?? new Set())
    : selectedNums;

  const panelToggle = isBatchActive && batchViewQueryId
    ? handleBatchToggleSuggestion
    : handleToggleSuggestion;

  const panelOptimizeResult = isBatchActive && batchViewQueryId && !batchOptimizeResults[batchViewQueryId]?.error
    ? batchOptimizeResults[batchViewQueryId]
    : (!isBatchActive ? optimizeResult : null);

  const panelQueryDetail = (() => {
    if (isBatchActive && batchViewQueryId) {
      const ar = batchAnalyzeResults[batchViewQueryId];
      if (ar && !ar.error) {
        return { query_id: batchViewQueryId, query_text: ar.original_query, credits: ar.credits };
      }
      return null;
    }
    if (inputMode === 'custom' && customQueryText.trim()) {
      return { query_id: 'Custom', query_text: customQueryText, credits: parseFloat(customCredits) || 0 };
    }
    return queryDetail;
  })();

  const hideSuggestApplyBtn = batchPhase === 'review' || batchPhase === 'optimizing'
    || (!isBatchActive && !!optimizeResult);
  const canAnalyze = !!config.model && !analyzing && !optimizing && inputMode !== 'snowflake'
    && (inputMode !== 'excel' || !!selectedQueryId);
  const canOptimize = panelAnalyzeResult && panelSelectedNums.size > 0 && !analyzing && !optimizing;

  return (
    <div className="app">
      {showSfModal && (
        <SnowflakeConnectModal
          onConnect={handleSnowflakeConnect}
          onClose={handleCloseSfModal}
          connecting={sfConnecting}
          error={sfConnectError}
        />
      )}

      <header className="app-header">
        <h1>
          <span className="logo-icon">&#x26A1;</span>
          Query Optimization System
          <span className="subtitle">Snowflake SQL - LLM-powered</span>
        </h1>
      </header>

      <ConfigPanel
        config={config}
        onConfigChange={handleConfigChange}
        queryIds={queryIds}
        selectedQueryId={selectedQueryId}
        onQueryChange={setSelectedQueryId}
        onAnalyze={handleAnalyze}
        analyzing={analyzing}
        canAnalyze={canAnalyze}
        onUpload={handleUpload}
        uploading={uploading}
        uploadedFilename={uploadedFilename}
        inputMode={inputMode}
        onInputModeChange={handleInputModeChange}
        customQueryText={customQueryText}
        onCustomQueryTextChange={setCustomQueryText}
        customCredits={customCredits}
        onCustomCreditsChange={setCustomCredits}
        sfConnected={sfConnected}
        sfAccount={sfAccount}
        onOpenSnowflakeModal={handleOpenSfModal}
      />

      {inputMode === 'snowflake' && sfConnected && (
        <SnowflakeDashboard
          account={sfAccount}
          onSelectQuery={handleSfQuerySelect}
          onDisconnect={handleSnowflakeDisconnect}
          onCheckConnection={handleSnowflakeCheckConnection}
        />
      )}

      {inputMode === 'excel' && (
        <BatchPanel
          queryIds={queryIds}
          batchPhase={batchPhase}
          batchProgress={batchProgress}
          batchAnalyzeResults={batchAnalyzeResults}
          batchSuggestionSelections={batchSuggestionSelections}
          batchOptimizeResults={batchOptimizeResults}
          batchViewQueryId={batchViewQueryId}
          onBatchViewChange={setBatchViewQueryId}
          batchRunIds={batchRunIds}
          onAnalyzeAll={handleBatchAnalyzeAll}
          onOptimizeAll={handleBatchOptimizeAll}
          onDownload={handleBatchDownload}
          onReset={handleBatchReset}
          canRun={!!config.model}
          selectedQueryId={selectedQueryId}
          onSelectQuery={setSelectedQueryId}
        />
      )}

      {error && <div className="error-box">&#x26A0; {error}</div>}

      <div className="query-row">
        <OriginalQueryPanel queryDetail={panelQueryDetail} />
        <SuggestionsPanel
          analyzeResult={panelAnalyzeResult}
          analyzing={analyzing || batchPhase === 'analyzing'}
          selectedNums={panelSelectedNums}
          onToggle={panelToggle}
          onOptimize={handleOptimize}
          optimizing={optimizing || batchPhase === 'optimizing'}
          canOptimize={canOptimize}
          hideOptimizeButton={hideSuggestApplyBtn}
        />
      </div>

      <OptimizedQueryPanel
        optimizerResult={panelOptimizeResult?.optimizer_result ?? null}
        loading={optimizing || batchPhase === 'optimizing'}
        onRegenerate={isBatchActive ? undefined : handleOptimize}
        onCorrectOutput={() => {}}
      />

      {panelOptimizeResult && (
        <CostComparison costComparison={panelOptimizeResult.cost_comparison} />
      )}

      {panelOptimizeResult && (
        <CostBreakdown
          advisorUsage={panelOptimizeResult.advisor_usage}
          optimizerUsage={panelOptimizeResult.optimizer_usage}
          totalCost={panelOptimizeResult.total_cost}
        />
      )}

      {panelOptimizeResult && (
        <TokenBadge usage={panelOptimizeResult.advisor_usage} />
      )}
    </div>
  );
}