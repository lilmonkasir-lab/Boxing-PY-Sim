import React from 'react';
import { Shield, Smartphone, Monitor, Terminal, Wifi, BatteryCharging } from 'lucide-react';

export default function Navbar({ isMobileFrame, setIsMobileFrame, showTerminal, setShowTerminal, logsCount, activeTarget, setActiveTarget }) {
  const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  return (
    <header className="bg-slate-900/90 backdrop-blur-md border-b border-slate-800 sticky top-0 z-40">
      {/* Mobile Simulated Top Status Bar */}
      {isMobileFrame && (
        <div className="bg-slate-950 px-4 py-1 text-[11px] font-mono text-slate-400 flex justify-between items-center border-b border-slate-900">
          <span>{currentTime}</span>
          <div className="w-16 h-3 bg-slate-900 rounded-full border border-slate-800 flex items-center justify-center">
            <div className="w-2 h-2 bg-slate-700 rounded-full mr-1"></div>
            <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-ping"></div>
          </div>
          <div className="flex items-center space-x-2">
            <Wifi className="w-3 h-3 text-emerald-400" />
            <span className="text-[10px] text-emerald-400 font-bold">5G / SEC</span>
            <BatteryCharging className="w-3.5 h-3.5 text-emerald-400" />
          </div>
        </div>
      )}

      {/* App Header */}
      <div className="px-3 py-2.5 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="p-1.5 bg-gradient-to-br from-emerald-500 to-cyan-600 rounded-lg shadow-lg shadow-emerald-500/20">
            <Shield className="w-5 h-5 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <div className="flex items-center space-x-1.5">
              <span className="font-extrabold text-sm tracking-wider text-slate-100 bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                NEXUS<span className="text-emerald-400 font-mono">SEC</span>
              </span>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                PRO v2.0
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400 -mt-0.5">Mobile Pentest Toolkit</p>
          </div>
        </div>

        {/* Header Controls */}
        <div className="flex items-center space-x-1.5">
          {/* Target input quick view */}
          <div className="hidden sm:flex items-center bg-slate-950 border border-slate-800 rounded-md px-2 py-1 text-xs">
            <span className="text-slate-500 mr-1.5 font-mono">Target:</span>
            <input
              type="text"
              value={activeTarget}
              onChange={(e) => setActiveTarget(e.target.value)}
              placeholder="e.g. target.com"
              className="bg-transparent text-emerald-400 font-mono w-28 focus:outline-none focus:w-36 transition-all text-xs"
            />
          </div>

          {/* Terminal Toggle Button */}
          <button
            onClick={() => setShowTerminal(!showTerminal)}
            className={`relative p-2 rounded-lg border text-xs font-mono flex items-center space-x-1 transition-all ${
              showTerminal
                ? 'bg-emerald-500/20 border-emerald-500 text-emerald-400 shadow-sm shadow-emerald-500/20'
                : 'bg-slate-800/80 border-slate-700 text-slate-300 hover:bg-slate-800'
            }`}
            title="Toggle Live Console Logs"
          >
            <Terminal className="w-4 h-4 text-emerald-400" />
            <span className="hidden xs:inline">Console</span>
            {logsCount > 0 && (
              <span className="bg-emerald-500 text-slate-950 font-bold px-1.5 py-0.2 rounded-full text-[10px]">
                {logsCount}
              </span>
            )}
          </button>

          {/* Device Frame Viewport Toggle */}
          <button
            onClick={() => setIsMobileFrame(!isMobileFrame)}
            className="p-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg transition-all"
            title={isMobileFrame ? 'Switch to Full Screen View' : 'Switch to Mobile Frame Mode'}
          >
            {isMobileFrame ? (
              <Monitor className="w-4 h-4 text-cyan-400" />
            ) : (
              <Smartphone className="w-4 h-4 text-emerald-400" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
