import React, { useEffect, useState } from 'react';
import { Typography, Collapse } from 'antd';
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
      <div style={{ marginBottom: 32 }}>
        <div style={{ 
          marginBottom: 16, 
          paddingBottom: 6,
          borderBottom: '1px solid rgba(47, 54, 48, 0.08)'
        }}>
          <Text style={{
            fontFamily: 'var(--font-serif)',
            color: 'var(--text-secondary)',
            fontSize: 12,
            letterSpacing: 3
          }}>{title}</Text>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {notes.map((note, i) => (
            <div key={`${note.name}-${i}`} className={`note-item ${note.changed && isHighlighted ? 'changed' : ''}`}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                <Text strong style={{ fontSize: 15, color: 'var(--text-primary)', fontFamily: 'var(--font-serif)' }}>{note.name}</Text>
                <Text style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{note.description}</Text>
                {note.changed && isHighlighted && <span className="changed-badge">[NEW]</span>}
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', marginTop: 6, paddingLeft: 2 }}>
                <span style={{ color: 'var(--accent-amber)', marginRight: 8, fontSize: 12 }}>↳</span>
                <Text style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>推荐理由: {note.reason}</Text>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div 
      id={`plan-${plan.planId}`} 
      className={`plan-card ${isHighlighted ? 'highlighted' : ''}`} 
      style={{ 
        marginBottom: 40, 
        animationDelay: `${index * 0.15}s`,
        padding: '36px 40px 28px'
      }}
    >
      {/* 标题区 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start', 
        marginBottom: 36,
        paddingBottom: 20,
        borderBottom: '1px solid rgba(47, 54, 48, 0.08)'
      }}>
        <div>
          <Title level={3} style={{ 
            fontFamily: 'var(--font-serif)', 
            color: 'var(--accent-moss)', 
            margin: 0, 
            fontWeight: 500,
            fontSize: 26,
            letterSpacing: 1
          }}>
            {plan.name}
          </Title>
          <Text style={{ 
            fontSize: 13, 
            color: 'var(--text-secondary)', 
            marginTop: 6, 
            display: 'block',
            fontFamily: 'var(--font-serif)',
            fontStyle: 'italic'
          }}>
            {plan.category}
          </Text>
        </div>
        <Text style={{ 
          color: 'var(--accent-amber)', 
          fontFamily: 'var(--font-serif)', 
          fontSize: 13, 
          letterSpacing: 2,
          fontStyle: 'italic',
          opacity: 0.7
        }}>
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
        expandIcon={({ isActive }) => isActive ? <ChevronUp size={14} color="var(--text-secondary)" /> : <ChevronDown size={14} color="var(--text-secondary)" />}
        style={{ marginTop: 8, marginLeft: -16, marginRight: -16 }}
      >
        <Panel 
          header={<Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontWeight: 500, fontSize: 14 }}>推荐原因</Text>} 
          key="reason"
        >
          <Paragraph style={{ color: 'var(--text-secondary)', lineHeight: 1.9, marginBottom: 0, fontSize: 13 }}>
            {plan.recommendationReason}
          </Paragraph>
        </Panel>
        
        <Panel 
          header={<Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontWeight: 500, fontSize: 14 }}>创作灵感</Text>} 
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
