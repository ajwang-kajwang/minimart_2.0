import { Users, Clock, TrendingUp, Thermometer, ArrowUp, ArrowDown, Minus } from 'lucide-react';

interface KPICardsProps {
    kpis: {
        uniqueShoppers: number;
        avgDwellTime: number;
        peakHour: number;
        avgTemp: number | null;
        avgHumidity: number | null;
    };
    kpiChanges?: {
        visitorsChange: number | null;
        dwellTimeChange: number | null;
        tempChange: number | null;
        comparisonLabel: string;
    };
    dateRange?: {
        start: string;
        end: string;
    };
}

export default function KPICards({ kpis, kpiChanges, dateRange }: KPICardsProps) {
    const isSingleDay = !dateRange || dateRange.start === dateRange.end;

    const formatPeakHour = (hour: number) => {
        if (hour === 0) return '12:00 AM';
        if (hour === 12) return '12:00 PM';
        if (hour < 12) return `${hour}:00 AM`;
        return `${hour - 12}:00 PM`;
    };

    const formatDwellTime = (minutes: number) => {
        if (minutes >= 60) {
            const hours = Math.floor(minutes / 60);
            const mins = Math.round(minutes % 60);
            return `${hours}h ${mins}m`;
        }
        return `${Math.round(minutes)}m`;
    };

    const formatChange = (value: number | null | undefined, isTemp: boolean = false) => {
        if (value === null || value === undefined) return null;

        const absValue = Math.abs(value);
        const formatted = isTemp
            ? `${absValue.toFixed(1)}°C`
            : `${absValue.toFixed(1)}%`;

        if (value > 0.5) {
            return { direction: 'up' as const, value: formatted };
        } else if (value < -0.5) {
            return { direction: 'down' as const, value: formatted };
        }
        return { direction: 'neutral' as const, value: formatted };
    };

    const cards = [
        {
            title: 'Total Shoppers',
            value: kpis.uniqueShoppers.toLocaleString(),
            icon: Users,
            color: 'text-blue-600',
            bgColor: 'bg-blue-50',
            change: formatChange(kpiChanges?.visitorsChange),
            positiveIsGood: true,
        },
        {
            title: 'Avg Dwell Time',
            value: formatDwellTime(kpis.avgDwellTime),
            icon: Clock,
            color: 'text-green-600',
            bgColor: 'bg-green-50',
            change: formatChange(kpiChanges?.dwellTimeChange),
            positiveIsGood: true, // Longer dwell time is generally good
        },
        {
            title: 'Peak Hour',
            value: formatPeakHour(kpis.peakHour),
            icon: TrendingUp,
            color: 'text-purple-600',
            bgColor: 'bg-purple-50',
            change: null, // No change tracking for peak hour
            positiveIsGood: true,
        },
        {
            title: 'Avg Temperature',
            value: kpis.avgTemp ? `${kpis.avgTemp}°C` : 'N/A',
            icon: Thermometer,
            color: 'text-orange-600',
            bgColor: 'bg-orange-50',
            change: formatChange(kpiChanges?.tempChange, true),
            positiveIsGood: null, // Temperature change is neutral
        },
    ];

    const getChangeColor = (direction: 'up' | 'down' | 'neutral', positiveIsGood: boolean | null) => {
        if (positiveIsGood === null || direction === 'neutral') {
            return 'text-gray-500';
        }
        if (direction === 'up') {
            return positiveIsGood ? 'text-green-600' : 'text-red-600';
        }
        return positiveIsGood ? 'text-red-600' : 'text-green-600';
    };

    const getChangeIcon = (direction: 'up' | 'down' | 'neutral') => {
        if (direction === 'up') return ArrowUp;
        if (direction === 'down') return ArrowDown;
        return Minus;
    };

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {cards.map((card) => (
                <div
                    key={card.title}
                    className="bg-white rounded-xl p-5 shadow-sm border border-gray-100"
                >
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-sm text-gray-500">{card.title}</span>
                        <div className={`p-2 rounded-lg ${card.bgColor}`}>
                            <card.icon className={`h-5 w-5 ${card.color}`} />
                        </div>
                    </div>
                    <p className="text-2xl font-bold text-gray-800 mb-1">{card.value}</p>
                    {card.change && kpiChanges && (
                        <div className={`flex items-center gap-1 text-sm ${getChangeColor(card.change.direction, card.positiveIsGood)}`}>
                            {(() => {
                                const ChangeIcon = getChangeIcon(card.change.direction);
                                return <ChangeIcon className="h-4 w-4" />;
                            })()}
                            <span>{card.change.direction === 'up' ? '+' : card.change.direction === 'down' ? '-' : ''}{card.change.value}</span>
                            <span className="text-gray-400 ml-1">{kpiChanges.comparisonLabel}</span>
                        </div>
                    )}
                    {!card.change && card.title !== 'Peak Hour' && kpiChanges && (
                        <div className="text-sm text-gray-400">No comparison data</div>
                    )}
                </div>
            ))}
        </div>
    );
}
