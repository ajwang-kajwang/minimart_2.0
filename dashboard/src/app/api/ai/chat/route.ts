import { NextResponse } from 'next/server';
import {
    getDailySummary,
    getHourlySummary,
    getTotalVisitors,
    getAvgDwellTime,
    getPeakHour,
    getZonePerformance,
    getDailyBreakdown,
    selectDataSource,
} from '@/lib/db';
import { chat, buildAnalyticsSystemPrompt, ChatMessage } from '@/lib/openai';

interface ChatRequest {
    question: string;
    dateRange: {
        start: string;
        end: string;
    };
    history?: Array<{ role: 'user' | 'assistant'; content: string }>;
}

/**
 * POST /api/ai/chat
 * Interactive chat endpoint for querying store data
 */
export async function POST(request: Request) {
    try {
        const body: ChatRequest = await request.json();
        const { question, dateRange, history = [] } = body;

        if (!question || !dateRange?.start || !dateRange?.end) {
            return NextResponse.json(
                { error: 'Question and dateRange (start, end) are required' },
                { status: 400 }
            );
        }

        // Determine which data source to use based on date range
        const dataSource = selectDataSource(dateRange.start, dateRange.end);
        const isSingleDay = dateRange.start === dateRange.end;

        // Fetch relevant data based on source
        let contextData: string;

        if (dataSource === 'daily' && !isSingleDay) {
            // Multi-day range: fetch per-day breakdown from raw data
            const [totalVisitors, avgDwell, peakHour, zonePerf] = await Promise.all([
                getTotalVisitors(dateRange.start, dateRange.end),
                getAvgDwellTime(dateRange.start, dateRange.end),
                getPeakHour(dateRange.start, dateRange.end),
                getZonePerformance(dateRange.start, dateRange.end),
            ]);

            // Get daily breakdown for finding busiest day
            const dailyBreakdown = await getDailyBreakdown(dateRange.start, dateRange.end);

            const topZones = zonePerf.slice(0, 3).map(z => z.zone).join(', ');
            const dailyStats = dailyBreakdown.map((d: { date: string; visitors: number; avg_dwell: string | number | null }) =>
                `${d.date}: ${d.visitors} visitors, ${d.avg_dwell ? parseFloat(String(d.avg_dwell)).toFixed(1) : 'N/A'} min avg dwell`
            ).join('\n');

            contextData = `
Data Summary for ${dateRange.start} to ${dateRange.end}:
- Total Visitors: ${totalVisitors}
- Average Dwell Time: ${avgDwell.toFixed(1)} minutes
- Peak Hour: ${peakHour}:00
- Top Zones/Shelves: ${topZones || 'N/A'}

Daily Breakdown:
${dailyStats}

Zone Performance: ${zonePerf.slice(0, 5).map(z => `${z.zone} (${z.visitors} visitors)`).join(', ')}
`;
        } else if (dataSource === 'daily') {
            // Single day with daily aggregation
            const dailySummary = await getDailySummary(dateRange.start);
            if (dailySummary) {
                contextData = `
Daily Summary for ${dateRange.start}:
- Total Shoppers (unique visitors): ${dailySummary.unique_shoppers}
- Data Records: ${dailySummary.total_records}
- Average Dwell Time: ${dailySummary.avg_dwell_minutes} minutes
- Peak Hour: ${dailySummary.peak_hour}:00
- Top Zones: ${dailySummary.top_zones?.join(', ') || 'N/A'}
- Change vs Yesterday: ${dailySummary.visitors_vs_yesterday ?? 'N/A'}%
- Change vs Last Week: ${dailySummary.visitors_vs_last_week ?? 'N/A'}%
${dailySummary.avg_temp ? `- Average Temperature: ${dailySummary.avg_temp}°C` : ''}
`;
            } else {
                // Fallback to raw data if no daily summary exists
                const [totalVisitors, avgDwell, peakHour, zonePerf] = await Promise.all([
                    getTotalVisitors(dateRange.start, dateRange.end),
                    getAvgDwellTime(dateRange.start, dateRange.end),
                    getPeakHour(dateRange.start, dateRange.end),
                    getZonePerformance(dateRange.start, dateRange.end),
                ]);

                const topZones = zonePerf.slice(0, 3).map(z => z.zone).join(', ');

                contextData = `
Real-time Data for ${dateRange.start}:
- Total Visitors: ${totalVisitors}
- Average Dwell Time: ${avgDwell.toFixed(1)} minutes
- Peak Hour: ${peakHour}:00
- Top Zones: ${topZones || 'N/A'}
- Zone Performance: ${zonePerf.slice(0, 5).map(z => `${z.zone} (${z.visitors} visitors)`).join(', ')}
`;
            }
        } else if (dataSource === 'hourly') {
            // Use hourly aggregated data
            const hourlySummary = await getHourlySummary(dateRange.start, dateRange.end);
            if (hourlySummary.length > 0) {
                const totalVisitors = hourlySummary.reduce((sum, h) => sum + (h.unique_shoppers || 0), 0);
                const avgDwell = hourlySummary.reduce((sum, h) => sum + (parseFloat(h.avg_dwell_minutes) || 0), 0) / hourlySummary.length;

                contextData = `
Hourly Summary for ${dateRange.start} to ${dateRange.end}:
- Hours with data: ${hourlySummary.length}
- Total Visitors: ${totalVisitors}
- Average Dwell Time: ${avgDwell.toFixed(1)} minutes
- Hourly Breakdown: ${hourlySummary.slice(0, 5).map(h => `${h.hour}:00 (${h.unique_shoppers} visitors)`).join(', ')}
`;
            } else {
                contextData = `No hourly data available for the selected range.`;
            }
        } else {
            // Use raw data queries
            const [totalVisitors, avgDwell, peakHour, zonePerf] = await Promise.all([
                getTotalVisitors(dateRange.start, dateRange.end),
                getAvgDwellTime(dateRange.start, dateRange.end),
                getPeakHour(dateRange.start, dateRange.end),
                getZonePerformance(dateRange.start, dateRange.end),
            ]);

            const topZones = zonePerf.slice(0, 3).map(z => z.zone).join(', ');

            contextData = `
Real-time Data for ${dateRange.start} to ${dateRange.end}:
- Total Visitors: ${totalVisitors}
- Average Dwell Time: ${avgDwell.toFixed(1)} minutes
- Peak Hour: ${peakHour}:00
- Top Zones: ${topZones || 'N/A'}
- Zone Performance: ${zonePerf.slice(0, 5).map(z => `${z.zone} (${z.visitors} visitors)`).join(', ')}
`;
        }

        // Build messages for chat
        const messages: ChatMessage[] = [
            { role: 'system', content: buildAnalyticsSystemPrompt() },
            { role: 'system', content: `Current store data:\n${contextData}` },
            ...history.map(h => ({ role: h.role as 'user' | 'assistant', content: h.content })),
            { role: 'user', content: question },
        ];

        // Generate response
        const response = await chat(messages, {
            model: 'gpt-4o-mini',
            maxTokens: 500,
            temperature: 0.7,
        });

        return NextResponse.json({
            answer: response.text,
            dataSource,
            dateRange,
            tokens_used: response.usage.promptTokens + response.usage.completionTokens,
        });

    } catch (error) {
        console.error('AI chat error:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        const errorStack = error instanceof Error ? error.stack : '';
        console.error('Error stack:', errorStack);
        return NextResponse.json(
            { error: 'Failed to process chat request', details: errorMessage },
            { status: 500 }
        );
    }
}
