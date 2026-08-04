import React, { useState } from 'react';
import { Search, UserCheck, ExternalLink, RefreshCw, FileSearch } from 'lucide-react';

export default function OsintView({ activeTarget, addLog }) {
  const [subTab, setSubTab] = useState('username'); // username | dorks

  // Username State
  const [usernameInput, setUsernameInput] = useState('admin');
  const [usernameResult, setUsernameResult] = useState(null);
  const [loadingUser, setLoadingUser] = useState(false);

  // Dorks State
  const [dorkDomain, setDorkDomain] = useState(activeTarget || 'example.com');
  const [dorkResult, setDorkResult] = useState(null);
  const [loadingDork, setLoadingDork] = useState(false);

  // 1. Username Footprint
  const handleSearchUsername = async () => {
    if (!usernameInput) return;
    setLoadingUser(true);
    try {
      const res = await fetch('/api/osint/username', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: usernameInput })
      });
      const data = await res.json();
      setUsernameResult(data);
      addLog('SUCCESS', `OSINT Username Footprint Query (${usernameInput})`, data);
    } catch (e) {
      addLog('ERROR', 'Username Search Failed', { error: e.message });
    } finally {
      setLoadingUser(false);
    }
  };

  // 2. Google Dorks
  const handleGenerateDorks = async () => {
    if (!dorkDomain) return;
    setLoadingDork(true);
    try {
      const res = await fetch('/api/osint/dorks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: dorkDomain })
      });
      const data = await res.json();
      setDorkResult(data);
      addLog('SUCCESS', `Generated Google Search Dorks for ${dorkDomain}`, data);
    } catch (e) {
      addLog('ERROR', 'Dorks Generation Failed', { error: e.message });
    } finally {
      setLoadingDork(false);
    }
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center space-x-2">
        <Search className="w-5 h-5 text-rose-400" />
        <h1 className="font-extrabold text-base text-slate-100">OSINT & Domain Intelligence</h1>
      </div>

      {/* Sub Tabs */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'username', label: 'Username Footprint' },
          { id: 'dorks', label: 'Google Dorks Generator' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSubTab(tab.id)}
            className={`px-3 py-1.5 rounded-lg transition-all shrink-0 ${
              subTab === tab.id
                ? 'bg-rose-500/20 text-rose-400 font-bold border border-rose-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* SUBTAB 1: USERNAME FOOTPRINT */}
      {subTab === 'username' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Handle / Username:</label>
              <input
                type="text"
                value={usernameInput}
                onChange={(e) => setUsernameInput(e.target.value)}
                placeholder="e.g. cyber_hunter"
                className="w-full bg-slate-950 border border-slate-800 focus:border-rose-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleSearchUsername}
              disabled={loadingUser}
              className="w-full py-2 bg-gradient-to-r from-rose-500 to-pink-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingUser ? <RefreshCw className="w-4 h-4 animate-spin" /> : <UserCheck className="w-4 h-4" />}
              <span>Search Handle Across Platforms</span>
            </button>
          </div>

          {usernameResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="text-slate-400 text-xs border-b border-slate-800 pb-1.5">
                Footprint Platforms for <strong className="text-rose-400">@{usernameResult.username}</strong>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {usernameResult.platforms.map((p, idx) => (
                  <a
                    key={idx}
                    href={p.url}
                    target="_blank"
                    rel="noreferrer"
                    className="bg-slate-950 p-2.5 rounded border border-slate-800 hover:border-rose-500/50 transition-all flex items-center justify-between text-xs group"
                  >
                    <div>
                      <span className="font-bold text-slate-200 block">{p.platform}</span>
                      <span className="text-[10px] text-slate-500 truncate block max-w-[180px]">{p.url}</span>
                    </div>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-500 group-hover:text-rose-400 shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: GOOGLE DORKS GENERATOR */}
      {subTab === 'dorks' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Domain Name:</label>
              <input
                type="text"
                value={dorkDomain}
                onChange={(e) => setDorkDomain(e.target.value)}
                placeholder="example.com"
                className="w-full bg-slate-950 border border-slate-800 focus:border-rose-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleGenerateDorks}
              disabled={loadingDork}
              className="w-full py-2 bg-gradient-to-r from-rose-500 to-pink-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingDork ? <RefreshCw className="w-4 h-4 animate-spin" /> : <FileSearch className="w-4 h-4" />}
              <span>Generate Google Dorks</span>
            </button>
          </div>

          {dorkResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="text-slate-400 text-xs border-b border-slate-800 pb-1.5">
                Google Search Dorks for <strong className="text-rose-400">{dorkResult.target_domain}</strong>
              </div>

              <div className="space-y-2">
                {dorkResult.dorks.map((item, idx) => (
                  <div key={idx} className="bg-slate-950 p-2.5 rounded border border-slate-800 space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="text-rose-400 font-bold text-[11px]">{item.category}</span>
                      <a
                        href={item.google_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[10px] text-cyan-400 hover:underline flex items-center space-x-1"
                      >
                        <span>Search Google</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    <code className="bg-slate-900 p-1.5 rounded text-emerald-400 text-[11px] block truncate border border-slate-800/80">
                      {item.query}
                    </code>
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
