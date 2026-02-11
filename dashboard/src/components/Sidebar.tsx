'use client';

import { LayoutDashboard, Video, Map, Route, BarChart3, MessageSquare } from 'lucide-react';

export type ViewType = 'overview' | 'live' | 'heatmap' | 'paths' | 'traffic' | 'ai';

interface SidebarProps {
    currentView: ViewType;
    onViewChange: (view: ViewType) => void;
}

const menuItems = [
    { id: 'overview' as ViewType, label: 'Overview', icon: LayoutDashboard },
    { id: 'live' as ViewType, label: 'Live Feed', icon: Video },
    { id: 'heatmap' as ViewType, label: 'Heatmap', icon: Map },
    { id: 'paths' as ViewType, label: 'Customer Routes', icon: Route },
    { id: 'traffic' as ViewType, label: 'Traffic Analysis', icon: BarChart3 },
    { id: 'ai' as ViewType, label: 'AI Assistant', icon: MessageSquare },
];

export default function Sidebar({ currentView, onViewChange }: SidebarProps) {
    return (
        <aside className="fixed left-0 top-0 h-full w-16 lg:w-56 bg-gray-900 text-white flex flex-col z-50 transition-all duration-300">
            {/* Logo */}
            <div className="p-4 border-b border-gray-700">
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-teal-500 rounded-lg flex items-center justify-center">
                        <span className="text-lg font-bold">M</span>
                    </div>
                    <span className="hidden lg:block font-semibold text-sm">Minimart Analytics</span>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4">
                <ul className="space-y-1 px-2">
                    {menuItems.map((item) => {
                        const Icon = item.icon;
                        const isActive = currentView === item.id;

                        return (
                            <li key={item.id}>
                                <button
                                    onClick={() => onViewChange(item.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors ${isActive
                                        ? 'bg-teal-500 text-white'
                                        : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                                        }`}
                                    title={item.label}
                                >
                                    <Icon className="w-5 h-5 flex-shrink-0" />
                                    <span className="hidden lg:block text-sm">{item.label}</span>
                                </button>
                            </li>
                        );
                    })}
                </ul>
            </nav>

            {/* Footer */}
            <div className="p-4 border-t border-gray-700">
                <p className="hidden lg:block text-xs text-gray-500 text-center">
                    v0.1.0
                </p>
            </div>
        </aside>
    );
}
