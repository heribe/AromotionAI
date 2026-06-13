import React, { useState } from 'react';
import { Row, Col, Typography, Input, Button, Divider } from 'antd';
import { Send } from 'lucide-react';

const { Title, Text, Paragraph } = Typography;

export const FragranceRecommend: React.FC = () => {
  const [chatInput, setChatInput] = useState('');

  // Mock 数据
  const mockNotes = [
    { type: '前调', name: '佛手柑, 粉红胡椒', desc: '带来清晨露水般的清新与微小的辛辣刺激感，吸引注意力。' },
    { type: '中调', name: '大马士革玫瑰, 茉莉', desc: '核心花香，优雅而不媚俗，体现核心用户群的独立与精致。' },
    { type: '后调', name: '雪松, 广藿香, 琥珀', desc: '沉稳的木质底色，琥珀带来肌肤相亲的温暖感，留香持久。' },
  ];

  return (
    <div style={{ height: 'calc(100vh - 144px)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ fontFamily: 'var(--font-serif)', margin: 0 }}>香调调配室</Title>
        <Text type="secondary">基于画像生成的初始方案，你可以通过右侧对话微调香材配比。</Text>
      </div>

      <Row gutter={40} style={{ flex: 1, minHeight: 0 }}>
        {/* 左侧：配方区 */}
        <Col span={14} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ 
            background: 'var(--bg-card)', 
            border: '1px solid var(--border-line)',
            borderRadius: 4,
            padding: 32,
            flex: 1,
            overflowY: 'auto'
          }}>
            <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)' }}>方案：晨露幽林 (Morning Mist)</Title>
            <Divider style={{ borderColor: 'var(--border-line)' }} />
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {mockNotes.map((note, index) => (
                <div key={index} style={{ borderLeft: '2px solid var(--border-line)', paddingLeft: 16 }}>
                  <Text type="secondary" style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 }}>{note.type}</Text>
                  <div style={{ fontSize: 18, fontWeight: 500, margin: '4px 0', color: 'var(--accent-amber)' }}>{note.name}</div>
                  <Text type="secondary">{note.desc}</Text>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 40, padding: 20, background: 'var(--bg-ceramic)', borderLeft: '2px solid var(--accent-moss)' }}>
              <Title level={5} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)' }}>创作灵感</Title>
              <Paragraph style={{ fontStyle: 'italic', color: 'var(--text-secondary)', marginBottom: 0 }}>
                "针对那些生活在一线城市、面临高压但内心渴望自然平静的独立女性。前调的佛手柑像破晓的阳光，中调的玫瑰不过分甜腻，尾调的木质与琥珀则像是给她们一个温暖的拥抱..."
              </Paragraph>
            </div>
          </div>
        </Col>

        {/* 右侧：对话区 */}
        <Col span={10} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div style={{ 
            border: '1px solid var(--border-line)',
            borderRadius: 4,
            background: '#fff',
            flex: 1,
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div style={{ padding: 16, borderBottom: '1px solid var(--border-line)', background: 'var(--bg-card)' }}>
              <Text strong>AI 调香助理</Text>
            </div>
            
            <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Mock AI Message */}
              <div style={{ alignSelf: 'flex-start', background: 'var(--bg-ceramic)', border: '1px solid var(--border-line)', padding: '12px 16px', borderRadius: '8px 8px 8px 0', maxWidth: '85%' }}>
                <Text>我已经根据画像生成了初始方案。如果你觉得中调的玫瑰不够特别，我们可以尝试加入一点<Text strong style={{color: 'var(--accent-amber)'}}>藏红花</Text>来增加辛锐感。</Text>
              </div>
            </div>

            <div style={{ padding: 16, borderTop: '1px solid var(--border-line)', background: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input 
                  placeholder="告诉 AI 你的修改想法..." 
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onPressEnter={() => setChatInput('')}
                  style={{ borderRadius: 4 }}
                />
                <Button type="primary" icon={<Send size={16} />} style={{ borderRadius: 4, background: 'var(--accent-moss)' }} />
              </div>
            </div>
          </div>
        </Col>
      </Row>
    </div>
  );
};
