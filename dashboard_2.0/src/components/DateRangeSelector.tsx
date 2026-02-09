'use client';

import { useState, useEffect } from 'react';
import { Calendar } from 'lucide-react';
import { format, parseISO, differenceInDays } from 'date-fns';

interface DateRangeSelectorProps {
    availableRange: {
        min: string;
        max: string;
    };
    currentRange: {
        start: string;
        end: string;
    };
    onRangeChange: (start: string, end: string) => void;
}

export default function DateRangeSelector({
    availableRange,
    currentRange,
    onRangeChange,
}: DateRangeSelectorProps) {
    const [startDate, setStartDate] = useState(currentRange.start);
    const [endDate, setEndDate] = useState(currentRange.end);
    const [isOpen, setIsOpen] = useState(false);

    useEffect(() => {
        setStartDate(currentRange.start);
        setEndDate(currentRange.end);
    }, [currentRange]);

    const handleApply = () => {
        onRangeChange(startDate, endDate);
        setIsOpen(false);
    };

    const formatDisplayDate = (dateStr: string) => {
        try {
            const date = parseISO(dateStr);
            // Use numeric format for cleaner display
            return new Intl.DateTimeFormat(undefined, {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
            }).format(date);
        } catch {
            return dateStr;
        }
    };

    // Check if single day and calculate day count
    const isSingleDay = currentRange.start === currentRange.end;
    const dayCount = (() => {
        try {
            return differenceInDays(parseISO(currentRange.end), parseISO(currentRange.start)) + 1;
        } catch {
            return 1;
        }
    })();

    // Quick select options
    const quickSelects = [
        { label: 'All Data', start: availableRange.min, end: availableRange.max },
    ];

    // Navigate to previous/next day
    const goToPreviousDay = () => {
        try {
            const currentStart = parseISO(currentRange.start);
            const currentEnd = parseISO(currentRange.end);
            const days = differenceInDays(currentEnd, currentStart);

            const newStart = new Date(currentStart);
            newStart.setDate(newStart.getDate() - 1);
            const newEnd = new Date(newStart);
            newEnd.setDate(newEnd.getDate() + days);

            const minDate = parseISO(availableRange.min);
            if (newStart >= minDate) {
                onRangeChange(
                    format(newStart, 'yyyy-MM-dd'),
                    format(newEnd, 'yyyy-MM-dd')
                );
            }
        } catch {
            // Ignore errors
        }
    };

    const goToNextDay = () => {
        try {
            const currentStart = parseISO(currentRange.start);
            const currentEnd = parseISO(currentRange.end);
            const days = differenceInDays(currentEnd, currentStart);

            const newEnd = new Date(currentEnd);
            newEnd.setDate(newEnd.getDate() + 1);
            const newStart = new Date(newEnd);
            newStart.setDate(newStart.getDate() - days);

            const maxDate = parseISO(availableRange.max);
            if (newEnd <= maxDate) {
                onRangeChange(
                    format(newStart, 'yyyy-MM-dd'),
                    format(newEnd, 'yyyy-MM-dd')
                );
            }
        } catch {
            // Ignore errors
        }
    };

    // Check if can navigate
    const canGoPrevious = (() => {
        try {
            const currentStart = parseISO(currentRange.start);
            const minDate = parseISO(availableRange.min);
            return currentStart > minDate;
        } catch {
            return false;
        }
    })();

    const canGoNext = (() => {
        try {
            const currentEnd = parseISO(currentRange.end);
            const maxDate = parseISO(availableRange.max);
            return currentEnd < maxDate;
        } catch {
            return false;
        }
    })();

    return (
        <div className="relative flex items-center gap-1">
            {/* Previous day button */}
            <button
                onClick={goToPreviousDay}
                disabled={!canGoPrevious}
                className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                title="Previous day"
            >
                <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
            </button>

            {/* Date selector button */}
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors h-[38px]"
            >
                <Calendar className="h-5 w-5 text-gray-500" />
                <span className="text-sm text-gray-700">
                    {isSingleDay ? (
                        formatDisplayDate(currentRange.start)
                    ) : (
                        <>
                            {formatDisplayDate(currentRange.start)} - {formatDisplayDate(currentRange.end)}
                            <span className="text-gray-400 ml-1">({dayCount} days)</span>
                        </>
                    )}
                </span>
            </button>

            {/* Next day button */}
            <button
                onClick={goToNextDay}
                disabled={!canGoNext}
                className="p-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                title="Next day"
            >
                <svg className="h-5 w-5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute right-0 top-12 z-50 bg-white border border-gray-200 rounded-lg shadow-lg p-4 min-w-[300px]">
                    <div className="space-y-4">
                        {/* Quick selects */}
                        <div className="flex flex-wrap gap-2">
                            {quickSelects.map((option) => (
                                <button
                                    key={option.label}
                                    onClick={() => {
                                        setStartDate(option.start);
                                        setEndDate(option.end);
                                    }}
                                    className="px-3 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded-full text-gray-700"
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>

                        {/* Date inputs */}
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs text-gray-500 mb-1">Start Date</label>
                                <input
                                    type="date"
                                    value={startDate}
                                    min={availableRange.min}
                                    max={endDate}
                                    onChange={(e) => setStartDate(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-500 mb-1">End Date</label>
                                <input
                                    type="date"
                                    value={endDate}
                                    min={startDate}
                                    max={availableRange.max}
                                    onChange={(e) => setEndDate(e.target.value)}
                                    className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm text-gray-800 focus:ring-2 focus:ring-teal-500 focus:border-transparent"
                                />
                            </div>
                        </div>

                        {/* Available range info */}
                        <p className="text-xs text-gray-400">
                            Available: {formatDisplayDate(availableRange.min)} - {formatDisplayDate(availableRange.max)}
                        </p>

                        {/* Action buttons */}
                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => setIsOpen(false)}
                                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleApply}
                                className="px-4 py-2 text-sm bg-teal-500 text-white rounded-lg hover:bg-teal-600"
                            >
                                Apply
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

