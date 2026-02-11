import { NextResponse } from 'next/server';
import { getDailySummary, getDailyAiInsights, saveDailyAiInsights, getShelfCategoriesMap, getRealTimeSummary } from '@/lib/db';
import { generateText, buildDailySummaryPrompt } from '@/lib/openai';

interface AiInsightsResponse {
    summary: string;
    highlights: string[];
    recommendations: string[];
}

/**
 * GET /api/ai/summary
 * Generate or retrieve cached AI insights for a date or date range
 * Single day: uses cache
 * Multi-day: generates fresh (no cache)
 */
export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const startDate = searchParams.get('start');
    const endDate = searchParams.get('end');
    // Support legacy single date param
    const legacyDate = searchParams.get('date');

    const start = startDate || legacyDate;
    const end = endDate || legacyDate;

    if (!start || !end) {
        return NextResponse.json(
            { error: 'Date parameters required (start & end, or date for single day)' },
            { status: 400 }
        );
    }

    const isSingleDay = start === end;

    try {
        // For single day, check cache first
        if (isSingleDay) {
            const cachedInsights = await getDailyAiInsights(start);
            if (cachedInsights) {
                return NextResponse.json({
                    ...cachedInsights,
                    cached: true,
                });
            }
        }

        // Get daily summary data (uses aggregated data for both single and multi-day)
        let dailySummary = await getDailySummary(start, end);

        // Fallback: If no aggregated data, compute from raw data in real-time
        if (!dailySummary) {
            dailySummary = await getRealTimeSummary(start, end);
        }

        if (!dailySummary) {
            return NextResponse.json(
                { error: `No data available for date range: ${start} to ${end}` },
                { status: 404 }
            );
        }

        // Get shelf categories from database and convert shelf names to category names
        const shelfCategories = await getShelfCategoriesMap();

        const topShelves = (dailySummary.top_zones || [])
            .filter((zone: string) => zone.startsWith('Shelf'))
            .map((zone: string) => shelfCategories[zone] || zone);

        // Build prompt with date range info
        const dateLabel = isSingleDay ? start : `${start} to ${end}`;
        const prompt = buildDailySummaryPrompt({
            date: dateLabel,
            totalVisitors: dailySummary.total_records,
            uniqueShoppers: dailySummary.unique_shoppers,
            avgDwellMinutes: dailySummary.avg_dwell_minutes,
            peakHour: dailySummary.peak_hour,
            topZones: topShelves,
            visitorsVsYesterday: dailySummary.visitors_vs_yesterday,
            visitorsVsLastWeek: dailySummary.visitors_vs_last_week,
            avgTemp: dailySummary.avg_temp,
        });

        const response = await generateText(prompt, {
            model: 'gpt-4o-mini',
            maxTokens: 500,
            temperature: 0.7,
        });

        // Parse JSON response from LLM
        let insights: AiInsightsResponse;
        try {
            // Try to extract JSON from response
            const jsonMatch = response.text.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                insights = JSON.parse(jsonMatch[0]);
            } else {
                // Fallback: structure the response manually
                insights = {
                    summary: response.text,
                    highlights: [],
                    recommendations: [],
                };
            }
        } catch {
            insights = {
                summary: response.text,
                highlights: [],
                recommendations: [],
            };
        }

        // Only cache single-day insights
        if (isSingleDay) {
            await saveDailyAiInsights({
                date: start,
                summary: insights.summary,
                highlights: insights.highlights,
                recommendations: insights.recommendations,
                model_used: 'gpt-4o-mini',
                prompt_tokens: response.usage.promptTokens,
                completion_tokens: response.usage.completionTokens,
            });
        }

        return NextResponse.json({
            date: dateLabel,
            summary: insights.summary,
            highlights: insights.highlights,
            recommendations: insights.recommendations,
            cached: false,
            tokens_used: response.usage.promptTokens + response.usage.completionTokens,
        });

    } catch (error) {
        console.error('AI summary generation error:', error);
        return NextResponse.json(
            { error: 'Failed to generate AI insights' },
            { status: 500 }
        );
    }
}

