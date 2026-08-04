import React, { useState } from 'react';
import { Network, Cpu, Wifi, RefreshCw, Radio, CheckCircle2, XCircle } from 'lucide-react';

export default function NetworkView({ activeTarget, addLog }) {
  const [subTab, setSubTab] = useState('portscan'); // portscan | subnet | dns

  // Port Scan State
  const [targetHost, setTargetHost] = useState(activeTarget || 'scanme.nmap.org');
  const [portPreset, setPortPreset] = useState('common'); // common | web | db
  const [scanResult, setScanResult] = useState(null);
  const [loadingScan, setLoadingScan] = useState(false);

  // Subnet State
  const [cidrInput, setCidrInput] = useState('192.168.1.0/24');
  const [subnetResult, setSubnetResult] = useState(null);
  const [loadingSubnet, setLoadingSubnet] = useState(false);

  // DNS State
  const [dnsDomain, setDnsDomain] = useState(activeTarget || 'google.com');
  const [dnsResult, setDnsResult] = useState(null);
  const [loadingDns, setLoadingDns] = useState(false);

  // Preset port definitions
  const portPresets = {
    common: [21, 22, 23, 25, 53, 80, 110, 139, 443, 445, 1433, 3306, 3389, 5432, 6379, 8080, 8443],
    web: [80, 443, 8000, 8080, 8443, 8888, 9000],
    db: [1433, 1521, 3306, 5432, 6379, 27017]
  };

  // 1. Handle Port Scan
  const handlePortScan = async () => {
    if (!targetHost) return;
    setLoadingScan(true);
    try {
      const selectedPorts = portPresets[portPreset] || portPresets.common;
      const res = await fetch('/api/network/portscan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: targetHost, ports: selectedPorts })
      });
      const data = await res.json();
      setScanResult(data);
      addLog('SUCCESS', `Port Scan (${data.open_count} Open Ports found on ${data.resolved_ip})`, data);
    } catch (e) {
      addLog('ERROR', 'Port Scan Failed', { error: e.message });
    } finally {
      setLoadingScan(false);
    }
  };

  // 2. Handle Subnet Calculation
  const handleSubnetCalc = async () => {
    if (!cidrInput) return;
    setLoadingSubnet(true);
    try {
      const res = await fetch('/api/network/subnet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cidr: cidrInput })
      });
      const data = await res.json();
      setSubnetResult(data);
      addLog('SUCCESS', `Calculated CIDR Subnet (${data.usable_hosts} hosts)`, data);
    } catch (e) {
      addLog('ERROR', 'Subnet Calculation Failed', { error: e.message });
    } finally {
      setLoadingSubnet(false);
    }
  };

  // 3. Handle DNS Lookup
  const handleDnsLookup = async () => {
    if (!dnsDomain) return;
    setLoadingDns(true);
    try {
      const res = await fetch('/api/network/dns', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ domain: dnsDomain })
      });
      const data = await res.json();
      setDnsResult(data);
      addLog('SUCCESS', `DNS Resolution for ${dnsDomain}`, data);
    } catch (e) {
      addLog('ERROR', 'DNS Lookup Failed', { error: e.message });
    } finally {
      setLoadingDns(false);
    }
  };

  return (
    <div className="space-y-4 pb-20">
      <div className="flex items-center space-x-2">
        <Network className="w-5 h-5 text-emerald-400" />
        <h1 className="font-extrabold text-base text-slate-100">Network & Port Scanner</h1>
      </div>

      {/* Sub Tabs */}
      <div className="flex space-x-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs font-mono overflow-x-auto">
        {[
          { id: 'portscan', label: 'Port Scanner' },
          { id: 'subnet', label: 'CIDR Subnet Calc' },
          { id: 'dns', label: 'DNS Resolver' }
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

      {/* SUBTAB 1: PORT SCANNER */}
      {subTab === 'portscan' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target IP / Hostname:</label>
              <input
                type="text"
                value={targetHost}
                onChange={(e) => setTargetHost(e.target.value)}
                placeholder="e.g. scanme.nmap.org or 192.168.1.1"
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <div>
              <label className="text-[10px] font-mono text-slate-400 block mb-1">Port Preset Range:</label>
              <div className="grid grid-cols-3 gap-1.5 text-xs font-mono">
                {[
                  { id: 'common', label: 'Top Common (17 Ports)' },
                  { id: 'web', label: 'Web Ports (80/443...)' },
                  { id: 'db', label: 'Database Ports' }
                ].map((preset) => (
                  <button
                    key={preset.id}
                    onClick={() => setPortPreset(preset.id)}
                    className={`py-1.5 px-2 rounded text-[11px] border transition-all ${
                      portPreset === preset.id
                        ? 'bg-emerald-500/20 text-emerald-400 font-bold border-emerald-500/40'
                        : 'bg-slate-950 border-slate-800 text-slate-400'
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handlePortScan}
              disabled={loadingScan}
              className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingScan ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
              <span>Execute Port Scan</span>
            </button>
          </div>

          {scanResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3 font-mono text-xs">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div>
                  <span className="text-slate-400 text-[10px] block">Resolved IP</span>
                  <span className="text-emerald-400 font-bold text-xs">{scanResult.resolved_ip} ({scanResult.target})</span>
                </div>
                <div className="text-right">
                  <span className="text-slate-400 text-[10px] block">Open Ports</span>
                  <span className="font-extrabold text-sm text-emerald-400">{scanResult.open_count} / {scanResult.total_scanned}</span>
                </div>
              </div>

              {/* Port Table */}
              <div className="space-y-1.5">
                {scanResult.results.map((res, i) => {
                  const isOpen = res.status === 'OPEN';
                  return (
                    <div
                      key={i}
                      className={`p-2 rounded border flex items-center justify-between ${
                        isOpen ? 'bg-emerald-950/20 border-emerald-800/80 text-emerald-300' : 'bg-slate-950 border-slate-800/80 text-slate-500'
                      }`}
                    >
                      <div className="flex items-center space-x-2">
                        {isOpen ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <XCircle className="w-4 h-4 text-slate-600 shrink-0" />}
                        <div>
                          <span className="font-bold text-xs">Port {res.port}</span>
                          <span className="text-[10px] text-slate-400 ml-2">({res.service})</span>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isOpen ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-800 text-slate-500'}`}>
                          {res.status}
                        </span>
                        <span className="text-[10px] text-slate-500 ml-2">{res.latency_ms}ms</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 2: CIDR SUBNET CALC */}
      {subTab === 'subnet' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">CIDR Subnet Notation:</label>
              <input
                type="text"
                value={cidrInput}
                onChange={(e) => setCidrInput(e.target.value)}
                placeholder="192.168.1.0/24"
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleSubnetCalc}
              disabled={loadingSubnet}
              className="w-full py-2 bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingSubnet ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Cpu className="w-4 h-4" />}
              <span>Calculate IP Subnet Range</span>
            </button>
          </div>

          {subnetResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="text-slate-400 text-xs border-b border-slate-800 pb-1.5 flex justify-between">
                <span>Network Range ({subnetResult.cidr})</span>
                <span className="text-emerald-400 font-bold">{subnetResult.usable_hosts} Usable IPs</span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Network IP</span>
                  <span className="text-emerald-400 font-bold">{subnetResult.network_address}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Netmask</span>
                  <span className="text-cyan-400 font-bold">{subnetResult.netmask}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">First Usable Host</span>
                  <span className="text-slate-200">{subnetResult.first_usable_ip}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Last Usable Host</span>
                  <span className="text-slate-200">{subnetResult.last_usable_ip}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Broadcast Address</span>
                  <span className="text-amber-400 font-bold">{subnetResult.broadcast_address}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Wildcard Mask</span>
                  <span className="text-purple-400 font-bold">{subnetResult.wildcard_mask}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUBTAB 3: DNS RESOLVER */}
      {subTab === 'dns' && (
        <div className="space-y-3">
          <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-3">
            <div>
              <label className="text-xs font-mono text-slate-400 block mb-1">Target Domain Name:</label>
              <input
                type="text"
                value={dnsDomain}
                onChange={(e) => setDnsDomain(e.target.value)}
                placeholder="example.com"
                className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 text-slate-100 rounded-lg p-2.5 font-mono text-xs focus:outline-none"
              />
            </div>

            <button
              onClick={handleDnsLookup}
              disabled={loadingDns}
              className="w-full py-2 bg-gradient-to-r from-emerald-500 to-teal-500 text-slate-950 font-bold font-mono rounded-lg text-xs flex items-center justify-center space-x-1"
            >
              {loadingDns ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Wifi className="w-4 h-4" />}
              <span>Resolve DNS Records</span>
            </button>
          </div>

          {dnsResult && (
            <div className="bg-slate-900 rounded-xl p-3.5 border border-slate-800 space-y-2 font-mono text-xs">
              <div className="text-slate-400 text-xs border-b border-slate-800 pb-1.5">
                DNS Records for <strong className="text-emerald-400">{dnsResult.domain}</strong>
              </div>

              {Object.entries(dnsResult.records).map(([recType, list]) => (
                <div key={recType} className="bg-slate-950 p-2 rounded border border-slate-800 space-y-1">
                  <span className="text-emerald-400 font-bold text-[10px] block">{recType} Records ({list.length})</span>
                  {list.length > 0 ? (
                    list.map((ip, i) => (
                      <div key={i} className="text-slate-200 text-[11px] font-mono">{ip}</div>
                    ))
                  ) : (
                    <span className="text-slate-600 text-[10px] italic">No records found</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
