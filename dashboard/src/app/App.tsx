import { useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Header } from "./components/Header";
import { VisionFeed } from "./components/VisionFeed";
import { BedrockAnalysis } from "./components/BedrockAnalysis";
import { DeviceTelemetry } from "./components/DeviceTelemetry";
import { ContainerHealth } from "./components/ContainerHealth";

export default function App() {
  const [activeTab, setActiveTab] = useState("dashboard");

  return (
    <div className="h-screen bg-zinc-950 flex overflow-hidden">
      {/* Sidebar */}
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header />

        {/* Dashboard Grid */}
        <div className="flex-1 overflow-auto p-6">
          <div className="grid grid-cols-2 gap-6 h-full">
            {/* Widget A - Vision Feed (Larger, spans full height on left) */}
            <div className="row-span-2">
              <VisionFeed />
            </div>

            {/* Widget B - Bedrock Analysis */}
            <div>
              <BedrockAnalysis />
            </div>

            {/* Bottom right grid */}
            <div className="grid grid-cols-2 gap-6">
              {/* Widget C - Device Telemetry */}
              <div>
                <DeviceTelemetry />
              </div>

              {/* Widget D - Container Health */}
              <div>
                <ContainerHealth />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
