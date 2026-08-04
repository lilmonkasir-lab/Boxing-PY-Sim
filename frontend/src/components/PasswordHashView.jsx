import React, { useState } from 'react';
import { KeyRound, Hash, ShieldCheck, Zap, Copy, Check, Search, AlertCircle, RefreshCw } from 'lucide-react';

export default function PasswordHashView({ addLog }) {
  const [subTab, setSubTab] = useState('generate'); // generate | identify | crack | entropy

  // Hash Generator State
  const [textInput, setTextInputs] = useState('AdminPass123!');
  const [saltInput, setSaltInput] = useState('');
  const [secretInput, setSecretInput] = useState('');
  const [hashResult, setHashResult] = useState(null);
  const [loadingGen, setLoadingGen] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  // Hash Identifier State
  const [identifyHash, setIdentifyHash] = useState('5f4dcc3b5aa765d61d8327deb882cf99');
  const [identifyResult, setIdentifyResult] = useState(null);
  const [loadingIdentify, setLoadingIdentify] = useState(false);

  // Hash Cracker Lookup State
  const [crackHash, setCrackHash] = useState('5f4dcc3b5aa765d61d8327deb882cf99');
  const [customWordlist, setCustomWordlist] = useState('');
  const [crackResult, setCrackResult] = useState(null);
  const [loadingCrack, setLoadingCrack] = useState(false);

  // Password Entropy State
  const [passwordToAnalyze, setPasswordToAnalyze] = useState('P@ssw0rd2026!');
  const [entropyResult, setEntropyResult] = useState(null);
  const [loadingEntropy, setLoadingEntropy] = useState(false);

  // 1. Generate Hashes
  const handleGenerateHashes = async () => {
    if (!textInput) return;
    setLoadingGen(true);
    try {
      const res = await fetch('/api/hash/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textInput, salt: saltInput, secret: secretInput })
      });
      const data = await res.json();
      setHashResult(data);
      addLog('SUCCESS', 'Generated Hashes', { input: textInput, time_ms: data.time_ms });
    } catch (e) {
      addLog('ERROR', 'Failed to generate hashes', { error: e.message });
    } finally {
      setLoadingGen(false);
    }
  };

  // 2. Identify Hash Format
  const handleIdentifyHash = async () => {
    if (!identifyHash) return;
    setLoadingIdentify(true);
    try {
      const res = await fetch('/api/hash/identify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hash: identifyHash })
      });
      const data = await res.json();
      setIdentifyResult(data);
      addLog('SUCCESS', `Identified Hash Structure (${data.length} chars)`, data);
    } catch (e) {
      addLog('ERROR', 'Hash Identification Failed', { error: e.message });
    } finally {
      setLoadingIdentify(false);
    }
  };

  // 3. Dictionary Crack Search
  const handleCrackLookup = async () => {
    if (!crackHash) return;
    setLoadingCrack(true);
    try {
      const wordlistArr = customWordlist.split('\n').map(w => w.trim()).filter(Boolean);
      const res = await fetch('/api/hash/crack_lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hash: crackHash, wordlist: wordlistArr })
      });
      const data = await res.json();
      setCrackResult(data);
      addLog(data.found ? 'SUCCESS' : 'INFO', `Hash Dictionary Lookup (${crackHash.slice(0, 8)}...)`, data);
    } catch (e) {
      addLog('ERROR', 'Crack Lookup Failed', { error: e.message });
    } finally {
      setLoadingCrack(false);
    }
  };

  // 4. Password Strength Analyzer
  const handleAnalyzePassword = async () => {
    if (!passwordToAnalyze) return;
    setLoadingEntropy(true);
    try {
      const res = await fetch('/api/password/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: passwordToAnalyze })
      });
      const data = await res.json();
      setEntropyResult(data);
      addLog('SUCCESS', `Password Entropy Analysis (${data.entropy_bits} bits)`, data);
    } catch (e) {
      addLog('ERROR', 'Password Analysis Failed', { error: e.message });
    } finally {
      setLoadingEntropy(false);
    }
  };

  const copyToClipboard = (text, keyName) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(keyName);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-4 pb-20">
      {/* Module Title */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <KeyRound className="w-5 h-5 text-amber-400" />
          <h1 className="font-extrabold text-base text-slate-100">Password & Hash Tools</h1>
        </div>
      </div>

      {/* Sub Tabs Navigation */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'generate', label: 'Generator' },
          { id: 'identify', label: 'Hash ID' },
          { id: 'crack', label: 'Wordlist Lookup' },
          { id: 'entropy', label: 'Entropy & Crack' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
              subTab === tab.id
                ? 'bg-amber-500/20 text-amber-400 font-bold border border-amber-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUBTAB 1: HASH GENERATOR */}
      {subTab === 'generate' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Plaintext Input:</label>
              <input
                type="text"
                value={textInput}
                onChange={(e) => setTextInputs(e.target.value)}
                placeholder="Enter string to hash..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Salt (Optional):</label>
                <input
                  type="text"
                  value={saltInput}
                  onChange={(e) => setSaltInput(e.target.value)}
                  placeholder="e.g. s@lt2026"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2 font-mono text-xs focus:outline-none"
                />
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Secret Key (HMAC):</label>
                <input
                  type="text"
                  value={secretInput}
                  onChange={(e) => setSecretInput(e.target.value)}
                  placeholder="e.g. hmac-secret-key"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2 font-mono text-xs focus:outline-none"
                />
              </div>
            </div>

            <button
              onClick={handleGenerateHashes}
              disabled={loadingGen}
              className="w-full py-2 bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1 shadow-lg shadow-amber-500/10"
            >
              {loadingGen ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Hash className="w-4 h-4" />}
              <span>Calculate Hashes</span>
            </button>
          </div>

          {/* Hash Results Display */}
          {hashResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2">
              <div className="flex justify-between items-center text-xs font-mono text-slate-400 mb-2 border-b border-slate-800 pb-1.5">
                <span>Calculated Hashes ({hashResult.time_ms} ms)</span>
                <span className="text-[10px] text-amber-400">Salt: {hashResult.salt || 'None'}</span>
              </div>

              {Object.entries(hashResult.hashes).map(([type, hashVal]) => (
                <div key={type} className="bg-slate-950 p-2 rounded border border-slate-800/80 font-mono text-xs flex items-center justify-between">
                  <div className="truncate mr-2">
                    <span className="text-amber-400 font-bold text-[10px] block">{type}</span>
                    <span className="text-slate-300 text-[11px] truncate select-all">{hashVal}</span>
                  </div>
                  <button
                    onClick={() => copyToClipboard(hashVal, type)}
                    className="p-1.5 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded shrink-0"
                  >
                    {copiedKey === type ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: HASH IDENTIFIER */}
      {subTab === 'identify' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Hash String to Identify:</label>
              <textarea
                rows={2}
                value={identifyHash}
                onChange={(e) => setIdentifyHash(e.target.value)}
                placeholder="Paste hash e.g. 5f4dcc3b5aa765d61d8327deb882cf99..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleIdentifyHash}
              disabled={loadingIdentify}
              className="w-full py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingIdentify ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              <span>Identify Hash Type</span>
            </button>
          </div>

          {identifyResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-slate-800 pb-1.5">
                <span>Matches ({identifyResult.matched_count})</span>
                <span>Length: {identifyResult.length} chars</span>
              </div>

              {identifyResult.matches.map((match, i) => (
                <div key={i} className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-xs space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-amber-400 font-bold">{match.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      Confidence: {match.confidence}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-400 pt-1">
                    <div>Hashcat Mode: <code className="text-emerald-400 font-bold">-m {match.hashcat_mode}</code></div>
                    <div>John Format: <code className="text-cyan-400 font-bold">--format={match.john_format}</code></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: DICTIONARY CRACK LOOKUP */}
      {subTab === 'crack' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Hash (MD5 / SHA1 / SHA256):</label>
              <input
                type="text"
                value={crackHash}
                onChange={(e) => setCrackHash(e.target.value)}
                placeholder="e.g. 5f4dcc3b5aa765d61d8327deb882cf99"
                className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Custom Wordlist (One word per line):</label>
              <textarea
                rows={3}
                value={customWordlist}
                onChange={(e) => setCustomWordlist(e.target.value)}
                placeholder="Optional extra words e.g.&#10;Company2026!&#10;SuperSecret123"
                className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleCrackLookup}
              disabled={loadingCrack}
              className="w-full py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingCrack ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
              <span>Test Wordlist Dictionary</span>
            </button>
          </div>

          {crackResult && (
            <div className={`rounded-xl p-3.5 border font-mono text-xs space-y-2 ${
              crackResult.found ? 'bg-emerald-950/20 border-emerald-800/80 text-emerald-300' : 'bg-slate-900 border-slate-800 text-slate-300'
            }`}>
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-1.5">
                <span className="font-bold">Dictionary Result:</span>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${crackResult.found ? 'bg-emerald-500 text-slate-950' : 'bg-slate-800 text-slate-400'}`}>
                  {crackResult.found ? 'MATCH FOUND' : 'NOT FOUND'}
                </span>
              </div>

              {crackResult.found ? (
                <div className="space-y-1 pt-1">
                  <div>Cracked Plaintext Password: <strong className="text-emerald-400 text-sm">{crackResult.password}</strong></div>
                  <div className="text-[11px] text-slate-400">Hash Algorithm: {crackResult.hash_type}</div>
                </div>
              ) : (
                <p className="text-xs text-slate-400">{crackResult.message}</p>
              )}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 4: PASSWORD ENTROPY & STRENGTH */}
      {subTab === 'entropy' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Password to Analyze:</label>
              <input
                type="text"
                value={passwordToAnalyze}
                onChange={(e) => setPasswordToAnalyze(e.target.value)}
                placeholder="Enter password to evaluate..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleAnalyzePassword}
              disabled={loadingEntropy}
              className="w-full py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingEntropy ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
              <span>Analyze Entropy & Crack Speed</span>
            </button>
          </div>

          {entropyResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 font-mono text-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-slate-400 text-[10px] block">Strength Score</span>
                  <span className="font-extrabold text-sm text-amber-400">{entropyResult.rating} ({entropyResult.score}/100)</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 text-[10px] block">Shannon Entropy</span>
                  <span className="font-bold text-xs text-cyan-400">{entropyResult.entropy_bits} Bits</span>
                </div>
              </div>

              {/* Character set breakdown */}
              <div className="grid grid-cols-4 gap-1 text-[10px] text-center">
                <div className={`p-1 rounded ${entropyResult.flags.has_lower ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-950 text-slate-600'}`}>a-z</div>
                <div className={`p-1 rounded ${entropyResult.flags.has_upper ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-950 text-slate-600'}`}>A-Z</div>
                <div className={`p-1 rounded ${entropyResult.flags.has_digit ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-950 text-slate-600'}`}>0-9</div>
                <div className={`p-1 rounded ${entropyResult.flags.has_symbol ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-950 text-slate-600'}`}>!@#</div>
              </div>

              {/* Crack speed estimates */}
              <div className="bg-slate-950 p-2.5 rounded border border-slate-800 space-y-1 text-[11px]">
                <div className="text-slate-400 font-bold mb-1">Estimated Brute-Force Crack Times:</div>
                <div className="flex justify-between">
                  <span>100 GH/s GPU Array:</span>
                  <span className="text-amber-400 font-bold">{entropyResult.crack_time_rig}</span>
                </div>
                <div className="flex justify-between">
                  <span>1 GH/s Single GPU:</span>
                  <span className="text-cyan-400 font-bold">{entropyResult.crack_time_single_gpu}</span>
                </div>
              </div>

              {/* Warnings */}
              {entropyResult.warnings.length > 0 && (
                <div className="bg-red-950/20 border border-red-800/40 p-2 rounded text-red-300 text-[11px] space-y-1">
                  <div className="font-bold flex items-center">
                    <AlertCircle className="w-3.5 h-3.5 mr-1" />
                    Security Recommendations:
                  </div>
                  {entropyResult.warnings.map((w, i) => (
                    <div key={i}>• {w}</div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
