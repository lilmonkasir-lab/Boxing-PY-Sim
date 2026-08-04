import React from 'react';
import { LayoutDashboard, KeyRound, Globe, Network, Binary, Search, Terminal } from 'lucide-react';

export default function BottomNav({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'dashboard', label: 'Dash', icon: LayoutDashboard },
    { id: 'passhash', label: 'Hash & Pass', icon: KeyRound },
    { id: 'websec', label: 'WebSec', icon: Globe },
    { id: 'network', label: 'Network', icon: Network },
    { id: 'encoder', label: 'Encoder', icon: Binary },
    { id: 'osint', label: 'OSINT', icon: Search },
    { id: 'payloads', label: 'Payloads', icon: Terminal },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 px-1 py-1 max-w-5xl mx-auto">
      <div className="grid grid-cols-7 gap-0.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex flex-col items-center justify-center py-1.5 px-0.5 rounded-lg transition-all ${
                isActive
                  ? 'bg-slate-800 text-emerald-400 font-bold border border-emerald-500/30 shadow-sm shadow-emerald-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              <Icon className={`w-4 h-4 mb-0.5 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
              <span className="text-[10px] truncate max-w-full leading-tight font-sans">
                {item.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
