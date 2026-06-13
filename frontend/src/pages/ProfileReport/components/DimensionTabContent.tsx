import React from 'react';
import { Typography, Row, Col } from 'antd';
import type { Dimension } from '../../../types/analysis';
import { SubDimensionChart } from './SubDimensionChart';

const { Paragraph } = Typography;

interface DimensionTabContentProps {
  dimension: Dimension;
}

/**
 * 维度 Tab 内容 — 展示一个维度下所有子维度的图表 + 维度总结
 */
export const DimensionTabContent: React.FC<DimensionTabContentProps> = ({ dimension }) => {
  return (
    <div>
      {/* 子维度图表网格：统一每行 2 列，等高对齐 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 32 }}>
        {dimension.subDimensions.map(sub => (
          <Col span={12} key={sub.subId} style={{ display: 'flex' }}>
            <SubDimensionChart sub={sub} />
          </Col>
        ))}
      </Row>

      {/* 维度总结 */}
      <div style={{
        padding: '24px 32px',
        background: 'var(--bg-ceramic)',
        border: '1px solid var(--border-line)',
        borderRadius: 2,
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute',
          top: -12,
          left: 24,
          background: 'var(--bg-ceramic)',
          padding: '0 8px',
          color: 'var(--accent-moss)',
          fontFamily: 'var(--font-serif)',
          fontStyle: 'italic',
          fontSize: 13,
        }}>
          总体判断
        </div>
        <Paragraph style={{
          color: 'var(--text-primary)',
          marginBottom: 0,
          lineHeight: 1.8,
          fontSize: 14,
        }}>
          {dimension.overallSummary}
        </Paragraph>
      </div>
    </div>
  );
};
