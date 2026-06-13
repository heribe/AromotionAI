import React, { useState } from 'react';
import { Input, Button } from 'antd';
import { Send } from 'lucide-react';
import { useFragranceStore } from '../../../stores/useFragranceStore';
import '../index.css';

const { TextArea } = Input;

const QUICK_ACTIONS = [
  { label: '换一种风格', message: '能给我换一种完全不同风格的方案吗？' },
  { label: '更浓郁', message: '我觉得整体偏淡，能不能做得更浓郁一些？' },
  { label: '适合约会', message: '如果主要用于约会场景，你会怎么调整？' },
  { label: '木质调后调', message: '能不能把方案一的后调换成沉香和木质调？' }, // 用于触发 Mock 剧本
];

export const ChatInput: React.FC = () => {
  const [value, setValue] = useState('');
  const { sendMessage, isSending } = useFragranceStore();

  const handleSend = () => {
    if (!value.trim() || isSending) return;
    sendMessage(value);
    setValue('');
  };

  const handleQuickAction = (message: string) => {
    if (isSending) return;
    sendMessage(message);
  };

  return (
    <div className="chat-input-area" style={{ 
      background: 'var(--bg-paper)', 
      padding: '16px 20px 20px',
      borderTop: '1px solid var(--border-line)',
      flexShrink: 0
    }}>
      {/* 快捷操作 */}
      <div style={{ 
        marginBottom: 14, 
        display: 'flex', 
        gap: 8, 
        flexWrap: 'wrap'
      }}>
        {QUICK_ACTIONS.map(action => (
          <button 
            key={action.label} 
            onClick={() => handleQuickAction(action.message)}
            disabled={isSending}
            style={{ 
              border: '1px solid var(--border-line)',
              borderRadius: 20,
              background: 'transparent',
              color: 'var(--text-secondary)', 
              fontSize: 12,
              padding: '5px 14px',
              cursor: isSending ? 'not-allowed' : 'pointer',
              opacity: isSending ? 0.5 : 1,
              fontFamily: 'var(--font-sans)',
              transition: 'all 0.2s ease',
              lineHeight: 1.4
            }}
            onMouseEnter={(e) => {
              if (!isSending) {
                e.currentTarget.style.borderColor = 'var(--accent-amber)';
                e.currentTarget.style.color = 'var(--accent-amber)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--border-line)';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* 输入区 */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        <TextArea
          value={value}
          onChange={e => setValue(e.target.value)}
          placeholder="对当前方案有什么想法，或者想如何调整？"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={isSending}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          style={{ 
            borderRadius: 20,
            fontFamily: 'var(--font-sans)',
            boxShadow: 'none',
            borderColor: 'var(--border-line)',
            padding: '8px 16px',
            fontSize: 13,
            resize: 'none'
          }}
        />
        <Button
          type="primary"
          icon={<Send size={14} />}
          onClick={handleSend}
          loading={isSending}
          className="chat-send-btn"
          style={{
            borderRadius: '50%',
            background: 'var(--accent-amber)',
            width: 36,
            height: 36,
            minWidth: 36,
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            border: 'none'
          }}
        />
      </div>
    </div>
  );
};
