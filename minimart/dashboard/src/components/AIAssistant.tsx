'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Send, Sparkles, MessageCircle, RefreshCw, AlertCircle } from 'lucide-react';

interface AIAssistantProps {
    dateRange: {
        start: string;
        end: string;
    };
    kpis: {
        uniqueShoppers: number;
        avgDwellTime: number;
        peakHour: number;
        avgTemp: number | null;
        avgHumidity: number | null;
    };
}

interface Message {
    role: 'user' | 'assistant';
    content: string;
}

interface AiInsights {
    summary: string;
    highlights: string[];
    recommendations: string[];
    cached?: boolean;
    error?: string;
}

// Module-level cache to persist insights between component unmount/remount
const insightsCache = new Map<string, AiInsights>();

// Simple markdown renderer for chat messages
const renderMarkdown = (text: string): React.ReactNode => {
    // Split by markdown patterns and render
    const parts: React.ReactNode[] = [];
    let remaining = text;
    let key = 0;

    // Pattern for **bold**, *italic*, `code`, and newlines
    const patterns = [
        { regex: /\*\*([^*]+)\*\*/g, render: (match: string) => <strong key={key++}>{match}</strong> },
        { regex: /\*([^*]+)\*/g, render: (match: string) => <em key={key++}>{match}</em> },
        { regex: /`([^`]+)`/g, render: (match: string) => <code key={key++} className="bg-gray-200 px-1 rounded text-xs">{match}</code> },
    ];

    // Process bold first
    const boldRegex = /\*\*([^*]+)\*\*/g;
    const italicRegex = /(?<!\*)\*([^*]+)\*(?!\*)/g;
    const codeRegex = /`([^`]+)`/g;

    // Simple approach: replace patterns with placeholders, then reconstruct
    let processed = text
        .split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\n)/g)
        .filter(Boolean)
        .map((part, idx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
                return <strong key={idx}>{part.slice(2, -2)}</strong>;
            }
            if (part.startsWith('*') && part.endsWith('*') && !part.startsWith('**')) {
                return <em key={idx}>{part.slice(1, -1)}</em>;
            }
            if (part.startsWith('`') && part.endsWith('`')) {
                return <code key={idx} className="bg-gray-200 px-1 rounded text-xs">{part.slice(1, -1)}</code>;
            }
            if (part === '\n') {
                return <br key={idx} />;
            }
            return part;
        });

    return <>{processed}</>;
};

export default function AIAssistant({ dateRange, kpis }: AIAssistantProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [chatLoading, setChatLoading] = useState(false);
    const [insights, setInsights] = useState<AiInsights | null>(null);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [insightsError, setInsightsError] = useState<string | null>(null);
    const [chatPanelHeight, setChatPanelHeight] = useState<number | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const messagesContainerRef = useRef<HTMLDivElement>(null);
    const leftPanelRef = useRef<HTMLDivElement>(null);

    // Auto-scroll to bottom when new messages are added (only scrolls the container, not the page)
    useEffect(() => {
        if ((messages.length > 0 || chatLoading) && messagesContainerRef.current) {
            messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
        }
    }, [messages, chatLoading]);

    // Capture left panel height after insights load to fix right panel height
    useEffect(() => {
        if (insights && !insightsLoading && leftPanelRef.current && chatPanelHeight === null) {
            // Small delay to ensure DOM has rendered
            setTimeout(() => {
                if (leftPanelRef.current) {
                    setChatPanelHeight(leftPanelRef.current.offsetHeight);
                }
            }, 100);
        }
    }, [insights, insightsLoading, chatPanelHeight]);

    // Check if it's a single day selection
    const isSingleDay = dateRange.start === dateRange.end;

    // Cache key for this date range
    const currentRangeKey = `${dateRange.start}-${dateRange.end}`;

    // Fetch AI insights for the current date range
    const fetchInsights = useCallback(async () => {
        setInsightsLoading(true);
        setInsightsError(null);

        try {
            // Pass both start and end dates to API
            const response = await fetch(`/api/ai/summary?start=${dateRange.start}&end=${dateRange.end}`);

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to fetch insights');
            }

            const data = await response.json();
            const insightsData: AiInsights = {
                summary: data.summary,
                highlights: data.highlights || [],
                recommendations: data.recommendations || [],
                cached: data.cached,
            };
            setInsights(insightsData);
            // Store in cache for future re-mounts
            insightsCache.set(currentRangeKey, insightsData);
        } catch (error) {
            console.error('Failed to fetch AI insights:', error);
            setInsightsError(error instanceof Error ? error.message : 'Failed to load AI insights');

            // Fallback to rule-based insights
            setInsights(generateFallbackInsights(isSingleDay ? false : true));
        } finally {
            setInsightsLoading(false);
        }
    }, [dateRange.start, dateRange.end, isSingleDay, currentRangeKey]);

    // Generate fallback insights when API fails or for multi-day ranges
    const generateFallbackInsights = (isMultiDay: boolean = false): AiInsights => {
        const highlights: string[] = [];

        if (kpis.peakHour >= 11 && kpis.peakHour <= 13) {
            highlights.push('Peak traffic occurs during lunch hours (11 AM - 1 PM).');
        } else if (kpis.peakHour >= 17 && kpis.peakHour <= 19) {
            highlights.push('Evening rush detected (5-7 PM).');
        }

        if (kpis.avgDwellTime > 10) {
            highlights.push('Above-average dwell time indicates good customer engagement.');
        } else if (kpis.avgDwellTime < 3) {
            highlights.push('Low dwell time may indicate navigation issues.');
        }

        if (kpis.avgTemp && kpis.avgTemp > 25) {
            highlights.push(`Store temperature is ${kpis.avgTemp}°C - consider adjusting AC.`);
        }

        // Different summary text for single day vs date range
        const periodText = isMultiDay
            ? `From ${dateRange.start} to ${dateRange.end}`
            : 'Today';

        const summary = `${periodText}, there were ${kpis.uniqueShoppers.toLocaleString()} shoppers with an average dwell time of ${kpis.avgDwellTime.toFixed(1)} minutes. Peak hour was ${kpis.peakHour}:00.`;

        return {
            summary,
            highlights: highlights.length > 0 ? highlights : ['All metrics within normal ranges.'],
            recommendations: ['Continue monitoring traffic patterns.'],
        };
    };

    // Load insights on component mount and when date changes
    useEffect(() => {
        // Check if we have cached data for this date range
        const cachedData = insightsCache.get(currentRangeKey);
        if (cachedData) {
            // Use cached data, no API call needed
            setInsights(cachedData);
            return;
        }

        // Only fetch if we don't have cached data
        fetchInsights();
    }, [fetchInsights, currentRangeKey]);

    // Handle chat submission
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || chatLoading) return;

        const userMessage = input.trim();
        setInput('');
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
        setChatLoading(true);

        try {
            const response = await fetch('/api/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: userMessage,
                    dateRange,
                    history: messages.slice(-6), // Send last 6 messages for context
                }),
            });

            if (!response.ok) {
                throw new Error('Failed to get response');
            }

            const data = await response.json();
            setMessages(prev => [...prev, { role: 'assistant', content: data.answer }]);
        } catch (error) {
            console.error('Chat error:', error);
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.'
            }]);
        } finally {
            setChatLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-gray-100 items-stretch">
                {/* AI Insights Panel */}
                <div ref={leftPanelRef} className="p-5">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                            <Sparkles className="h-5 w-5 text-teal-500" />
                            <h3 className="text-lg font-semibold text-gray-800">AI Insights</h3>
                            {insights?.cached && (
                                <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded">cached</span>
                            )}
                        </div>
                        <button
                            onClick={fetchInsights}
                            disabled={insightsLoading}
                            className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
                            title="Refresh insights"
                        >
                            <RefreshCw className={`h-4 w-4 text-gray-500 ${insightsLoading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>

                    {insightsLoading ? (
                        <div className="bg-teal-50 rounded-lg p-4 border-l-4 border-teal-500 animate-pulse">
                            <div className="h-4 bg-teal-200 rounded w-3/4 mb-3"></div>
                            <div className="h-3 bg-teal-100 rounded w-full mb-2"></div>
                            <div className="h-3 bg-teal-100 rounded w-5/6"></div>
                        </div>
                    ) : insightsError && !insights ? (
                        <div className="bg-red-50 rounded-lg p-4 border-l-4 border-red-500">
                            <div className="flex items-center gap-2 text-red-700">
                                <AlertCircle className="h-4 w-4" />
                                <span className="text-sm">{insightsError}</span>
                            </div>
                        </div>
                    ) : insights && (
                        <div className="bg-teal-50 rounded-lg p-4 border-l-4 border-teal-500">
                            <p className="text-sm text-teal-800 mb-3">{insights.summary}</p>

                            {insights.highlights.length > 0 && (
                                <>
                                    <p className="text-xs font-medium text-teal-600 mb-1">Key Highlights:</p>
                                    <ul className="space-y-1 mb-3">
                                        {insights.highlights.map((highlight, idx) => (
                                            <li key={idx} className="text-sm text-teal-700 flex items-start gap-2">
                                                <span className="text-teal-500">•</span>
                                                {highlight}
                                            </li>
                                        ))}
                                    </ul>
                                </>
                            )}

                            {insights.recommendations.length > 0 && (
                                <>
                                    <p className="text-xs font-medium text-teal-600 mb-1">Recommendations:</p>
                                    <ul className="space-y-1">
                                        {insights.recommendations.map((rec, idx) => (
                                            <li key={idx} className="text-sm text-teal-700 flex items-start gap-2">
                                                <span className="text-teal-500">→</span>
                                                {rec}
                                            </li>
                                        ))}
                                    </ul>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* AI Chat Panel - height fixed to match left panel */}
                <div
                    className="p-5 flex flex-col relative overflow-hidden"
                    style={chatPanelHeight ? { height: chatPanelHeight, maxHeight: chatPanelHeight } : undefined}
                >
                    <div className="flex items-center gap-2 mb-4 flex-shrink-0">
                        <MessageCircle className="h-5 w-5 text-blue-500" />
                        <h3 className="text-lg font-semibold text-gray-800">Ask AI</h3>
                    </div>

                    {/* Content container with relative positioning for animation */}
                    <div className="flex-1 flex flex-col min-h-0 relative">

                        {/* Empty state - input and suggestions centered together */}
                        {messages.length === 0 && !chatLoading ? (
                            <div className="flex-1 flex flex-col justify-center items-center transition-all duration-500 ease-out">
                                <p className="text-sm text-gray-400 mb-2">
                                    Ask questions about your store data...
                                </p>
                                <div className="flex flex-wrap gap-2 justify-center mb-4">
                                    {(isSingleDay ? [
                                        'What was today\'s peak hour?',
                                        'Which product category is most popular?',
                                        'How does traffic compare to yesterday?',
                                    ] : [
                                        'What was the busiest day during this period?',
                                        'Which product category is most popular?',
                                        'What are the traffic trends this week?',
                                    ]).map((suggestion, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => setInput(suggestion)}
                                            className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full hover:bg-gray-200 transition-colors"
                                        >
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                                {/* Input in centered state */}
                                <form onSubmit={handleSubmit} className="flex gap-2 w-full transition-all duration-500 ease-out">
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        placeholder="Ask about your store..."
                                        className="flex-1 px-4 py-2 rounded-full border border-gray-200 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                                    />
                                    <button
                                        type="submit"
                                        disabled={chatLoading || !input.trim()}
                                        className="p-2 rounded-full bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <Send className="h-5 w-5" />
                                    </button>
                                </form>
                            </div>
                        ) : (
                            /* Messages state - with input at bottom */
                            <div className="flex flex-col flex-1 min-h-0">
                                {/* Messages area - scrollable, flex-1 with min-h-0 for proper overflow */}
                                <div
                                    ref={messagesContainerRef}
                                    className="flex-1 min-h-0 overflow-y-auto space-y-3 mb-4 transition-all duration-500 ease-out"
                                    style={{ animation: 'fadeSlideIn 0.4s ease-out' }}
                                >
                                    {messages.map((msg, idx) => (
                                        <div
                                            key={idx}
                                            className={`text-sm p-3 rounded-lg max-w-[85%] ${msg.role === 'user'
                                                ? 'bg-blue-500 text-white ml-auto'
                                                : 'bg-gray-100 text-gray-700'
                                                }`}
                                        >
                                            {msg.role === 'assistant' ? renderMarkdown(msg.content) : msg.content}
                                        </div>
                                    ))}
                                    {chatLoading && (
                                        <div className="bg-gray-100 text-gray-500 text-sm p-3 rounded-lg max-w-[85%] flex items-center gap-2">
                                            <div className="flex gap-1">
                                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                                                <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                                            </div>
                                            <span>Thinking...</span>
                                        </div>
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>

                                {/* Input at bottom with slide-in animation */}
                                <form
                                    onSubmit={handleSubmit}
                                    className="flex gap-2 flex-shrink-0 transition-all duration-500 ease-out"
                                    style={{ animation: 'slideInUp 0.4s ease-out' }}
                                >
                                    <input
                                        type="text"
                                        value={input}
                                        onChange={(e) => setInput(e.target.value)}
                                        placeholder="Ask about your store..."
                                        className="flex-1 px-4 py-2 rounded-full border border-gray-200 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-teal-500 bg-white"
                                    />
                                    <button
                                        type="submit"
                                        disabled={chatLoading || !input.trim()}
                                        className="p-2 rounded-full bg-teal-500 text-white hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                        <Send className="h-5 w-5" />
                                    </button>
                                </form>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
