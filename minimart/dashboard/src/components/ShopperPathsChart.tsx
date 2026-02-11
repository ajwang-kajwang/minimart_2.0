'use client';

import { useState } from 'react';

const PATH_COLORS = [
    '#3b82f6', // blue
    '#22c55e', // green
    '#f97316', // orange
    '#a855f7', // purple
    '#ef4444', // red
];


// Store layout with sub-shelves (category is now dynamic from database)
const STORE_LAYOUT = {
    shelves: [
        // Shelf 1 split vertically (Bottom left area)
        { id: 'shelf1a', label: '1A', x: 17, y: 0, width: 12.5, height: 44 },
        { id: 'shelf1b', label: '1B', x: 29.5, y: 0, width: 12.5, height: 44 },
        // Shelf 2 split vertically (Bottom right area)
        { id: 'shelf2a', label: '2A', x: 61, y: 0, width: 12.5, height: 44 },
        { id: 'shelf2b', label: '2B', x: 73.5, y: 0, width: 12.5, height: 44 },
        // Shelf 3 split vertically (Top left area)
        { id: 'shelf3a', label: '3A', x: 17, y: 57, width: 12.5, height: 43 },
        { id: 'shelf3b', label: '3B', x: 29.5, y: 57, width: 12.5, height: 43 },
        // Shelf 4 split vertically (Top right area)
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

// Shelf colors
const SHELF_COLORS = {
    a: '#374151',
    b: '#4b5563',
};

const SHELF_BY_NAME = new Map(
    STORE_LAYOUT.shelves.map((shelf) => [`Shelf ${shelf.label}`, shelf])
);

const ZONE_BY_NAME = new Map(
    STORE_LAYOUT.zones.map((zone) => [zone.label, zone])
);

const WALKABLE_ZONE_NAMES = new Set([
    'Aisle',
    'Counter',
    'Zone 1',
    'Zone 2',
    'Zone 3',
    'Zone 4',
    'Zone 5',
]);

const AISLE_BOUNDS = { yMin: 45, yMax: 56, yMid: 50 };

// Helper to get category from shelf label using categories map
const getShelfCategory = (label: string, categories: Record<string, string>): string => {
    return categories[`Shelf ${label}`] || label;
};

// Helper to get category format from zone name (e.g., "Shelf 1A" -> "Fruits (1A)")
const getShelfCategoryFormat = (zoneName: string, categories: Record<string, string>): string => {
    const shelf = SHELF_BY_NAME.get(zoneName);
    if (shelf) {
        const category = categories[zoneName] || shelf.label;
        return `${category} (${shelf.label})`;
    }
    return zoneName.replace('Shelf ', '');
};



interface ShopperPathsChartProps {
    data: Array<{
        shopper_id: number;
        points: Array<{ x: number; y: number; time: string; zone: string }>;
        shelves: Array<{ zone: string; time: string }>;
    }>;
    shelfCategories?: Record<string, string>;
    fullHeight?: boolean;
}

export default function ShopperPathsChart({ data, shelfCategories = {}, fullHeight = false }: ShopperPathsChartProps) {
    const [selectedShopperId, setSelectedShopperId] = useState<number | null>(null);

    const handleShopperClick = (shopperId: number) => {
        setSelectedShopperId(prev => prev === shopperId ? null : shopperId);
    };
    const createSvgPath = (points: Array<{ x: number; y: number }>): string => {
        if (points.length < 2) return '';

        const svgPoints = points.map((p) => ({
            x: Math.max(0, Math.min(100, p.x)),
            y: Math.max(0, Math.min(100, 100 - p.y)),
        }));

        if (svgPoints.length === 2) {
            return `M ${svgPoints[0].x.toFixed(2)} ${svgPoints[0].y.toFixed(2)} L ${svgPoints[1].x.toFixed(2)} ${svgPoints[1].y.toFixed(2)}`;
        }

        const radius = 5;
        let d = `M ${svgPoints[0].x.toFixed(2)} ${svgPoints[0].y.toFixed(2)}`;

        for (let i = 1; i < svgPoints.length - 1; i++) {
            const prev = svgPoints[i - 1];
            const curr = svgPoints[i];
            const next = svgPoints[i + 1];

            const v1x = curr.x - prev.x;
            const v1y = curr.y - prev.y;
            const v2x = next.x - curr.x;
            const v2y = next.y - curr.y;

            const len1 = Math.hypot(v1x, v1y);
            const len2 = Math.hypot(v2x, v2y);
            const r = Math.min(radius, len1 / 2, len2 / 2);

            if (r < 0.1) {
                d += ` L ${curr.x.toFixed(2)} ${curr.y.toFixed(2)}`;
                continue;
            }

            const startX = curr.x - (v1x / len1) * r;
            const startY = curr.y - (v1y / len1) * r;
            const endX = curr.x + (v2x / len2) * r;
            const endY = curr.y + (v2y / len2) * r;

            d += ` L ${startX.toFixed(2)} ${startY.toFixed(2)}`;
            d += ` Q ${curr.x.toFixed(2)} ${curr.y.toFixed(2)} ${endX.toFixed(2)} ${endY.toFixed(2)}`;
        }

        const last = svgPoints[svgPoints.length - 1];
        d += ` L ${last.x.toFixed(2)} ${last.y.toFixed(2)}`;

        return d;
    };

    const colorFor = (idx: number) => PATH_COLORS[idx % PATH_COLORS.length];
    const normalizePoints = (points: Array<{ x: number; y: number }>) => {
        const normalized: Array<{ x: number; y: number }> = [];
        for (let i = 0; i < points.length; i++) {
            const current = points[i];
            const prev = normalized[normalized.length - 1];
            if (!prev || Math.abs(prev.x - current.x) > 0.5 || Math.abs(prev.y - current.y) > 0.5) {
                normalized.push(current);
            }
        }
        return normalized;
    };



    const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

    const getWalkablePoint = (
        point: { x: number; y: number; zone: string },
        offset: number,
        aisleY: number
    ): { x: number; y: number } => {
        const zoneName = point.zone?.trim();
        if (zoneName === 'Aisle') {
            return {
                x: clamp(point.x, 0, 100),
                y: aisleY,
            };
        }

        const shelf = zoneName ? SHELF_BY_NAME.get(zoneName) : undefined;
        if (shelf) {
            const isA = shelf.label.endsWith('A');
            const edgeX = isA ? shelf.x - 0.5 : shelf.x + shelf.width + 0.5;
            return {
                x: clamp(edgeX, 0, 100),
                y: clamp(point.y, shelf.y, shelf.y + shelf.height),
            };
        }

        const zone = zoneName ? ZONE_BY_NAME.get(zoneName) : undefined;
        if (zone && WALKABLE_ZONE_NAMES.has(zoneName)) {
            return {
                x: clamp(point.x, zone.x, zone.x + zone.width),
                y: clamp(point.y, zone.y, zone.y + zone.height),
            };
        }

        return {
            x: clamp(point.x, 0, 100),
            y: clamp(point.y, 0, 100),
        };
    };

    const buildWalkablePath = (points: Array<{ x: number; y: number; zone: string }>, shopperId: number) => {
        const fullPoints = [
            { x: 8, y: 22, zone: 'Counter' },
            ...points,
            { x: 8, y: 22, zone: 'Counter' }
        ];

        if (fullPoints.length < 2) return [] as Array<{ x: number; y: number }>;
        const offset = (((shopperId * 37) % 9) - 4) * 0.6;
        const aisleY = clamp(AISLE_BOUNDS.yMid + offset, AISLE_BOUNDS.yMin + 0.4, AISLE_BOUNDS.yMax - 0.4);

        const pathPoints: Array<{ x: number; y: number }> = [];

        const projected = fullPoints.map((p) => ({
            zone: p.zone?.trim() || '',
            point: getWalkablePoint(p, offset, aisleY),
        }));

        for (let i = 0; i < projected.length - 1; i++) {
            const curr = projected[i];
            const next = projected[i + 1];
            const currPoint = curr.point;
            const nextPoint = next.point;
            const sameZone = curr.zone && curr.zone === next.zone;
            const isShelf = curr.zone.startsWith('Shelf');

            pathPoints.push(currPoint);

            if (sameZone && !isShelf) {
                continue;
            }

            if (Math.abs(currPoint.y - aisleY) > 0.5) {
                pathPoints.push({ x: currPoint.x, y: aisleY });
            }
            if (Math.abs(nextPoint.x - currPoint.x) > 0.5) {
                pathPoints.push({ x: nextPoint.x, y: aisleY });
            }
            if (Math.abs(nextPoint.y - aisleY) > 0.5) {
                pathPoints.push(nextPoint);
            }
        }

        pathPoints.push(projected[projected.length - 1].point);

        return normalizePoints(pathPoints);
    };

    return (
        <div className={`bg-white rounded-xl p-5 shadow-sm border border-gray-100 flex flex-col ${fullHeight ? 'h-[calc(100vh-180px)]' : 'h-96'}`}>
            {!fullHeight && <h3 className="text-lg font-semibold text-gray-800 mb-4 flex-shrink-0">Customer Routes</h3>}
            {data.length === 0 ? (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                    No path data available
                </div>
            ) : fullHeight ? (
                <div className="flex-1 flex gap-4 min-h-0 overflow-hidden">
                    {/* Map on the left (70%) */}
                    <div className="relative flex-[7] bg-gray-50 rounded-lg overflow-hidden border border-gray-200">
                        <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                            <rect x="0" y="0" width="100" height="100" fill="#f9fafb" />

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

                            {STORE_LAYOUT.shelves.map((shelf) => {
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
                                        <text
                                            x={shelf.x + shelf.width / 2}
                                            y={100 - shelf.y - shelf.height / 2 - 3}
                                            textAnchor="middle"
                                            dominantBaseline="middle"
                                            fontSize="2"
                                            fill="#e5e7eb"
                                            fontWeight="600"
                                        >
                                            {shelf.label}
                                        </text>
                                        <text
                                            x={shelf.x + shelf.width / 2}
                                            y={100 - shelf.y - shelf.height / 2 + 2}
                                            textAnchor="middle"
                                            dominantBaseline="middle"
                                            fontSize="1.6"
                                            fill="#9ca3af"
                                        >
                                            {getShelfCategory(shelf.label, shelfCategories)}
                                        </text>
                                    </g>
                                );
                            })}

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

                            {data.map((pathItem, idx) => {
                                // Skip if a shopper is selected and this is not the selected one
                                if (selectedShopperId !== null && pathItem.shopper_id !== selectedShopperId) {
                                    return null;
                                }

                                const points = buildWalkablePath(pathItem.points, pathItem.shopper_id);
                                if (points.length < 2) return null;

                                const pathD = createSvgPath(points);
                                const color = colorFor(idx);
                                const isSelected = selectedShopperId === pathItem.shopper_id;

                                return (
                                    <g key={pathItem.shopper_id}>
                                        <path
                                            d={pathD}
                                            fill="none"
                                            stroke={color}
                                            strokeWidth={isSelected ? 1 : 0.5}
                                            strokeLinecap="round"
                                            strokeLinejoin="round"
                                            opacity={isSelected ? 0.8 : 0.35}
                                        />
                                        <circle
                                            cx={points[0].x}
                                            cy={100 - points[0].y}
                                            r={isSelected ? 1.8 : 1.2}
                                            fill={color}
                                            opacity={0.8}
                                        />
                                        <circle
                                            cx={points[points.length - 1].x}
                                            cy={100 - points[points.length - 1].y}
                                            r={isSelected ? 1.8 : 1.2}
                                            fill="white"
                                            stroke={color}
                                            strokeWidth="0.8"
                                            opacity={0.8}
                                        />
                                    </g>
                                );
                            })}
                        </svg>
                    </div>

                    {/* Routes list on the right (30%) - fixed height with internal scroll */}
                    <div className="flex-[3] bg-white rounded-lg border border-gray-200 flex flex-col min-h-0 overflow-hidden">
                        <h4 className="text-sm font-semibold text-gray-700 p-4 pb-2 flex-shrink-0">Shopper Routes</h4>
                        <div className="flex-1 overflow-y-auto px-4 pt-2 pb-4 space-y-2">
                            {data.map((pathItem, idx) => {
                                const isSelected = selectedShopperId === pathItem.shopper_id;
                                return (
                                    <div
                                        key={pathItem.shopper_id}
                                        className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-all ${isSelected
                                            ? 'bg-blue-100 ring-2 ring-blue-400'
                                            : 'bg-gray-50 hover:bg-gray-100'
                                            }`}
                                        onClick={() => handleShopperClick(pathItem.shopper_id)}
                                    >
                                        <div
                                            className="w-3 h-3 rounded-full flex-shrink-0 mt-0.5"
                                            style={{ backgroundColor: colorFor(idx) }}
                                        />
                                        <div className="flex-1 min-w-0">
                                            <div className="text-xs font-medium text-gray-700">Shopper {pathItem.shopper_id}</div>
                                            <div className="text-xs text-gray-500 mt-0.5">
                                                {pathItem.shelves.length > 0
                                                    ? pathItem.shelves.map(shelf => getShelfCategoryFormat(shelf.zone, shelfCategories)).join(' → ')
                                                    : 'No shelf visits'}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            ) : (
                <div className="relative flex-1 bg-gray-50 rounded-lg overflow-hidden border border-gray-200">
                    <svg viewBox="0 0 100 100" className="w-full h-full" preserveAspectRatio="xMidYMid meet">
                        <rect x="0" y="0" width="100" height="100" fill="#f9fafb" />

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

                        {STORE_LAYOUT.shelves.map((shelf) => {
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
                                    <text
                                        x={shelf.x + shelf.width / 2}
                                        y={100 - shelf.y - shelf.height / 2 - 3}
                                        textAnchor="middle"
                                        dominantBaseline="middle"
                                        fontSize="2"
                                        fill="#e5e7eb"
                                        fontWeight="600"
                                    >
                                        {shelf.label}
                                    </text>
                                    <text
                                        x={shelf.x + shelf.width / 2}
                                        y={100 - shelf.y - shelf.height / 2 + 2}
                                        textAnchor="middle"
                                        dominantBaseline="middle"
                                        fontSize="1.6"
                                        fill="#9ca3af"
                                    >
                                        {getShelfCategory(shelf.label, shelfCategories)}
                                    </text>
                                </g>
                            );
                        })}

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

                        {data.map((pathItem, idx) => {
                            const points = buildWalkablePath(pathItem.points, pathItem.shopper_id);
                            if (points.length < 2) return null;

                            const pathD = createSvgPath(points);
                            const color = colorFor(idx);

                            return (
                                <g key={pathItem.shopper_id}>
                                    <path
                                        d={pathD}
                                        fill="none"
                                        stroke={color}
                                        strokeWidth={0.5}
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        opacity={0.35}
                                    />
                                    <circle
                                        cx={points[0].x}
                                        cy={100 - points[0].y}
                                        r="1.2"
                                        fill={color}
                                        opacity={0.8}
                                    />
                                    <circle
                                        cx={points[points.length - 1].x}
                                        cy={100 - points[points.length - 1].y}
                                        r="1.2"
                                        fill="white"
                                        stroke={color}
                                        strokeWidth="0.8"
                                        opacity={0.8}
                                    />
                                </g>
                            );
                        })}
                    </svg>
                </div>
            )}
        </div>
    );
}
