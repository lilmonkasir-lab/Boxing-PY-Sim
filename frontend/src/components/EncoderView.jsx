import React, { useState } from 'react';
import { Binary, Key, RefreshCw, Copy, Check, FileCode2, ShieldAlert } from 'lucide-react';

export default function EncoderView({ addLog }) {
  const [subTab, setSubTab] = useState('converter'); // converter | jwt | xor

  // Converter State
  const [inputText, setInputText] = useState('NexusSec Mobile Pentest');
  const [convFormat, setConvFormat] = useState('base64');
  const [convMode, setConvMode] = useState('encode');
  const [convOutput, setConvOutput] = useState('');
  const [loadingConv, setLoadingConv] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  // JWT State
  const [jwtInput, setJwtInput] = useState('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkFsZXggSHVudGVyIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjI1Mjk2MDAwMDB9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c');
  const [jwtResult, setJwtResult] = useState(null);
  const [loadingJwt, setLoadingJwt] = useState(false);

  // XOR Cipher State
  const [xorText, setXorText] = useState('SecretPayload123');
  const [xorKey, setXorKey] = useState('KEY');
  const [xorOutput, setXorOutput] = useState('');

  // 1. Convert Format
  const handleConvert = async (modeOverride) => {
    const activeMode = modeOverride || convMode;
    if (!inputText) return;
    setLoadingConv(true);
    try {
      const res = await fetch('/api/encoder/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText, format: convFormat, mode: activeMode })
      });
      const data = await res.json();
      setConvOutput(data.output || data.error);
      addLog('SUCCESS', `Converted (${convFormat.toUpperCase()} ${activeMode})`, data);
    } catch (e) {
      addLog('ERROR', 'Conversion Failed', { error: e.message });
    } finally {
      setLoadingConv(false);
    }
  };

  // 2. Decode JWT
  const handleDecodeJwt = async () => {
    if (!jwtInput) return;
    setLoadingJwt(true);
    try {
      const res = await fetch('/api/encoder/jwt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: jwtInput })
      });
      const data = await res.json();
      setJwtResult(data);
      addLog('SUCCESS', `Parsed JWT Token (Exp: ${data.exp_date || 'None'})`, data);
    } catch (e) {
      addLog('ERROR', 'JWT Parsing Failed', { error: e.message });
    } finally {
      setLoadingJwt(false);
    }
  };

  // 3. XOR Cipher
  const handleXorCipher = () => {
    if (!xorText || !xorKey) return;
    let res = '';
    for (let i = 0; i < xorText.length; i++) {
      const charCode = xorText.charCodeAt(i) ^ xorKey.charCodeAt(i % xorKey.length);
      res += String.fromCharCode(charCode);
    }
    const hexRes = Array.from(res).map(c => c.charCodeAt(0).toString(16).padStart(2, '0')).join('');
    setXorOutput(`Hex Result: ${hexRes}`);
    addLog('SUCCESS', 'XOR Encryption Executed', { text: xorText, key: xorKey, hex: hexRes });
  };

  const copyText = (str, k) => {
    navigator.clipboard.writeText(str);
    setCopiedKey(k);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center space-x-2">
        <Binary className="w-5 h-5 text-purple-400" />
        <h1 className="font-extrabold text-base text-slate-100">Encoder / Decoder & JWT</h1>
      </div>

      {/* Sub Tab Bar */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'converter', label: 'Multi-Format' },
          { id: 'jwt', label: 'JWT Token Inspector' },
          { id: 'xor', label: 'XOR Cipher' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
              subTab === tab.id
                ? 'bg-purple-500/20 text-purple-400 font-bold border border-purple-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUBTAB 1: MULTI-FORMAT CONVERTER */}
      {subTab === 'converter' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Input Text:</label>
              <textarea
                rows={3}
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Enter string to convert..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[10px] font-mono text-slate-400 block mb-1">Target Format:</label>
              <select
                value={convFormat}
                onChange={(e) => setConvFormat(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 font-mono text-xs focus:outline-none"
              >
                <option value="base64">Base64 Encoding</option>
                <option value="hex">Hexadecimal (0x...)</option>
                <option value="url">URL Percent Encoding (%20...)</option>
                <option value="html">HTML Entities (&#...)</option>
                <option value="binary">Binary (01010101)</option>
                <option value="rot13">ROT13 Cipher</option>
                <option value="reverse">Reverse String</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2 font-mono text-xs">
              <button
                onClick={() => { setConvMode('encode'); handleConvert('encode'); }}
                disabled={loadingConv}
                className="py-2 bg-purple-500 hover:bg-purple-600 text-slate-950 font-bold rounded-lg flex items-center justify-center space-x-1"
              >
                <span>ENCODE</span>
              </button>
              <button
                onClick={() => { setConvMode('decode'); handleConvert('decode'); }}
                disabled={loadingConv}
                className="py-2 bg-slate-800 hover:bg-slate-700 text-purple-400 border border-purple-500/30 font-bold rounded-lg flex items-center justify-center space-x-1"
              >
                <span>DECODE</span>
              </button>
            </div>
          </div>

          {convOutput && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="flex justify-between items-center text-slate-400 text-xs border-b border-slate-800 pb-1.5">
                <span>Output ({convFormat.toUpperCase()})</span>
                <button
                  onClick={() => copyText(convOutput, 'conv')}
                  className="text-[10px] text-purple-400 hover:underline flex items-center space-x-1"
                >
                  {copiedKey === 'conv' ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedKey === 'conv' ? 'Copied' : 'Copy Result'}</span>
                </button>
              </div>

              <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-emerald-400 select-all break-all whitespace-pre-wrap">
                {convOutput}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: JWT TOKEN INSPECTOR */}
      {subTab === 'jwt' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">JWT Bearer Token String:</label>
              <textarea
                rows={3}
                value={jwtInput}
                onChange={(e) => setJwtInput(e.target.value)}
                placeholder="eyJhbGciOiJIUzI1Ni..."
                className="w-full bg-slate-950 border border-slate-800 focus:border-purple-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleDecodeJwt}
              disabled={loadingJwt}
              className="w-full py-2 bg-purple-500 hover:bg-purple-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingJwt ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileCode2 className="w-4 h-4" />}
              <span>Inspect JWT Header & Claims</span>
            </button>
          </div>

          {jwtResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 font-mono text-xs space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-slate-400 text-[10px] block">Expiration Status</span>
                  <span className={`font-bold text-xs ${jwtResult.is_expired ? 'text-red-400' : 'text-emerald-400'}`}>
                    {jwtResult.is_expired ? 'EXPIRED TOKEN' : 'VALID / ACTIVE TOKEN'}
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 text-[10px] block">Expiration Date</span>
                  <span className="text-cyan-400 text-[11px]">{jwtResult.exp_date || 'No Expiry Set'}</span>
                </div>
              </div>

              <div>
                <span className="text-purple-400 font-bold block mb-1 text-[11px]">Header JSON:</span>
                <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-slate-300 text-[11px] overflow-x-auto">
                  {JSON.stringify(jwtResult.header, null, 2)}
                </pre>
              </div>

              <div>
                <span className="text-purple-400 font-bold block mb-1 text-[11px]">Payload Claims JSON:</span>
                <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-emerald-400 text-[11px] overflow-x-auto">
                  {JSON.stringify(jwtResult.payload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: XOR CIPHER */}
      {subTab === 'xor' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3 font-mono text-xs">
            <div>
              <label className="text-slate-400 block mb-1">Text String:</label>
              <input
                type="text"
                value={xorText}
                onChange={(e) => setXorText(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-slate-400 block mb-1">XOR Key:</label>
              <input
                type="text"
                value={xorKey}
                onChange={(e) => setXorKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 focus:outline-none"
              />
            </div>
            <button
              onClick={handleXorCipher}
              className="w-full py-2 bg-gradient-to-r from-purple-500 to-indigo-500 text-slate-950 font-bold rounded"
            >
              Execute XOR Calculation
            </button>
          </div>

          {xorOutput && (
            <div className="bg-slate-900 p-3 rounded-xl border border-slate-800 font-mono text-xs text-emerald-400 select-all">
              {xorOutput}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
