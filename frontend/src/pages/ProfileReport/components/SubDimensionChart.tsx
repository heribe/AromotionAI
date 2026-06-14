import React from 'react';
import { Card, Typography } from 'antd';
import type { SubDimension } from '../../../types/analysis';
import { CHART_COLORS } from '../../../utils/chartColors';

const { Text, Paragraph } = Typography;

interface SubDimensionChartProps {
  sub: SubDimension;
}

/**
 * 子维度图表组件 — 根据 chartType 自动渲染不同图表
 * 当前使用纯 CSS 实现（避免 @ant-design/charts 的体积和兼容问题）
 * 后续可轻松替换为 @ant-design/charts 的 Pie/Bar/Radar 组件
 */
export const SubDimensionChart: React.FC<SubDimensionChartProps> = ({ sub }) => {
  const maxValue = Math.max(...sub.data.map(d => d.value), 1);

  return (
    <Card
      bodyStyle={{ padding: '24px 28px' }}
      style={{ height: '100%', width: '100%', display: 'flex', flexDirection: 'column' }}
    >
      <Text style={{ fontFamily: 'var(--font-serif)', fontSize: 15, color: 'var(--accent-moss)', display: 'block', marginBottom: 20 }}>
        {sub.subName}
      </Text>

      {/* 饼图 → 水平条形可视化（更紧凑、信息密度更高） */}
      {(sub.chartType === 'pie') && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sub.data.map((item, i) => (
            <div key={item.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Text style={{ fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</Text>
                <Text style={{ fontSize: 13, color: 'var(--accent-amber)', fontFamily: 'var(--font-serif)' }}>{item.value}%</Text>
              </div>
              <div style={{ height: 10, background: 'var(--border-line)', borderRadius: 1, overflow: 'hidden' }}>
                <div style={{
                  width: `${item.value}%`,
                  height: '100%',
                  background: item.color || CHART_COLORS[i % CHART_COLORS.length],
                  borderRadius: 1,
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 柱状图 → 水平柱状条（上下布局，与 pie/radar 统一） */}
      {sub.chartType === 'bar' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sub.data.map((item, i) => (
            <div key={item.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Text style={{ fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</Text>
                <Text style={{ fontSize: 13, color: 'var(--accent-amber)', fontFamily: 'var(--font-serif)' }}>{item.value}%</Text>
              </div>
              <div style={{ height: 10, background: 'var(--border-line)', borderRadius: 1, overflow: 'hidden', position: 'relative' }}>
                <div style={{
                  width: `${(item.value / maxValue) * 100}%`,
                  height: '100%',
                  background: item.color || CHART_COLORS[i % CHART_COLORS.length],
                  borderRadius: 1,
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 雷达图 → 多维度条形对比 */}
      {sub.chartType === 'radar' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {sub.data.map((item, i) => (
            <div key={item.name}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <Text style={{ fontSize: 13, color: 'var(--text-primary)' }}>{item.name}</Text>
                <Text style={{ fontSize: 13, color: 'var(--accent-amber)', fontFamily: 'var(--font-serif)' }}>{item.value}</Text>
              </div>
              <div style={{ height: 10, background: 'var(--border-line)', borderRadius: 1, overflow: 'hidden' }}>
                <div style={{
                  width: `${item.value}%`,
                  height: '100%',
                  background: CHART_COLORS[i % CHART_COLORS.length],
                  borderRadius: 1,
                  transition: 'width 0.6s ease',
                }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 纯文字类型 */}
      {sub.chartType === 'text' && (
        <div>
          <div style={{ display: 'inline-block', padding: '6px 16px', border: '1px solid var(--accent-amber)', borderRadius: 2, marginBottom: 12 }}>
            <Text style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-serif)', fontSize: 14 }}>{sub.data[0]?.name}</Text>
          </div>
          {sub.summary && (
            <Paragraph style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 0, lineHeight: 1.7, marginTop: 8 }}>
              {sub.summary}
            </Paragraph>
          )}
        </div>
      )}
    </Card>
  );
};
