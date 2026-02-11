'use client';

import { useMemo } from 'react';

interface HeatmapCell {
    zone_id: number;
    shelf_name: string;
    grid_col: number;
    grid_row: number;
    count: number;
}

interface StoreHeatmapProps {
    data: HeatmapCell[];
    zones: Array<{
        id: number;
        zone_name: string;
        x_min: number;
        x_max: number;
        y_min: number;
        y_max: number;
    }>;
    shelfCategories?: Record<string, string>;
    fullHeight?: boolean;
}

// Store layout (category is now dynamic from database)
const STORE_LAYOUT = {
    shelves: [
        { id: 'shelf1a', label: '1A', x: 17, y: 0, width: 12.5, height: 44 },
        { id: 'shelf1b', label: '1B', x: 29.5, y: 0, width: 12.5, height: 44 },
        { id: 'shelf2a', label: '2A', x: 61, y: 0, width: 12.5, height: 44 },
        { id: 'shelf2b', label: '2B', x: 73.5, y: 0, width: 12.5, height: 44 },
        { id: 'shelf3a', label: '3A', x: 17, y: 57, width: 12.5, height: 43 },
        { id: 'shelf3b', label: '3B', x: 29.5, y: 57, width: 12.5, height: 43 },
        { id: 'shelf4a', label: '4A', x: 61, y: 57, width: 12.5, height: 43 },
        { id: 'shelf4b', label: '4B', x: 73.5, y: 57, width: 12.5, height: 43 },
    ],
    zones: [
        { id: 'counter', label: 'Counter', x: 0, y: 0, width: 16, height: 44 },
        { id: 'zone1', label: 'Zone 1', x: 0, y: 57, width: 16, height: 43 },
        { id: 'zone2', label: 'Zone 2', x: 43, y: 57, width: 17, height: 43 },
        { id: 'zone3', label: 'Zone 3', x: 87, y: 57, width: 13, height: 43 },
        { id: 'zone4', label: 'Zone 4', x: 87, y: 0, width: 13, height: 44 },
        { id: 'zone5', label: 'Zone 5', x: 43, y: 0, width: 17, height: 44 },
    ],
    aisle: { x: 0, y: 45, width: 100, height: 11 },
};

// Shelf colors (must match ShopperPathsChart)
const SHELF_COLORS = {
    a: '#374151',
    b: '#4b5563',
};

const GRID_COLS = 4;
const GRID_ROWS = 8;

// Helper to get category from shelf label
const getShelfCategory = (label: string, categories: Record<string, string>): string => {
    return categories[`Shelf ${label}`] || label;
};

export default function StoreHeatmap({ data, shelfCategories = {}, fullHeight = false }: StoreHeatmapProps) {
    // Process data: create heatpoints for gradient effect
    const { heatPoints, shelfTotals } = useMemo(() => {
        const points: Array<{ shelfId: string; x: number; y: number; intensity: number }> = [];
        const totals = new Map<string, number>();
        let maxCount = 0;

        // First pass: find max count and calculate shelf totals
        data.forEach((cell) => {
            maxCount = Math.max(maxCount, cell.count);
            const shelfName = cell.shelf_name?.trim();
            if (shelfName) {
                totals.set(shelfName, (totals.get(shelfName) || 0) + cell.count);
            }
        });

        // Second pass: create normalized heat points (per-cell intensity)
        data.forEach((cell) => {
            const shelfName = cell.shelf_name?.trim();
            if (!shelfName) return;

            const shelf = STORE_LAYOUT.shelves.find(s => `Shelf ${s.label}` === shelfName);
            if (!shelf) return;

            const cellWidth = shelf.width / GRID_COLS;
            const cellHeight = shelf.height / GRID_ROWS;
            const x = shelf.x + (cell.grid_col + 0.5) * cellWidth;
            const y = shelf.y + (cell.grid_row + 0.5) * cellHeight;

            points.push({
                shelfId: shelf.id,
                x,
                y,
                // Intensity based on individual cell count (local hotspot)
                intensity: maxCount > 0 ? cell.count / maxCount : 0,
            });
        });

        return { heatPoints: points, shelfTotals: totals };
    }, [data]);

    // Group heat points by shelf
    const heatPointsByShelf = useMemo(() => {
        const grouped = new Map<string, typeof heatPoints>();
        heatPoints.forEach(point => {
            if (!grouped.has(point.shelfId)) {
                grouped.set(point.shelfId, []);
            }
            grouped.get(point.shelfId)!.push(point);
        });
        return grouped;
    }, [heatPoints]);

    // Rank shelves by total browsing count (for ranking display, no numbers)
    const rankedShelves = useMemo(() => {
        return STORE_LAYOUT.shelves
            .map(shelf => ({
                ...shelf,
                count: shelfTotals.get(`Shelf ${shelf.label}`) || 0
            }))
            .sort((a, b) => b.count - a.count);
    }, [shelfTotals]);

    return (
        <div className={`bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col ${fullHeight ? 'h-[calc(100vh-180px)]' : 'h-96'}`}>
            {!fullHeight && <h3 className="text-lg font-semibold text-gray-800 mb-4 flex-shrink-0">Shelf Heatmap</h3>}
            {data.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                    No heatmap data available
                </div>
            ) : (
                <div className="relative flex-1 bg-gray-50 rounded-lg overflow-hidden border border-gray-200">
                    <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                        <defs>
                            <filter id="heatBlur" x="-50%" y="-50%" width="200%" height="200%">
                                <feGaussianBlur in="SourceGraphic" stdDeviation="1.5" />
                            </filter>

                            {STORE_LAYOUT.shelves.map((shelf) => (
                                <clipPath key={`clip-${shelf.id}`} id={`clip-${shelf.id}`}>
                                    <rect
                                        x={shelf.x}
                                        y={100 - shelf.y - shelf.height}
                                        width={shelf.width}
                                        height={shelf.height}
                                    />
                                </clipPath>
                            ))}
                        </defs>

                        <rect x="0" y="0" width="100" height="100" fill="#f8fafc" />

                        {/* Central Aisle */}
                        <rect
                            x={STORE_LAYOUT.aisle.x}
                            y={100 - STORE_LAYOUT.aisle.y - STORE_LAYOUT.aisle.height}
                            width={STORE_LAYOUT.aisle.width}
                            height={STORE_LAYOUT.aisle.height}
                            fill="#fef3c7"
                            stroke="#fcd34d"
                            strokeWidth="0.3"
                        />
                        <text
                            x="50"
                            y={100 - STORE_LAYOUT.aisle.y - STORE_LAYOUT.aisle.height / 2}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize="2.5"
                            fill="#d97706"
                        >
                            Aisle
                        </text>

                        {/* Shelves with gradient heatmap */}
                        {STORE_LAYOUT.shelves.map((shelf) => {
                            const shelfPoints = heatPointsByShelf.get(shelf.id) || [];

                            const isASide = shelf.id.endsWith('a');
                            return (
                                <g key={shelf.id}>
                                    <rect
                                        x={shelf.x}
                                        y={100 - shelf.y - shelf.height}
                                        width={shelf.width}
                                        height={shelf.height}
                                        fill={isASide ? SHELF_COLORS.a : SHELF_COLORS.b}
                                        stroke="#1f2937"
                                        strokeWidth="0.3"
                                    />

                                    <g clipPath={`url(#clip-${shelf.id})`}>
                                        {shelfPoints.map((point, idx) => {
                                            let color: string;
                                            if (point.intensity < 0.25) {
                                                color = '#22c55e';
                                            } else if (point.intensity < 0.5) {
                                                color = '#eab308';
                                            } else if (point.intensity < 0.75) {
                                                color = '#f97316';
                                            } else {
                                                color = '#ef4444';
                                            }

                                            const radius = 2 + point.intensity * 4;

                                            return (
                                                <circle
                                                    key={idx}
                                                    cx={point.x}
                                                    cy={100 - point.y}
                                                    r={radius}
                                                    fill={color}
                                                    opacity={0.6 + point.intensity * 0.3}
                                                    filter="url(#heatBlur)"
                                                />
                                            );
                                        })}
                                    </g>

                                    <text
                                        x={shelf.x + shelf.width / 2}
                                        y={100 - shelf.y - shelf.height / 2 - 2}
                                        textAnchor="middle"
                                        dominantBaseline="middle"
                                        fontSize="2.8"
                                        fill="#fff"
                                        fontWeight="700"
                                    >
                                        {shelf.label}
                                    </text>
                                    <text
                                        x={shelf.x + shelf.width / 2}
                                        y={100 - shelf.y - shelf.height / 2 + 3}
                                        textAnchor="middle"
                                        dominantBaseline="middle"
                                        fontSize="1.6"
                                        fill="#94a3b8"
                                    >
                                        {getShelfCategory(shelf.label, shelfCategories)}
                                    </text>
                                </g>
                            );
                        })}

                        {/* Zones */}
                        {STORE_LAYOUT.zones.map((zone) => (
                            <g key={zone.id}>
                                <rect
                                    x={zone.x}
                                    y={100 - zone.y - zone.height}
                                    width={zone.width}
                                    height={zone.height}
                                    fill="rgba(229, 231, 235, 0.5)"
                                    stroke="#d1d5db"
                                    strokeWidth="0.3"
                                />
                                <text
                                    x={zone.x + zone.width / 2}
                                    y={100 - zone.y - zone.height / 2}
                                    textAnchor="middle"
                                    dominantBaseline="middle"
                                    fontSize="2.2"
                                    fill="#6b7280"
                                >
                                    {zone.label}
                                </text>
                            </g>
                        ))}
                    </svg>

                    {/* Only show overlays in fullHeight (detail view), not in overview */}
                    {fullHeight && (
                        <>
                            {/* Color Legend */}
                            <div className="absolute bottom-2 right-2 bg-white/95 rounded-lg px-3 py-2 shadow-sm border border-gray-200">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs text-gray-500">Low</span>
                                    <div className="w-16 h-3 rounded" style={{
                                        background: 'linear-gradient(to right, #22c55e, #eab308, #f97316, #ef4444)'
                                    }}></div>
                                    <span className="text-xs text-gray-500">High</span>
                                </div>
                            </div>

                            {/* Top Shelves Ranking (no numbers, just shelf names in order) */}
                            <div className="absolute top-2 left-2 bg-white/95 rounded-lg px-3 py-2 shadow-sm border border-gray-200">
                                <div className="text-xs text-gray-600 mb-1 font-medium">🔥 Top Shelves</div>
                                {rankedShelves.map((shelf, idx) => (
                                    <div key={shelf.label} className="flex items-center gap-2 text-xs">
                                        <div
                                            className="w-2 h-2 rounded-full"
                                            style={{
                                                backgroundColor: idx === 0 ? '#ef4444' : idx === 1 ? '#f97316' : idx === 2 ? '#eab308' : '#22c55e'
                                            }}
                                        />
                                        <span className="text-gray-700">{getShelfCategory(shelf.label, shelfCategories)}</span>
                                        <span className="text-gray-400">({shelf.label})</span>
                                    </div>
                                ))}
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}
