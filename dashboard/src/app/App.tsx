import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { VisionFeed } from "./components/VisionFeed";
import { BedrockAnalysis } from "./components/BedrockAnalysis";
import { DeviceTelemetry } from "./components/DeviceTelemetry";
import { ContainerHealth } from "./components/ContainerHealth";

// Backend URL - can be configured via environment variable
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:5000";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="h-screen bg-zinc-950 flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with real-time connection status */}
        <Header backendUrl={BACKEND_URL} />

        {/* Dashboard Grid */}
        <div className="flex-1 overflow-auto p-6">
          {activeTab === "dashboard" && (
            <div className="grid grid-cols-2 gap-6 h-full min-h-[600px]">
              {/* Widget A - Vision Feed (Left column, full height) */}
              <div className="row-span-2">
                <VisionFeed backendUrl={BACKEND_URL} />
              </div>

              {/* Widget B - Bedrock Analysis (Top right) */}
              <div className="h-[400px]">
                <BedrockAnalysis backendUrl={BACKEND_URL} />
              </div>

              {/* Bottom right grid - Telemetry widgets */}
              <div className="grid grid-cols-2 gap-6">
                {/* Widget C - Device Telemetry */}
                <div className="h-full">
                  <DeviceTelemetry backendUrl={BACKEND_URL} />
                </div>

                {/* Widget D - Container Health */}
                <div className="h-full">
                  <ContainerHealth backendUrl={BACKEND_URL} />
                </div>
              </div>
            </div>
          )}

          {activeTab === "live-vision" && (
            <div className="h-full">
              <VisionFeed backendUrl={BACKEND_URL} />
            </div>
          )}

          {activeTab === "system-health" && (
            <div className="grid grid-cols-2 gap-6 h-full">
              <DeviceTelemetry backendUrl={BACKEND_URL} />
              <ContainerHealth backendUrl={BACKEND_URL} />
            </div>
          )}

          {activeTab === "inventory-logs" && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center">
                <h2 className="text-xl text-zinc-400 mb-2">Inventory Logs</h2>
                <p className="text-zinc-600">Coming soon - Will integrate with tracking history</p>
              </div>
            </div>
          )}

          {activeTab === "settings" && (
            <div className="max-w-2xl mx-auto">
              <h2 className="text-xl text-white mb-6">Settings</h2>
              
              <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 space-y-6">
                <div>
                  <label className="block text-sm text-zinc-400 mb-2">Backend URL</label>
                  <input 
                    type="text" 
                    value={BACKEND_URL}
                    readOnly
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-4 py-2 text-zinc-300 font-mono text-sm"
                  />
                  <p className="text-xs text-zinc-600 mt-1">
                    Set via VITE_BACKEND_URL environment variable
                  </p>
                </div>

                <div>
                  <label className="block text-sm text-zinc-400 mb-2">API Endpoints</label>
                  <div className="space-y-2 text-sm font-mono">
                    <div className="flex justify-between text-zinc-500">
                      <span>Video Feed:</span>
                      <span className="text-cyan-400">{BACKEND_URL}/video_feed</span>
                    </div>
                    <div className="flex justify-between text-zinc-500">
                      <span>Coordinates:</span>
                      <span className="text-cyan-400">{BACKEND_URL}/api/coordinates</span>
                    </div>
                    <div className="flex justify-between text-zinc-500">
                      <span>Telemetry:</span>
                      <span className="text-cyan-400">{BACKEND_URL}/api/telemetry</span>
                    </div>
                    <div className="flex justify-between text-zinc-500">
                      <span>WebSocket:</span>
                      <span className="text-cyan-400">ws://localhost:5000</span>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-zinc-800">
                  <p className="text-xs text-zinc-600">
                    Minimart 2.0 Dashboard • WebSocket Bridge Integration
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
