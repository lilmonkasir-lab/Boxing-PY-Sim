import React, { useState } from 'react';
import Navbar from './components/Navbar';
import BottomNav from './components/BottomNav';
import TerminalDrawer from './components/TerminalDrawer';
import DashboardView from './components/DashboardView';
import PasswordHashView from './components/PasswordHashView';
import WebTestingView from './components/WebTestingView';
import NetworkView from './components/NetworkView';
import EncoderView from './components/EncoderView';
import OsintView from './components/OsintView';
import PayloadLibraryView from './components/PayloadLibraryView';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [activeTarget, setActiveTarget] = useState('scanme.nmap.org');
  const [isMobileFrame, setIsMobileFrame] = useState(true);
  const [showTerminal, setShowTerminal] = useState(false);
  const [logs, setLogs] = useState([
    {
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type: 'SUCCESS',
      title: 'NexusSec Mobile Pentest Engine Initialized',
      data: { status: 'ONLINE', mode: 'Mobile Pentest Kit', version: '2.0.0' }
    }
  ]);

  const addLog = (type, title, data) => {
    const newLog = {
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      type,
      title,
      data
    };
    setLogs((prev) => [newLog, ...prev.slice(0, 49)]); // keep last 50 logs
  };

  const clearLogs = () => setLogs([]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased flex flex-col justify-between selection:bg-emerald-500/30 selection:text-emerald-300">
      <div className={`w-full mx-auto transition-all ${isMobileFrame ? 'max-w-md my-0 sm:my-4 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden bg-slate-950 min-h-[844px]' : 'max-w-5xl'}`}>
        {/* Header Navigation */}
        <Navbar
          isMobileFrame={isMobileFrame}
          setIsMobileFrame={setIsMobileFrame}
          showTerminal={showTerminal}
          setShowTerminal={setShowTerminal}
          logsCount={logs.length}
          activeTarget={activeTarget}
          setActiveTarget={setActiveTarget}
        />

        {/* Main Content Area */}
        <main className="p-3 sm:p-4">
          {activeTab === 'dashboard' && (
            <DashboardView
              setActiveTab={setActiveTab}
              activeTarget={activeTarget}
              setActiveTarget={setActiveTarget}
              addLog={addLog}
            />
          )}

          {activeTab === 'passhash' && <PasswordHashView addLog={addLog} />}

          {activeTab === 'websec' && <WebTestingView activeTarget={activeTarget} addLog={addLog} />}

          {activeTab === 'network' && <NetworkView activeTarget={activeTarget} addLog={addLog} />}

          {activeTab === 'encoder' && <EncoderView addLog={addLog} />}

          {activeTab === 'osint' && <OsintView activeTarget={activeTarget} addLog={addLog} />}

          {activeTab === 'payloads' && <PayloadLibraryView addLog={addLog} />}
        </main>

        {/* Live Terminal / Console Drawer */}
        <TerminalDrawer
          logs={logs}
          clearLogs={clearLogs}
          isOpen={showTerminal}
          setIsOpen={setShowTerminal}
        />

        {/* Bottom Tab Navigation Bar */}
        <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
    </div>
  );
}
