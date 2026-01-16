import { Brain, Sparkles, Send, User, Bot, AlertTriangle, CheckCircle, Info } from "lucide-react";
import { useEffect, useState, useRef } from "react";
import { socket } from "../services/socket"; // Import shared socket

interface Message {
  id: number;
  type: "user" | "ai" | "system_info" | "system_warning" | "system_success";
  text: string;
  timestamp: string;
}

export function BedrockAnalysis() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      type: "ai",
      text: "Hello. I am the Minimart AI Assistant. I can analyze store logs, check inventory, and answer questions about store security.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    // 1. Connection Status Handlers
    function onConnect() {
      setIsConnected(true);
    }

    function onDisconnect() {
      setIsConnected(false);
    }

    // 2. Chat Response Handler (Answers to your questions)
    function onBedrockResponse(data: { text: string }) {
      setIsTyping(false);
      addMessage("ai", data.text);
    }

    // 3. System Alert Handler (Unsolicited updates from IoT Core)
    function onBedrockAlert(data: { message: string; type: string }) {
      let msgType: Message['type'] = "system_info";
      if (data.type === "warning") msgType = "system_warning";
      if (data.type === "success") msgType = "system_success";
      addMessage(msgType, data.message);
    }

    // Attach Listeners
    socket.on("connect", onConnect);
    socket.on("disconnect", onDisconnect);
    socket.on("bedrock_response", onBedrockResponse);
    socket.on("bedrock_alert", onBedrockAlert);

    // Initial check in case socket is already connected
    if (socket.connected) setIsConnected(true);

    return () => {
      // Detach Listeners
      socket.off("connect", onConnect);
      socket.off("disconnect", onDisconnect);
      socket.off("bedrock_response", onBedrockResponse);
      socket.off("bedrock_alert", onBedrockAlert);
    };
  }, []);

  const addMessage = (type: Message['type'], text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: Date.now(),
        type,
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      },
    ]);
  };

  const handleSend = (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputValue.trim()) return;

    // 1. Add User Message immediately
    addMessage("user", inputValue);
    
    // 2. Emit to Backend
    socket.emit("bedrock_query", { query: inputValue });
    
    // 3. Set Loading State
    setInputValue("");
    setIsTyping(true);
  };

  const renderIcon = (type: Message['type']) => {
    switch (type) {
      case "ai": return <Bot className="w-4 h-4 text-purple-400" />;
      case "user": return <User className="w-4 h-4 text-zinc-400" />;
      case "system_warning": return <AlertTriangle className="w-4 h-4 text-amber-400" />;
      case "system_success": return <CheckCircle className="w-4 h-4 text-emerald-400" />;
      default: return <Info className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <div className="bg-zinc-900 border border-zinc-800 rounded-lg h-full flex flex-col overflow-hidden shadow-sm">
      {/* Header */}
      <div className="p-4 border-b border-zinc-800 flex justify-between items-center bg-zinc-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-purple-400" />
          <h2 className="text-white font-semibold">Store Manager Assistant</h2>
          <Sparkles className="w-3 h-3 text-purple-400 animate-pulse" />
        </div>
        <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} />
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-zinc-950/30">
        {messages.map((msg) => {
          const isSystem = msg.type.startsWith("system");
          const isUser = msg.type === "user";

          if (isSystem) {
            let borderColor = "border-cyan-500/20 bg-cyan-500/5";
            if (msg.type === "system_warning") borderColor = "border-amber-500/20 bg-amber-500/5";
            if (msg.type === "system_success") borderColor = "border-emerald-500/20 bg-emerald-500/5";

            return (
              <div key={msg.id} className={`flex items-start gap-3 p-3 rounded-lg border ${borderColor} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
                <div className="mt-0.5">{renderIcon(msg.type)}</div>
                <div className="flex-1">
                  <p className="text-sm text-zinc-300">{msg.text}</p>
                  <span className="text-[10px] text-zinc-500 font-mono mt-1 block">{msg.timestamp}</span>
                </div>
              </div>
            );
          }

          return (
            <div key={msg.id} className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} animate-in fade-in slide-in-from-bottom-2 duration-300`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? "bg-zinc-800" : "bg-purple-500/10 border border-purple-500/20"}`}>
                {renderIcon(msg.type)}
              </div>
              
              <div className={`max-w-[85%] rounded-lg p-3 ${isUser ? "bg-zinc-800 text-zinc-200" : "bg-zinc-900 border border-zinc-800 text-zinc-300"}`}>
                <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                <span className="text-[10px] text-zinc-500 mt-2 block opacity-70">{msg.timestamp}</span>
              </div>
            </div>
          );
        })}
        
        {isTyping && (
          <div className="flex gap-3 animate-in fade-in duration-300">
             <div className="w-8 h-8 rounded-full bg-purple-500/10 border border-purple-500/20 flex items-center justify-center">
                <Bot className="w-4 h-4 text-purple-400" />
             </div>
             <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-3 flex items-center gap-1">
                <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <div className="w-1.5 h-1.5 bg-zinc-500 rounded-full animate-bounce" />
             </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-zinc-900 border-t border-zinc-800">
        <form onSubmit={handleSend} className="relative">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder={isConnected ? "Ask about inventory, anomalies..." : "Connecting to brain..."}
            disabled={!isConnected}
            className="w-full bg-zinc-950 border border-zinc-800 text-zinc-300 rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 transition-all placeholder:text-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={!inputValue.trim() || !isConnected}
            className="absolute right-2 top-2 p-1.5 bg-purple-600 hover:bg-purple-500 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
        <div className="text-[10px] text-center text-zinc-600 mt-2 flex justify-center items-center gap-1.5">
          <span>Powered by AWS Bedrock</span>
          <span className="w-0.5 h-0.5 rounded-full bg-zinc-600" />
          <span>Claude 3.5 Sonnet</span>
        </div>
      </div>
    </div>
  );
}