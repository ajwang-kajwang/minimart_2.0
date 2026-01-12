import { Brain, Sparkles, MessageSquare, Send, Loader2 } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { useTrackingSocket } from "../hooks";

interface AnalysisEntry {
  id: number;
  timestamp: string;
  message: string;
  type: "info" | "warning" | "success" | "system";
  source: "ai" | "system" | "user";
}

interface BedrockAnalysisProps {
  backendUrl?: string;
}

export function BedrockAnalysis({ backendUrl = "http://localhost:5000" }: BedrockAnalysisProps) {
  // 1. Destructure socket from the hook (ensure hook is updated to return this)
  const { trackingData, activePeople, isConnected, socket } = useTrackingSocket({ url: backendUrl });
  
  const [entries, setEntries] = useState<AnalysisEntry[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Track previous state for generating insights
  const prevActiveCount = useRef(0);
  const lastInsightTime = useRef(0);

  // Auto-scroll to bottom when new entries added
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [entries]);

  // 2. Listen for Real AI Responses from Flask
  useEffect(() => {
    if (!socket) return;

    const handleBedrockResponse = (data: { answer: string }) => {
      addEntry({
        message: data.answer,
        type: "success",
        source: "ai"
      });
      setIsProcessing(false);
    };

    socket.on("bedrock_response", handleBedrockResponse);

    return () => {
      socket.off("bedrock_response", handleBedrockResponse);
    };
  }, [socket]);

  // Generate automatic insights based on tracking data (Client-side logic)
  useEffect(() => {
    const now = Date.now();
    const timeSinceLastInsight = now - lastInsightTime.current;
    
    // Don't spam insights - minimum 5 seconds between auto-generated ones
    if (timeSinceLastInsight < 5000) return;
    
    const currentCount = activePeople.length;

    // Detect significant changes
    if (currentCount !== prevActiveCount.current) {
      const diff = currentCount - prevActiveCount.current;
      
      if (diff > 0) {
        addEntry({
          message: `${diff} new ${diff === 1 ? 'person' : 'people'} detected in frame. Total active: ${currentCount}`,
          type: "info",
          source: "system"
        });
      } else if (diff < 0 && prevActiveCount.current > 0) {
        addEntry({
          message: `${Math.abs(diff)} ${Math.abs(diff) === 1 ? 'person' : 'people'} left the frame. Remaining: ${currentCount}`,
          type: "info", 
          source: "system"
        });
      }
      
      prevActiveCount.current = currentCount;
      lastInsightTime.current = now;
    }
  }, [activePeople.length]);

  // Add initial system message
  useEffect(() => {
    if (entries.length === 0) {
      addEntry({
        message: "Minimart Analytics ready. I can help analyze customer traffic patterns, identify anomalies, and generate reports. What would you like to know?",
        type: "system",
        source: "ai"
      });
    }
  }, []);

  const addEntry = (entry: Omit<AnalysisEntry, "id" | "timestamp">) => {
    const timestamp = new Date().toLocaleTimeString('en-US', { 
      hour12: false, 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
    
    setEntries(prev => [...prev.slice(-19), { // Keep last 20 entries
      ...entry,
      id: Date.now(),
      timestamp
    }]);
  };

  const handleSendMessage = () => {
    if (!inputMessage.trim() || isProcessing) return;
    
    const userMessage = inputMessage.trim();
    setInputMessage("");
    
    // Add user message to UI immediately
    addEntry({
      message: userMessage,
      type: "info",
      source: "user"
    });
    
    setIsProcessing(true);
    
    // 3. Send Request to Python Backend via Socket.IO
    if (socket && isConnected) {
      socket.emit("ask_bedrock", { 
        question: userMessage,
        context: {
            active_people: activePeople.length,
            fps: trackingData.fps
        }
      });
    } else {
      // Fallback if disconnected
      setTimeout(() => {
          addEntry({
              message: "Error: Connection to backend lost.",
              type: "warning",
              source: "system"
          });
          setIsProcessing(false);
      }, 500);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const getTypeColor = (type: string, source: string) => {
    if (source === "user") return "border-blue-500/20 bg-blue-500/5";
    switch (type) {
      case "warning":
        return "border-amber-500/20 bg-amber-500/5";
      case "success":
        return "border-emerald-500/20 bg-emerald-500/5";
      case "system":
        return "border-purple-500/20 bg-purple-500/5";
      default:
        return "border-cyan-500/20 bg-cyan-500/5";
    }
  };

  const getTypeDot = (type: string, source: string) => {
    if (source === "user") return "bg-blue-400";
    switch (type) {
      case "warning":
        return "bg-amber-400";
      case "success":
        return "bg-emerald-400";
      case "system":
        return "bg-purple-400";
      default:
        return "bg-cyan-400";
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-5 h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-purple-400" />
        <h2 className="text-white font-semibold">Store Analytics</h2>
        <Sparkles className="w-4 h-4 text-purple-400 ml-1" />
        <div className="ml-auto flex items-center gap-1.5 text-xs">
          <div className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-emerald-400' : 'bg-zinc-600'}`} />
          <span className={isConnected ? 'text-emerald-400' : 'text-zinc-500'}>
            {isConnected ? 'Live' : 'Offline'}
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-3 pr-2 mb-4"
      >
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`border rounded-lg p-3 ${getTypeColor(entry.type, entry.source)} transition-all`}
          >
            <div className="flex items-start gap-3">
              <div className={`w-2 h-2 ${getTypeDot(entry.type, entry.source)} rounded-full mt-1.5 flex-shrink-0`}></div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-zinc-500 font-mono">{entry.timestamp}</span>
                  {entry.source === "ai" && (
                    <span className="text-xs text-purple-400 font-medium">AI</span>
                  )}
                  {entry.source === "user" && (
                    <span className="text-xs text-blue-400 font-medium">You</span>
                  )}
                  {entry.source === "system" && (
                    <span className="text-xs text-cyan-400 font-medium">System</span>
                  )}
                </div>
                <p className="text-sm text-zinc-300">{entry.message}</p>
              </div>
            </div>
          </div>
        ))}
        
        {isProcessing && (
          <div className="flex items-center gap-2 text-purple-400 text-sm p-3">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Analyzing...</span>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="border-t border-zinc-800 pt-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 relative">
            <MessageSquare className="w-4 h-4 text-zinc-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask about traffic patterns, generate reports..."
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-zinc-200 placeholder-zinc-500 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/25"
              disabled={isProcessing || !isConnected}
            />
          </div>
          <button
            onClick={handleSendMessage}
            disabled={!inputMessage.trim() || isProcessing || !isConnected}
            className="p-2.5 bg-purple-500 hover:bg-purple-600 disabled:bg-zinc-700 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {isProcessing ? (
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            ) : (
              <Send className="w-4 h-4 text-white" />
            )}
          </button>
        </div>
        
        <div className="mt-3 flex items-center justify-between text-xs text-zinc-500">
          <span>AI Model: Claude 3.5 Sonnet</span>
          <div className="flex items-center gap-1">
            <div className={`w-1.5 h-1.5 bg-purple-400 rounded-full ${isConnected ? 'animate-pulse' : ''}`}></div>
            <span className="text-purple-400">{isConnected ? 'Bedrock Connected' : 'Waiting for connection...'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}