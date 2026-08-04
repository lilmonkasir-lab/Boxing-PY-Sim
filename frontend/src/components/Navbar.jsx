import React, { useState } from 'react';
import { Shield, Smartphone, Monitor, Terminal, Wifi, BatteryCharging, Server, Settings, Check, X } from 'lucide-react';

export default function Navbar({ isMobileFrame, setIsMobileFrame, showTerminal, setShowTerminal, logsCount, activeTarget, setActiveTarget, apiUrl, setApiUrl }) {
  const [showApiModal, setShowApiModal] = useState(false);
  const [tempApiUrl, setTempApiUrl] = useState(apiUrl);
  const currentTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const saveApiUrl = () => {
    setApiUrl(tempApiUrl);
    setShowApiModal(false);
  };

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
            <span className="text-[10px] text-emerald-400 font-bold">5G / APK</span>
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
                APK / PWA
              </span>
            </div>
            <p className="text-[10px] font-mono text-slate-400 -mt-0.5">Mobile Security Suite</p>
          </div>
        </div>

        {/* Header Controls */}
        <div className="flex items-center space-x-1.5">
          {/* API Server Settings Button */}
          <button
            onClick={() => setShowApiModal(true)}
            className="p-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg transition-all"
            title="Configure Backend API Endpoint"
          >
            <Server className="w-4 h-4 text-amber-400" />
          </button>

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

          {/* Viewport Frame Toggle */}
          <button
            onClick={() => setIsMobileFrame(!isMobileFrame)}
            className="p-2 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg transition-all"
            title={isMobileFrame ? 'Switch to Full Screen' : 'Switch to Mobile APK View'}
          >
            {isMobileFrame ? (
              <Monitor className="w-4 h-4 text-cyan-400" />
            ) : (
              <Smartphone className="w-4 h-4 text-emerald-400" />
            )}
          </button>
        </div>
      </div>

      {/* Backend API Configuration Modal */}
      {showApiModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 max-w-sm w-full space-y-3 font-mono text-xs shadow-2xl">
            <div className="flex justify-between items-center border-b border-slate-800 pb-2">
              <div className="flex items-center space-x-1.5">
                <Server className="w-4 h-4 text-amber-400" />
                <span className="font-bold text-slate-100">Mobile API Server URL</span>
              </div>
              <button onClick={() => setShowApiModal(false)} className="text-slate-400 hover:text-slate-100">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div>
              <label className="text-slate-400 block mb-1 text-[10px]">Python Backend Endpoint:</label>
              <input
                type="text"
                value={tempApiUrl}
                onChange={(e) => setTempApiUrl(e.target.value)}
                placeholder="e.g. http://192.168.1.100:5000 or /api"
                className="w-full bg-slate-950 border border-slate-800 text-emerald-400 rounded p-2 focus:outline-none focus:border-amber-500"
              />
              <p className="text-[10px] text-slate-500 mt-1 font-sans">
                Set to local network IP or VPS server when running as an APK on Android.
              </p>
            </div>

            <div className="flex justify-end space-x-2 pt-1">
              <button
                onClick={() => setShowApiModal(false)}
                className="px-3 py-1.5 bg-slate-800 text-slate-300 rounded hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={saveApiUrl}
                className="px-3 py-1.5 bg-amber-500 text-slate-950 font-bold rounded flex items-center space-x-1"
              >
                <Check className="w-3.5 h-3.5" />
                <span>Save Endpoint</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
