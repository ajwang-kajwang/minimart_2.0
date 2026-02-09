'use client';

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface HourlyTrafficChartProps {
    data: Array<{
        hour: number;
        visitors: number;
    }>;
}

export default function HourlyTrafficChart({ data }: HourlyTrafficChartProps) {
    const formattedData = data.map(item => ({
        ...item,
        hourLabel: `${item.hour}:00`,
    }));

    return (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 h-80">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Hourly Traffic</h3>
            {data.length === 0 ? (
                <div className="h-56 flex items-center justify-center text-gray-500">
                    No traffic data available
                </div>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={formattedData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                            <linearGradient id="colorVisitors" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="#14b8a6" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="#14b8a6" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                        <XAxis
                            dataKey="hourLabel"
                            tick={{ fontSize: 12 }}
                            tickLine={false}
                            axisLine={{ stroke: '#e0e0e0' }}
                        />
                        <YAxis
                            tick={{ fontSize: 12 }}
                            tickLine={false}
                            axisLine={{ stroke: '#e0e0e0' }}
                            allowDecimals={false}
                        />
                        <Tooltip
                            contentStyle={{
                                borderRadius: '8px',
                                border: 'none',
                                boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)'
                            }}
                        />
                        <Area
                            type="monotone"
                            dataKey="visitors"
                            stroke="#14b8a6"
                            strokeWidth={2}
                            fill="url(#colorVisitors)"
                        />
                    </AreaChart>
                </ResponsiveContainer>
            )}
        </div>
    );
}
