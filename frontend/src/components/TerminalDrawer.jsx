import React, { useState } from 'react';
import { Terminal as TerminalIcon, X, Trash2, Copy, Check, ChevronDown, ChevronUp } from 'lucide-react';

export default function TerminalDrawer({ logs, clearLogs, isOpen, setIsOpen }) {
  const [copied, setCopied] = useState(false);
  const [expandedLog, setExpandedLog] = useState(null);

  if (!isOpen) return null;

  const copyAllLogs = () => {
    const text = logs.map(l => `[${l.time}] [${l.type}] ${l.title}: ${JSON.stringify(l.data, null, 2)}`).join('\n\n');
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed bottom-14 left-0 right-0 z-50 max-w-5xl mx-auto px-2">
      <div className="bg-slate-950/95 border border-slate-800 rounded-t-xl shadow-2xl backdrop-blur-xl overflow-hidden flex flex-col max-h-[360px] animate-in slide-in-from-bottom duration-200">
        {/* Terminal Header */}
        <div className="bg-slate-900 px-3 py-2 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <TerminalIcon className="w-4 h-4 text-emerald-400" />
            <span className="font-mono text-xs font-bold text-slate-200">Live Pentest Console</span>
            <span className="text-[10px] bg-slate-800 text-slate-400 font-mono px-2 py-0.5 rounded-full border border-slate-700">
              {logs.length} events
            </span>
          </div>

          <div className="flex items-center space-x-2">
            {logs.length > 0 && (
              <>
                <button
                  onClick={copyAllLogs}
                  className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-200 rounded text-xs flex items-center space-x-1 font-mono"
                  title="Copy All Console Logs"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span className="hidden xs:inline">Copy Logs</span>
                </button>
                <button
                  onClick={clearLogs}
                  className="p-1 hover:bg-slate-800 text-slate-400 hover:text-red-400 rounded text-xs"
                  title="Clear Console"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </>
            )}
            <button
              onClick={() => setIsOpen(false)}
              className="p-1 hover:bg-slate-800 text-slate-400 hover:text-slate-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Log Body */}
        <div className="p-3 font-mono text-xs overflow-y-auto space-y-2 flex-1 scrollbar-thin">
          {logs.length === 0 ? (
            <div className="text-slate-600 text-center py-8 text-xs font-mono italic">
              &gt; Console ready. Execute any security tool to stream live logs & JSON output...
            </div>
          ) : (
            logs.map((log, index) => {
              const isErr = log.type === 'ERROR';
              const isSucc = log.type === 'SUCCESS';
              const isExp = expandedLog === index;

              return (
                <div
                  key={index}
                  className={`border rounded p-2 transition-all ${
                    isErr
                      ? 'bg-red-950/20 border-red-800/40 text-red-300'
                      : isSucc
                      ? 'bg-slate-900/80 border-slate-800 text-slate-300'
                      : 'bg-slate-900/50 border-slate-800/80 text-slate-400'
                  }`}
                >
                  <div
                    className="flex items-center justify-between cursor-pointer select-none"
                    onClick={() => setExpandedLog(isExp ? null : index)}
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <span className="text-[10px] text-slate-500 font-mono">[{log.time}]</span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                          isErr
                            ? 'bg-red-500/20 text-red-400'
                            : isSucc
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-cyan-500/20 text-cyan-400'
                        }`}
                      >
                        {log.type}
                      </span>
                      <span className="font-semibold text-slate-200 text-xs truncate">{log.title}</span>
                    </div>

                    <div className="flex items-center space-x-1">
                      {isExp ? <ChevronUp className="w-3.5 h-3.5 text-slate-500" /> : <ChevronDown className="w-3.5 h-3.5 text-slate-500" />}
                    </div>
                  </div>

                  {/* Expanded JSON Data */}
                  {isExp && (
                    <div className="mt-2 pt-2 border-t border-slate-800/80 text-[11px] overflow-x-auto">
                      <pre className="text-emerald-400/90 whitespace-pre-wrap bg-slate-950 p-2 rounded border border-slate-900">
                        {JSON.stringify(log.data, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
