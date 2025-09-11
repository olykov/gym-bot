import React, { useState } from 'react';

interface DailyActivity {
  date: string;
  sets_count: number;
}

interface ActivityGridProps {
  activityData: DailyActivity[];
}

const ActivityGrid: React.FC<ActivityGridProps> = ({ activityData }) => {
  const [hoveredDay, setHoveredDay] = useState<DailyActivity | null>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Get intensity level based on sets count
  const getIntensityLevel = (setsCount: number): number => {
    if (setsCount === 0) return 0;
    if (setsCount <= 5) return 1;
    if (setsCount <= 10) return 2;
    if (setsCount <= 15) return 3;
    return 4;
  };

  // Get CSS class for intensity level  
  const getIntensityClass = (level: number): string => {
    const baseClasses = "rounded-sm border border-gray-200 transition-all duration-200 hover:border-gray-400";
    
    switch (level) {
      case 0: return `${baseClasses} bg-gray-100`;
      case 1: return `${baseClasses} bg-green-200`;
      case 2: return `${baseClasses} bg-green-300`;
      case 3: return `${baseClasses} bg-green-500`;
      case 4: return `${baseClasses} bg-green-700`;
      default: return `${baseClasses} bg-gray-100`;
    }
  };

  // Format date for tooltip
  const formatDate = (dateStr: string): string => {
    const date = new Date(dateStr);
    const options: Intl.DateTimeFormatOptions = { 
      month: 'short', 
      day: 'numeric', 
      year: 'numeric' 
    };
    return date.toLocaleDateString('en-US', options);
  };

  // Get sets text for tooltip
  const getSetsText = (count: number): string => {
    if (count === 0) return 'No sets';
    if (count === 1) return '1 set';
    return `${count} sets`;
  };

  // Handle mouse events for tooltip
  const handleMouseEnter = (day: DailyActivity, event: React.MouseEvent) => {
    setHoveredDay(day);
    setMousePosition({ x: event.clientX, y: event.clientY });
  };

  const handleMouseMove = (event: React.MouseEvent) => {
    setMousePosition({ x: event.clientX, y: event.clientY });
  };

  const handleMouseLeave = () => {
    setHoveredDay(null);
  };

  // Generate month labels for the top
  const generateMonthLabels = (): string[] => {
    const months: string[] = [];
    const startDate = new Date(activityData[0]?.date || new Date());
    
    for (let i = 0; i < 12; i++) {
      const date = new Date(startDate);
      date.setMonth(date.getMonth() + i);
      months.push(date.toLocaleDateString('en-US', { month: 'short' }));
    }
    
    return months;
  };

  const monthLabels = generateMonthLabels();
  const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']; // Monday first (European format)

  // Render proper GitHub-style grid (CSS Grid with auto-flow column)
  const renderProperGitHubGrid = () => {
    if (!activityData || activityData.length === 0) {
      return null;
    }
    
    // Find the first date and determine padding needed
    const firstDate = new Date(activityData[0].date);
    let firstDayOfWeek = firstDate.getDay(); // 0 = Sunday, 1 = Monday, etc.
    
    // Convert to Monday-first format: Monday=0, Tuesday=1, ... Sunday=6
    firstDayOfWeek = firstDayOfWeek === 0 ? 6 : firstDayOfWeek - 1;
    
    const gridElements = [];
    
    // Add empty cells for padding to start on correct day of week  
    for (let i = 0; i < firstDayOfWeek; i++) {
      gridElements.push(
        <div
          key={`padding-${i}`}
          className="activity-square opacity-0"
        />
      );
    }
    
    // Add actual data cells - CSS Grid will arrange them properly
    activityData.forEach((day) => {
      const intensityLevel = getIntensityLevel(day.sets_count);
      gridElements.push(
        <div
          key={day.date}
          className={`activity-square ${getIntensityClass(intensityLevel)}`}
          onMouseEnter={(e) => handleMouseEnter(day, e)}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          title={`${getSetsText(day.sets_count)} on ${formatDate(day.date)}`}
        />
      );
    });
    
    return gridElements;
  };

  return (
    <div className="relative">
      {/* Activity Grid Container */}
      <div className="inline-block">
        {/* Month Labels */}
        <div className="flex mb-2 ml-8">
          {monthLabels.map((month, index) => (
            <div 
              key={index} 
              className="text-xs text-gray-600 flex-1 text-left"
              style={{ minWidth: '40px' }}
            >
              {index === 0 || index % 2 === 0 ? month : ''}
            </div>
          ))}
        </div>

        {/* Main Grid Layout */}
        <div className="flex">
          {/* Day Labels */}
          <div className="flex flex-col mr-2 text-xs text-gray-600 day-labels">
            {dayLabels.map((day, index) => (
              <div key={day} className="day-label flex items-center justify-end">
                {day} {/* Show all day names */}
              </div>
            ))}
          </div>

          {/* Activity Grid */}
          <div className="activity-grid">
            {renderProperGitHubGrid()}
          </div>
        </div>

        {/* Intensity Legend */}
        <div className="flex items-center justify-between mt-4 text-xs text-gray-600">
          <span>Less</span>
          <div className="flex gap-1 mx-3">
            {[0, 1, 2, 3, 4].map(level => (
              <div
                key={level}
                className={getIntensityClass(level)}
              />
            ))}
          </div>
          <span>More</span>
        </div>
      </div>

      {/* Tooltip */}
      {hoveredDay && (
        <div
          className="fixed z-50 bg-gray-900 text-white text-sm rounded-md py-2 px-3 pointer-events-none shadow-lg"
          style={{
            left: `${mousePosition.x + 10}px`,
            top: `${mousePosition.y - 10}px`,
            transform: 'translateY(-100%)'
          }}
        >
          <div className="font-medium">
            {getSetsText(hoveredDay.sets_count)}
          </div>
          <div className="text-gray-300">
            {formatDate(hoveredDay.date)}
          </div>
        </div>
      )}

      <style jsx>{`        
        .activity-grid {
          display: grid;
          grid-template-rows: repeat(7, 12px);
          grid-auto-flow: column;
          grid-auto-columns: 12px;
          gap: 3px;
          overflow-x: auto;
        }
        
        .activity-square {
          height: 12px;
          width: 12px;
        }
        
        .day-labels {
          display: flex;
          flex-direction: column;
          gap: 3px;
        }
        
        .day-label {
          height: 12px;
          line-height: 12px;
        }
        
        @media (max-width: 640px) {
          .activity-grid {
            grid-template-rows: repeat(7, 10px);
            grid-auto-columns: 10px;
            gap: 2px;
          }
          
          .activity-square {
            height: 10px;
            width: 10px;
          }
          
          .day-labels {
            gap: 2px;
          }
          
          .day-label {
            height: 10px;
            line-height: 10px;
          }
        }
      `}</style>
    </div>
  );
};

export default ActivityGrid;