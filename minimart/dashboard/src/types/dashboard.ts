export interface DashboardData {
    dateRange: {
        start: string;
        end: string;
        available: {
            min: string;
            max: string;
        };
    };
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
    hourlyTraffic: Array<{
        hour: number;
        visitors: number;
    }>;
    zonePerformance: Array<{
        zone: string;
        visitors: number;
        events: number;
    }>;
    heatmapData: Array<{
        zone_id: number;
        shelf_name: string;
        grid_col: number;
        grid_row: number;
        count: number;
    }>;
    shopperPaths: Array<{
        shopper_id: number;
        points: Array<{ x: number; y: number; time: string; zone: string }>;
        shelves: Array<{ zone: string; time: string }>;
    }>;
    zones: Array<{
        id: number;
        zone_name: string;
        x_min: number;
        x_max: number;
        y_min: number;
        y_max: number;
    }>;
    shelfCategories: Record<string, string>;
}
