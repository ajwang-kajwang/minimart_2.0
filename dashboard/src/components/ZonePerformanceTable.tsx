interface ShelfPerformanceTableProps {
    data: Array<{
        zone: string;
        visitors: number;
        events: number;
    }>;
    shelfCategories?: Record<string, string>;
}

// Get display name: "Fruits (1A)" format
const getShelfDisplayName = (shelfName: string, categories: Record<string, string>): string => {
    const category = categories[shelfName];
    const label = shelfName.replace('Shelf ', '');
    return category ? `${category} (${label})` : shelfName;
};

export default function ShelfPerformanceTable({ data, shelfCategories = {} }: ShelfPerformanceTableProps) {
    // Filter to only show shelf data (zones starting with "Shelf")
    const shelfData = data.filter(z => z.zone.startsWith('Shelf'));
    const maxVisitors = Math.max(...shelfData.map(z => z.visitors), 1);

    return (
        <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-100 h-80">
            <h3 className="text-lg font-semibold text-gray-800 mb-4">Shelf Performance</h3>
            {shelfData.length === 0 ? (
                <div className="h-56 flex items-center justify-center text-gray-500">
                    No shelf data available
                </div>
            ) : (
                <div className="overflow-y-auto h-56">
                    <table className="w-full">
                        <thead className="sticky top-0 bg-white">
                            <tr className="text-left text-sm text-gray-500 border-b">
                                <th className="pb-2">Category</th>
                                <th className="pb-2 text-right">Visitors</th>
                                <th className="pb-2 text-right">Events</th>
                            </tr>
                        </thead>
                        <tbody>
                            {shelfData.map((shelf) => (
                                <tr key={shelf.zone} className="border-b border-gray-50">
                                    <td className="py-3">
                                        <div className="flex items-center gap-2">
                                            <div
                                                className="w-16 h-2 rounded-full bg-gray-100 overflow-hidden"
                                            >
                                                <div
                                                    className="h-full bg-teal-500 rounded-full"
                                                    style={{ width: `${(shelf.visitors / maxVisitors) * 100}%` }}
                                                />
                                            </div>
                                            <span className="text-sm font-medium text-gray-700">{getShelfDisplayName(shelf.zone, shelfCategories)}</span>
                                        </div>
                                    </td>
                                    <td className="py-3 text-right text-sm text-gray-600">
                                        {shelf.visitors.toLocaleString()}
                                    </td>
                                    <td className="py-3 text-right text-sm text-gray-500">
                                        {shelf.events.toLocaleString()}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
