// MOCK DATABASE ADAPTER (Demo Mode)
// This file replaces real SQL queries with static data to allow
// the dashboard to load without a local PostgreSQL server.

export interface CameraData {
  id: number;
  time: Date;
  shopper_id: number;
  zone_id: number;
  x: number;
  y: number;
}

export interface ZoneDim {
  id: number;
  zone_name: string;
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
}

export interface ShelfCategory {
  shelf_name: string;
  category: string;
  display_order: number;
}

// ---------------------------------------------------------
// MOCK DATA GENERATORS
// ---------------------------------------------------------

export async function getShelfCategories(): Promise<ShelfCategory[]> {
  return [
    { shelf_name: 'Shelf A', category: 'Beverages', display_order: 1 },
    { shelf_name: 'Shelf B', category: 'Snacks', display_order: 2 },
    { shelf_name: 'Shelf C', category: 'Electronics', display_order: 3 },
  ];
}

export async function getShelfCategoriesMap(): Promise<Record<string, string>> {
  return {
    'Shelf A': 'Beverages',
    'Shelf B': 'Snacks',
    'Shelf C': 'Electronics',
  };
}

export async function getDataDateRange() {
  const today = new Date();
  const lastWeek = new Date(today);
  lastWeek.setDate(today.getDate() - 7);
  
  return {
    min_date: lastWeek,
    max_date: today,
    total_shoppers: 1250
  };
}

export async function getTotalVisitors(startDate: string, endDate: string) {
  return 142; // Mock daily count
}

export async function getAvgDwellTime(startDate: string, endDate: string) {
  return 4.5; // Mock minutes
}

export async function getPeakHour(startDate: string, endDate: string) {
  return 13; // 1 PM
}

export async function getKPIComparison(startDate: string, endDate: string) {
  return {
    visitorsChange: 12.5,
    dwellTimeChange: -5.2,
    tempChange: 0.5,
    comparisonLabel: 'vs previous period',
    prevPeriod: { start: '2023-01-01', end: '2023-01-02' },
  };
}

export async function getHourlyTraffic(startDate: string, endDate: string) {
  const hours = [];
  for (let i = 8; i <= 20; i++) {
    hours.push({
      hour: i,
      visitors: Math.floor(10 + Math.random() * 50)
    });
  }
  return hours;
}

export async function getDailyBreakdown(startDate: string, endDate: string) {
  return [
    { date: '2025-01-01', visitors: 120, avg_dwell: 5.2 },
    { date: '2025-01-02', visitors: 145, avg_dwell: 4.8 },
    { date: '2025-01-03', visitors: 132, avg_dwell: 5.5 },
  ];
}

export async function getZonePerformance(startDate: string, endDate: string) {
  return [
    { zone: 'Beverages', visitors: 85, events: 200 },
    { zone: 'Snacks', visitors: 60, events: 150 },
    { zone: 'Checkout', visitors: 120, events: 120 },
  ];
}

export async function getShelfPerformance(startDate: string, endDate: string) {
  return [
    { zone: 'Shelf A', visitors: 45, events: 90 },
    { zone: 'Shelf B', visitors: 30, events: 60 },
  ];
}

export async function getHeatmapData(startDate: string, endDate: string) {
  return []; // Empty to prevent render errors
}

export async function getShopperShelfPaths(startDate: string, endDate: string) {
  return [];
}

export async function getZones() {
  return [
    { id: 1, zone_name: 'Entrance', x_min: 0, x_max: 100, y_min: 0, y_max: 100 },
    { id: 2, zone_name: 'Shelf A', x_min: 200, x_max: 300, y_min: 200, y_max: 300 },
  ];
}

export async function getSensorAverages(startDate: string, endDate: string) {
  return { avg_temp: 22.5, avg_humidity: 45.0 };
}

export async function getAvgTemperature(startDate: string, endDate: string): Promise<number | null> {
  return 22.5;
}

// Mock AI Summaries
export async function getDailySummary(startDate: string, endDate?: string) {
  return {
    date: startDate,
    total_records: 5000,
    unique_shoppers: 142,
    avg_dwell_minutes: 4.5,
    peak_hour: 13,
    hourly_traffic: [],
    zone_ranking: [],
    top_zones: ['Beverages', 'Snacks'],
    avg_zones_visited: 2.1,
    avg_temp: 22.5,
    visitors_vs_yesterday: 5.0,
    visitors_vs_last_week: 10.0
  };
}

export async function getRealTimeSummary(startDate: string, endDate?: string) {
  return getDailySummary(startDate, endDate);
}

export async function getHourlySummary(startDate: string, endDate: string) {
  return [];
}

export async function getDailyAiInsights(date: string) {
  return null;
}

export async function saveDailyAiInsights(insights: any): Promise<void> {
  return;
}

export function selectDataSource(startDate: string, endDate: string): 'raw' | 'hourly' | 'daily' {
  return 'raw';
}

// Mock the Pool so other files don't crash
const pool = { query: async () => ({ rows: [] }) };
export default pool;