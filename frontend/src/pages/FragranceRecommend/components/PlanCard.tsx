import React, { useEffect, useState } from 'react';
import { Typography, Collapse, Space } from 'antd';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { FragrancePlan, FragranceNote } from '../../../types/fragrance';
import { useFragranceStore } from '../../../stores/useFragranceStore';
import '../index.css';

const { Text, Paragraph, Title } = Typography;
const { Panel } = Collapse;

interface PlanCardProps {
  plan: FragrancePlan;
  index: number;
}

export const PlanCard: React.FC<PlanCardProps> = ({ plan, index }) => {
  const { changeAnimation } = useFragranceStore();
  const [activeKeys, setActiveKeys] = useState<string[]>([]);

  // 检查当前卡片是否正在高亮动画中
  const isHighlighted = changeAnimation?.planId === plan.planId;

  // 如果被修改，自动展开所有折叠面板
  useEffect(() => {
    if (isHighlighted) {
      setActiveKeys(['reason', 'story']);
    }
  }, [isHighlighted]);

  const renderNotes = (title: string, notes: FragranceNote[]) => {
    if (!notes || notes.length === 0) return null;
    return (
      <div style={{ marginBottom: 20 }}>
        <div style={{ borderBottom: '1px solid rgba(47, 54, 48, 0.1)', marginBottom: 12, paddingBottom: 4 }}>
          <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 13, letterSpacing: 1 }}>{title}</Text>
        </div>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          {notes.map((note, i) => (
            <div key={`${note.name}-${i}`} className={`note-item ${note.changed && isHighlighted ? 'changed' : ''}`}>
              <div>
                <Text strong style={{ fontSize: 14, color: 'var(--text-primary)' }}>{note.name}</Text>
                <Text style={{ fontSize: 13, color: 'var(--text-secondary)', marginLeft: 8 }}>{note.description}</Text>
                {note.changed && isHighlighted && <span className="changed-badge">[NEW]</span>}
              </div>
              <div style={{ display: 'flex', marginTop: 4 }}>
                <span style={{ color: 'var(--accent-amber)', marginRight: 6 }}>↳</span>
                <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>推荐理由: {note.reason}</Text>
              </div>
            </div>
          ))}
        </Space>
      </div>
    );
  };

  return (
    <div 
      id={`plan-${plan.planId}`} 
      className={`plan-card ${isHighlighted ? 'highlighted' : ''}`} 
      style={{ marginBottom: 24, animationDelay: `${index * 0.15}s` }}
    >
      {/* 标题区 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 24 }}>
        <div>
          <Title level={3} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', margin: 0, fontWeight: 500 }}>
            {plan.name}
          </Title>
          <Text style={{ fontSize: 14, color: 'var(--text-secondary)', marginTop: 4, display: 'block' }}>
            {plan.category}
          </Text>
        </div>
        <Text style={{ color: 'var(--accent-amber)', fontFamily: 'var(--font-serif)', fontSize: 16 }}>
          Plan {index + 1}
        </Text>
      </div>

      {/* 香材区 */}
      {renderNotes('前调', plan.topNotes)}
      {renderNotes('中调', plan.middleNotes)}
      {renderNotes('后调', plan.baseNotes)}

      {/* 展开区：推荐原因和故事 */}
      <Collapse
        ghost
        activeKey={activeKeys}
        onChange={(keys) => setActiveKeys(keys as string[])}
        expandIcon={({ isActive }) => isActive ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        style={{ marginTop: 12, marginLeft: -16, marginRight: -16 }} // 抵消卡片的 padding，使 Collapse 分割线到边缘
      >
        <Panel 
          header={<Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontWeight: 500 }}>推荐原因</Text>} 
          key="reason"
        >
          <Paragraph style={{ color: 'var(--text-secondary)', lineHeight: 1.8, marginBottom: 0 }}>
            {plan.recommendationReason}
          </Paragraph>
        </Panel>
        
        <Panel 
          header={<Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontWeight: 500 }}>创作灵感</Text>} 
          key="story"
        >
          <div className="story-content">
            {plan.fragranceStory}
          </div>
        </Panel>
      </Collapse>
    </div>
  );
};
