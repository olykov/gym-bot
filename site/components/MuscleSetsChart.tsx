import React, { useEffect, useState } from 'react';
import ReactECharts from 'echarts-for-react';

interface MuscleSetsSeries {
  name: string;
  data: number[];
}

interface MuscleSetsChartProps {
  weeks: string[];
  series: MuscleSetsSeries[];
  title?: string;
  height?: number;
  showToolbox?: boolean;
}

/**
 * Reusable ECharts component for displaying muscle sets data over time
 * Shows stacked area chart with gradients for each muscle group
 */
const MuscleSetsChart: React.FC<MuscleSetsChartProps> = ({
  weeks,
  series,
  title = 'Weekly Muscle Sets Distribution',
  height = 400,
  showToolbox = true
}) => {
  const [chartReady, setChartReady] = useState(false);

  useEffect(() => {
    setChartReady(true);
  }, []);

  // Predefined colors and gradients for different muscle groups
  const muscleColors = [
    '#80FFA5', // Green
    '#00DDFF', // Cyan  
    '#37A2FF', // Blue
    '#FF0087', // Pink
    '#FFBF00', // Orange
    '#FF6B6B', // Red
    '#4ECDC4', // Teal
    '#45B7D1', // Light Blue
    '#96CEB4', // Mint
    '#FECA57'  // Yellow
  ];

  const muscleGradients = [
    // Green gradient
    [[0, 'rgb(128, 255, 165)'], [1, 'rgb(1, 191, 236)']],
    // Cyan gradient  
    [[0, 'rgb(0, 221, 255)'], [1, 'rgb(77, 119, 255)']],
    // Blue gradient
    [[0, 'rgb(55, 162, 255)'], [1, 'rgb(116, 21, 219)']],
    // Pink gradient
    [[0, 'rgb(255, 0, 135)'], [1, 'rgb(135, 0, 157)']],
    // Orange gradient
    [[0, 'rgb(255, 191, 0)'], [1, 'rgb(224, 62, 76)']],
    // Red gradient
    [[0, 'rgb(255, 107, 107)'], [1, 'rgb(255, 59, 59)']],
    // Teal gradient
    [[0, 'rgb(78, 205, 196)'], [1, 'rgb(85, 98, 112)']],
    // Light Blue gradient
    [[0, 'rgb(69, 183, 209)'], [1, 'rgb(144, 224, 239)']],
    // Mint gradient
    [[0, 'rgb(150, 206, 180)'], [1, 'rgb(74, 144, 226)']],
    // Yellow gradient
    [[0, 'rgb(254, 202, 87)'], [1, 'rgb(255, 107, 107)']]
  ];

  if (!chartReady || !series || series.length === 0) {
    return (
      <div className="flex items-center justify-center" style={{ height }}>
        <div className="text-gray-500">Loading muscle sets data...</div>
      </div>
    );
  }

  // Build ECharts option with real data
  const option = {
    color: muscleColors.slice(0, series.length),
    title: {
      text: title,
      left: 'center',
      textStyle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#374151'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
        label: {
          backgroundColor: '#6a7985'
        }
      },
      formatter: function(params: any) {
        let tooltip = `<strong>${params[0].axisValue}</strong><br/>`;
        let total = 0;
        params.forEach((param: any) => {
          const value = Number(param.value) || 0; // Ensure it's a number
          total += value;
          tooltip += `${param.marker} ${param.seriesName}: ${value} sets<br/>`;
        });
        tooltip += `<strong>Total: ${total} sets</strong>`;
        return tooltip;
      }
    },
    legend: {
      data: series.map(s => s.name),
      top: 50,
      textStyle: {
        fontSize: 11
      },
      itemGap: 10,
      itemWidth: 14,
      itemHeight: 10,
      orient: 'horizontal',
      // Force single row by calculating if too many items
      ...(series.length > 6 ? {
        type: 'scroll',
        pageIconSize: 12,
        pageTextStyle: { fontSize: 10 }
      } : {})
    },
    toolbox: showToolbox ? {
      feature: {
        saveAsImage: {
          title: 'Save as Image',
          name: 'muscle_sets_weekly'
        }
      }
    } : undefined,
    grid: {
      left: '3%',
      right: '4%',
      bottom: '8%',
      top: '30%',
      containLabel: true
    },
    xAxis: [
      {
        type: 'category',
        boundaryGap: false,
        data: weeks,
        axisLabel: {
          fontSize: 10,
          rotate: 45
        }
      }
    ],
    yAxis: [
      {
        type: 'value',
        name: 'Sets Count',
        nameTextStyle: {
          fontSize: 12
        },
        axisLabel: {
          fontSize: 10
        }
      }
    ],
    series: series.map((muscleData, index) => ({
      name: muscleData.name,
      type: 'line',
      stack: 'Total',
      smooth: true,
      lineStyle: {
        width: 0
      },
      showSymbol: false,
      areaStyle: {
        opacity: 0.8,
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: muscleGradients[index % muscleGradients.length].map(([offset, color]) => ({
            offset,
            color
          }))
        }
      },
      emphasis: {
        focus: 'series'
      },
      data: muscleData.data
    }))
  };

  return (
    <div className="w-full">
      <ReactECharts
        option={option}
        style={{ height: `${height}px`, width: '100%' }}
        opts={{ renderer: 'canvas' }}
      />
    </div>
  );
};

export default MuscleSetsChart;