'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/AuthContext';
import { DashboardData } from '@/types/dashboard';
import KPICards from '@/components/KPICards';
import HourlyTrafficChart from '@/components/HourlyTrafficChart';
import ShelfPerformanceTable from '@/components/ZonePerformanceTable';
import StoreHeatmap from '@/components/StoreHeatmap';
import ShopperPathsChart from '@/components/ShopperPathsChart';
import AIAssistant from '@/components/AIAssistant';
import LiveStream from '@/components/LiveStream';
import DateRangeSelector from '@/components/DateRangeSelector';
import Sidebar, { ViewType } from '@/components/Sidebar';
import { RefreshCw, LogOut, Store, ChevronDown } from 'lucide-react';


export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<{ start: string; end: string } | null>(null);
  const [currentView, setCurrentView] = useState<ViewType>('overview');
  const [selectedStore, setSelectedStore] = useState('Bentley-ICP');

  // Available stores (for future expansion)
  const stores = [
    'Bentley-ICP',
    'Perth CBD (Coming Soon)',
    'Fremantle (Coming Soon)',
  ];

  const { isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [authLoading, isAuthenticated, router]);

  const fetchData = useCallback(async (startDate?: string, endDate?: string) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (startDate) params.set('startDate', startDate);
      if (endDate) params.set('endDate', endDate);

      const url = `/api/dashboard${params.toString() ? `?${params.toString()}` : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch data');
      const result = await response.json();
      setData(result);
      setDateRange({ start: result.dateRange.start, end: result.dateRange.end });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleDateRangeChange = (start: string, end: string) => {
    setDateRange({ start, end });
    fetchData(start, end);
  };

  // Show loading while checking auth
  if (authLoading || (!authLoading && !isAuthenticated)) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  if (loading && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center bg-red-50 p-8 rounded-lg">
          <p className="text-red-600 mb-4">Error: {error}</p>
          <button
            onClick={() => fetchData()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const renderContent = () => {
    switch (currentView) {
      case 'live':
        return (
          <div className="h-[calc(100vh-180px)]">
            <LiveStream />
          </div>
        );

      case 'heatmap':
        return (
          <StoreHeatmap data={data.heatmapData} zones={data.zones} shelfCategories={data.shelfCategories} fullHeight={true} />
        );

      case 'paths':
        return (
          <ShopperPathsChart data={data.shopperPaths} shelfCategories={data.shelfCategories} fullHeight={true} />

        );

      case 'traffic':
        return (
          <div className="space-y-6">
            <KPICards kpis={data.kpis} kpiChanges={data.kpiChanges} dateRange={data.dateRange} />
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
              <div className="lg:col-span-3">
                <HourlyTrafficChart data={data.hourlyTraffic} />
              </div>
              <div className="lg:col-span-2">
                <ShelfPerformanceTable data={data.zonePerformance} shelfCategories={data.shelfCategories} />
              </div>
            </div>
          </div>
        );

      case 'ai':
        return (
          <div className="h-[calc(100vh-180px)]">
            <AIAssistant dateRange={data.dateRange} kpis={data.kpis} />
          </div>
        );

      case 'overview':
      default:
        return (
          <>
            {/* AI Assistant */}
            <section className="mb-6">
              <AIAssistant dateRange={data.dateRange} kpis={data.kpis} />
            </section>

            {/* KPI Cards */}
            <section className="mb-6">
              <KPICards kpis={data.kpis} kpiChanges={data.kpiChanges} dateRange={data.dateRange} />
            </section>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
              <div className="lg:col-span-3">
                <HourlyTrafficChart data={data.hourlyTraffic} />
              </div>
              <div className="lg:col-span-2">
                <ShelfPerformanceTable data={data.zonePerformance} shelfCategories={data.shelfCategories} />
              </div>
            </div>

            {/* Heatmap and Paths Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <StoreHeatmap data={data.heatmapData} zones={data.zones} shelfCategories={data.shelfCategories} />
              <ShopperPathsChart data={data.shopperPaths} shelfCategories={data.shelfCategories} />
            </div>
          </>
        );
    }
  };

  const getViewTitle = () => {
    switch (currentView) {
      case 'live': return 'Live Feed';
      case 'heatmap': return 'Store Heatmap';
      case 'paths': return 'Customer Routes';
      case 'traffic': return 'Traffic Analysis';
      case 'ai': return 'AI Assistant';
      default: return 'Store Overview';
    }
  };

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar currentView={currentView} onViewChange={setCurrentView} />

      {/* Main Content */}
      <main className="flex-1 ml-16 lg:ml-56 p-6 transition-all duration-300 flex flex-col min-h-screen">
        {/* Header */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-800">{getViewTitle()}</h1>
            {currentView === 'overview' && (
              <div className="relative">
                <select
                  value={selectedStore}
                  onChange={(e) => setSelectedStore(e.target.value)}
                  className="appearance-none pl-8 pr-8 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-700 hover:bg-gray-50 focus:ring-2 focus:ring-teal-500 focus:border-transparent cursor-pointer"
                >
                  {stores.map((store) => (
                    <option
                      key={store}
                      value={store}
                      disabled={store.includes('Coming Soon')}
                    >
                      {store}
                    </option>
                  ))}
                </select>
                <Store className="absolute left-2.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500 pointer-events-none" />
                <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
              </div>
            )}
          </div>
          <div className="flex items-center gap-4">
            <DateRangeSelector
              availableRange={data.dateRange.available}
              currentRange={dateRange || { start: data.dateRange.start, end: data.dateRange.end }}
              onRangeChange={handleDateRangeChange}
            />
            <button
              onClick={() => dateRange ? fetchData(dateRange.start, dateRange.end) : fetchData()}
              disabled={loading}
              className="p-2 rounded-lg bg-white border border-gray-200 hover:bg-gray-50 transition-colors disabled:opacity-50"
              title="Refresh data"
            >
              <RefreshCw className={`h-5 w-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={logout}
              className="p-2 rounded-lg bg-white border border-gray-200 hover:bg-red-50 hover:border-red-200 transition-colors group"
              title="Sign out"
            >
              <LogOut className="h-5 w-5 text-gray-600 group-hover:text-red-500" />
            </button>
          </div>
        </div>

        {/* Dynamic Content */}
        <div className="flex-1">
          {renderContent()}
        </div>

        {/* Footer */}
        <footer className="mt-auto pt-6 border-t border-gray-200">
          <div className="flex items-center justify-end gap-4 text-xs text-gray-500">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
              <span>Live Data</span>
            </div>
            <span className="text-gray-300">|</span>
            <span>{data.dateRange.start === data.dateRange.end ? data.dateRange.start : `${data.dateRange.start} → ${data.dateRange.end}`}</span>
            <span className="text-gray-300">|</span>
            <span>Updated {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
          </div>
        </footer>
      </main>
    </div>
  );
}
