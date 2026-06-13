import React from 'react';
import { Typography } from 'antd';
import type { ChatMessage } from '../../../types/fragrance';
import '../index.css';

const { Text } = Typography;

interface MessageBubbleProps {
  message: ChatMessage;
}

export const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.role === 'user';

  const scrollToPlan = (planId: string) => {
    const el = document.getElementById(`plan-${planId}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: isUser ? 'flex-end' : 'flex-start', marginBottom: 8 }}>
      <div className={`message-bubble ${isUser ? 'user' : 'assistant'}`}>
        <Text style={{ color: 'inherit', whiteSpace: 'pre-wrap', lineHeight: 1.6, fontSize: 14 }}>{message.content}</Text>
        
        {/* 如果有方案更新，显示更新标签锚点 */}
        {!isUser && message.updatedPlans && message.updatedPlans.length > 0 && (
          <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.06)' }}>
            {message.updatedPlans.map(plan => (
              <div 
                key={plan.planId}
                onClick={() => scrollToPlan(plan.planId)}
                style={{ 
                  display: 'inline-block',
                  cursor: 'pointer',
                  padding: '4px 12px',
                  background: 'rgba(193, 136, 65, 0.1)',
                  color: 'var(--accent-amber)',
                  borderRadius: 12,
                  fontSize: 12,
                  marginTop: 4,
                  fontFamily: 'var(--font-sans)'
                }}
              >
                [NEW] {plan.name} 已更新，点击查看
              </div>
            ))}
          </div>
        )}
      </div>
      <Text style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: -12, marginBottom: 16, padding: '0 4px' }}>
        {new Date(message.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </Text>
    </div>
  );
};
