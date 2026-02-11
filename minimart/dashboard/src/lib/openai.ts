import OpenAI from 'openai';

// Lazy initialization of OpenAI client to support build without API key
let openaiClient: OpenAI | null = null;

function getOpenAIClient(): OpenAI {
    if (!openaiClient) {
        if (!process.env.OPENAI_API_KEY) {
            throw new Error('OPENAI_API_KEY environment variable is not set');
        }
        openaiClient = new OpenAI({
            apiKey: process.env.OPENAI_API_KEY,
        });
    }
    return openaiClient;
}

export interface ChatMessage {
    role: 'system' | 'user' | 'assistant';
    content: string;
}

export interface ChatOptions {
    model?: string;
    maxTokens?: number;
    temperature?: number;
}

/**
 * Generate text completion using OpenAI API
 */
export async function generateText(
    prompt: string,
    options: ChatOptions = {}
): Promise<{ text: string; usage: { promptTokens: number; completionTokens: number } }> {
    const {
        model = 'gpt-5.2-instant',
        maxTokens = 1000,
        temperature = 0.7,
    } = options;

    const response = await getOpenAIClient().chat.completions.create({
        model,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: maxTokens,
        temperature,
    });

    return {
        text: response.choices[0]?.message?.content || '',
        usage: {
            promptTokens: response.usage?.prompt_tokens || 0,
            completionTokens: response.usage?.completion_tokens || 0,
        },
    };
}

/**
 * Generate chat completion with conversation history
 */
export async function chat(
    messages: ChatMessage[],
    options: ChatOptions = {}
): Promise<{ text: string; usage: { promptTokens: number; completionTokens: number } }> {
    const {
        model = 'gpt-5.2-instant',
        maxTokens = 1000,
        temperature = 0.7,
    } = options;

    const response = await getOpenAIClient().chat.completions.create({
        model,
        messages,
        max_tokens: maxTokens,
        temperature,
    });

    return {
        text: response.choices[0]?.message?.content || '',
        usage: {
            promptTokens: response.usage?.prompt_tokens || 0,
            completionTokens: response.usage?.completion_tokens || 0,
        },
    };
}

/**
 * Build system prompt for retail analytics assistant
 */
export function buildAnalyticsSystemPrompt(): string {
    return `You are an AI retail analytics assistant for a minimart store. Your role is to:
1. Analyze store traffic and customer behavior data
2. Provide actionable insights for store operations
3. Answer questions about store performance metrics
4. Make recommendations based on data patterns

Guidelines:
- Be concise and data-driven in your responses
- Use bullet points for clarity when listing insights
- Include specific numbers and percentages when available
- Focus on actionable recommendations
- Keep responses under 200 words unless more detail is requested`;
}

/**
 * Build prompt for daily summary generation
 */
export function buildDailySummaryPrompt(data: {
    date: string;
    totalVisitors: number;
    uniqueShoppers: number;
    avgDwellMinutes: number;
    peakHour: number;
    topZones: string[];
    visitorsVsYesterday: number | null;
    visitorsVsLastWeek: number | null;
    avgTemp: number | null;
}): string {
    const comparison = data.visitorsVsYesterday !== null
        ? `${data.visitorsVsYesterday > 0 ? '+' : ''}${data.visitorsVsYesterday}% vs yesterday`
        : 'no comparison data';

    return `Analyze this retail store data and provide insights:

Date: ${data.date}
Total Tracking Events: ${data.totalVisitors} (position data points)
Unique Shoppers: ${data.uniqueShoppers}
Average Dwell Time: ${data.avgDwellMinutes} minutes
Peak Hour: ${data.peakHour}:00
Top Shelves: ${data.topZones.join(', ')}
Change: ${comparison}
${data.avgTemp ? `Store Temperature: ${data.avgTemp}°C` : ''}

Provide:
1. A brief summary (2-3 sentences)
2. 3 key highlights as bullet points
3. 2 operational recommendations

Format your response as JSON with keys: summary, highlights (array), recommendations (array)`;
}
