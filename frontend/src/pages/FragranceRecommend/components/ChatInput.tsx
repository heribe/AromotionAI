import React, { useState } from 'react';
import { Input, Button, Space } from 'antd';
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
    <div className="chat-input-area" style={{ background: 'var(--bg-paper)' }}>
      <div style={{ marginBottom: 12, display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 4 }}>
        {QUICK_ACTIONS.map(action => (
          <Button 
            key={action.label} 
            size="small" 
            onClick={() => handleQuickAction(action.message)}
            disabled={isSending}
            style={{ 
              borderRadius: 2, 
              color: 'var(--text-secondary)', 
              borderColor: 'var(--border-line)',
              fontSize: 12,
              flexShrink: 0
            }}
          >
            {action.label}
          </Button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
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
            borderRadius: 2,
            fontFamily: 'var(--font-sans)',
            boxShadow: 'none',
            borderColor: 'var(--border-line)',
          }}
        />
        <Button 
          type="primary" 
          icon={<Send size={16} />} 
          onClick={handleSend}
          loading={isSending}
          style={{ 
            borderRadius: 2, 
            background: 'var(--accent-amber)',
            height: 32,
            paddingInline: 16
          }}
        />
      </div>
    </div>
  );
};
