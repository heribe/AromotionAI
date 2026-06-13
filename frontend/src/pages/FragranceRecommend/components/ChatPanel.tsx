import React, { useEffect, useRef } from 'react';
import { useFragranceStore } from '../../../stores/useFragranceStore';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import '../index.css';

export const ChatPanel: React.FC = () => {
  const { messages, isSending } = useFragranceStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  return (
    <div className="chat-panel" style={{ height: '100%', borderLeft: '1px solid var(--border-line)', background: 'var(--bg-green)' }}>
      {/* 消息列表区 */}
      <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '24px 24px' }}>
        {messages.map(msg => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        
        {/* 正在输入指示器 */}
        {isSending && (
          <div className="typing-indicator">
            <span style={{ fontSize: 13, color: 'var(--text-secondary)', marginRight: 8, fontFamily: 'var(--font-serif)' }}>AI 调香师正在构思</span>
            <div className="dot" />
            <div className="dot" />
            <div className="dot" />
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 输入区 */}
      <ChatInput />
    </div>
  );
};
