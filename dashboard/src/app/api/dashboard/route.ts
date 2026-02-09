import { NextResponse } from 'next/server';
import {
    getDataDateRange,
    getTotalVisitors,
    getAvgDwellTime,
    getPeakHour,
    getHourlyTraffic,
    getShelfPerformance,
    getHeatmapData,
    getShopperShelfPaths,
    getZones,
    getSensorAverages,
    getShelfCategoriesMap,
    getKPIComparison,
} from '@/lib/db';

// Format date to YYYY-MM-DD string (avoid timezone conversion issues)
function formatDate(date: Date | string | null): string {
    if (!date) return '';
    if (typeof date === 'string') {
        // If already a string, extract just the date part
        return date.split('T')[0];
    }
    // Use local date components to avoid UTC conversion shifting the date
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

export async function GET(request: Request) {
    const { searchParams } = new URL(request.url);
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');

    try {
        // Get date range from database
        const dateRange = await getDataDateRange();

        // Format the available date range (from database)
        const availableMin = formatDate(dateRange.min_date);
        const availableMax = formatDate(dateRange.max_date);

        // Check if database has no data
        if (!availableMin || !availableMax) {
            const today = new Date().toISOString().split('T')[0];
            // Return empty data structure when no data exists
            return NextResponse.json({
                dateRange: {
                    start: today,
                    end: today,
                    available: {
                        min: today,
                        max: today,
                    },
                },
                kpis: {
                    uniqueShoppers: 0,
                    avgDwellTime: 0,
                    peakHour: null,
                    avgTemp: null,
                    avgHumidity: null,
                },
                hourlyTraffic: [],
                zonePerformance: [],
                heatmapData: [],
                shopperPaths: [],
                zones: await getZones(),
                shelfCategories: await getShelfCategoriesMap(),
                isEmpty: true, // Flag to indicate no data
            });
        }

        // Use provided dates or fall back to latest date only (for AI insights consistency)
        const effectiveStartDate = startDate || availableMax;
        const effectiveEndDate = endDate || availableMax;

        // Fetch all data in parallel
        const [
            totalVisitors,
            avgDwellTime,
            peakHour,
            hourlyTraffic,
            zonePerformance,
            heatmapData,
            shopperPaths,
            zones,
            sensorAverages,
            shelfCategories,
        ] = await Promise.all([
            getTotalVisitors(effectiveStartDate, effectiveEndDate),
            getAvgDwellTime(effectiveStartDate, effectiveEndDate),
            getPeakHour(effectiveStartDate, effectiveEndDate),
            getHourlyTraffic(effectiveStartDate, effectiveEndDate),
            getShelfPerformance(effectiveStartDate, effectiveEndDate),
            getHeatmapData(effectiveStartDate, effectiveEndDate),
            getShopperShelfPaths(effectiveStartDate, effectiveEndDate),
            getZones(),
            getSensorAverages(effectiveStartDate, effectiveEndDate),
            getShelfCategoriesMap(),
        ]);

        // Fetch KPI comparison data
        const kpiComparison = await getKPIComparison(effectiveStartDate, effectiveEndDate);

        return NextResponse.json({
            dateRange: {
                start: effectiveStartDate,
                end: effectiveEndDate,
                available: {
                    min: availableMin,
                    max: availableMax,
                },
            },
            kpis: {
                uniqueShoppers: totalVisitors,
                avgDwellTime: Math.round(avgDwellTime * 10) / 10,
                peakHour,
                avgTemp: sensorAverages?.avg_temp ? parseFloat(sensorAverages.avg_temp) : null,
                avgHumidity: sensorAverages?.avg_humidity ? parseFloat(sensorAverages.avg_humidity) : null,
            },
            kpiChanges: {
                visitorsChange: kpiComparison.visitorsChange !== null
                    ? Math.round(kpiComparison.visitorsChange * 10) / 10
                    : null,
                dwellTimeChange: kpiComparison.dwellTimeChange !== null
                    ? Math.round(kpiComparison.dwellTimeChange * 10) / 10
                    : null,
                tempChange: kpiComparison.tempChange !== null
                    ? Math.round(kpiComparison.tempChange * 10) / 10
                    : null,
                comparisonLabel: kpiComparison.comparisonLabel,
            },
            hourlyTraffic,
            zonePerformance,
            heatmapData,
            shopperPaths,
            zones,
            shelfCategories,
        });
    } catch (error) {
        console.error('Dashboard data fetch error:', error);
        return NextResponse.json(
            { error: 'Failed to fetch dashboard data' },
            { status: 500 }
        );
    }
}
