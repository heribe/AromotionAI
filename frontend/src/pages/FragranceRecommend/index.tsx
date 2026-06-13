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
      <div style={{ marginBottom: 24, borderBottom: '1px solid rgba(47, 54, 48, 0.1)', paddingBottom: 16 }}>
        <Title level={1} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>香调调配室</Title>
        <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16 }}>Formulation & Notes</Text>
      </div>

      <Row gutter={40} style={{ flex: 1, minHeight: 0 }}>
        {/* 左侧：配方区 */}
        <Col span={14} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div className="ledger-card" style={{ 
            padding: '40px 48px',
            flex: 1,
            overflowY: 'auto'
          }}>
            <div style={{ borderTop: '3px double var(--accent-moss)', borderBottom: '1px solid var(--border-line)', padding: '16px 0', marginBottom: 32, textAlign: 'center' }}>
              <Text style={{ letterSpacing: 2, fontSize: 12, color: 'var(--text-secondary)' }}>FORMULA NO. 01</Text>
              <Title level={3} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', margin: '8px 0 0 0' }}>晨露幽林 (Morning Mist)</Title>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
              {mockNotes.map((note, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'baseline' }}>
                  <div style={{ width: '80px', flexShrink: 0 }}>
                    <Text style={{ fontSize: 12, letterSpacing: 2, color: 'var(--text-secondary)', fontFamily: 'var(--font-serif)', fontStyle: 'italic' }}>{note.type}</Text>
                  </div>
                  <div style={{ flex: 1, borderBottom: '1px dashed var(--border-line)', paddingBottom: 16 }}>
                    <div style={{ fontSize: 20, fontFamily: 'var(--font-serif)', color: 'var(--accent-amber)', marginBottom: 8 }}>{note.name}</div>
                    <Text style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{note.desc}</Text>
                  </div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 48, padding: 32, background: 'var(--bg-ceramic)', border: '1px solid var(--border-line)', position: 'relative' }}>
              <div style={{ position: 'absolute', top: -12, left: 32, background: 'var(--bg-ceramic)', padding: '0 8px', color: 'var(--accent-moss)', fontFamily: 'var(--font-serif)', fontStyle: 'italic' }}>Inspiration</div>
              <Paragraph style={{ fontStyle: 'italic', color: 'var(--accent-moss)', marginBottom: 0, fontFamily: 'var(--font-serif)', fontSize: 15, lineHeight: 1.8 }}>
                "针对那些生活在一线城市、面临高压但内心渴望自然平静的独立女性。前调的佛手柑像破晓的阳光，中调的玫瑰不过分甜腻，尾调的木质与琥珀则像是给她们一个温暖的拥抱..."
              </Paragraph>
            </div>
          </div>
        </Col>

        {/* 右侧：对话区 */}
        <Col span={10} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <div className="ledger-card" style={{ 
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            padding: '24px'
          }}>
            <div style={{ padding: '16px 0', borderBottom: '1px solid var(--border-line)' }}>
              <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontStyle: 'italic' }}>Notes & Iterations</Text>
            </div>
            
            <div style={{ flex: 1, padding: 20, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Mock AI Message */}
              <div style={{ alignSelf: 'flex-start', background: 'var(--bg-ceramic)', border: '1px solid var(--border-line)', padding: '12px 16px', borderRadius: '4px 4px 4px 0', maxWidth: '85%' }}>
                <Text>我已经根据画像生成了初始方案。如果你觉得中调的玫瑰不够特别，我们可以尝试加入一点<Text strong style={{color: 'var(--accent-amber)'}}>藏红花</Text>来增加辛锐感。</Text>
              </div>
            </div>

            <div style={{ padding: '16px 0', borderTop: '1px solid var(--border-line)', background: 'var(--bg-card)' }}>
              <div style={{ display: 'flex', gap: 8 }}>
                <Input 
                  placeholder="告诉 AI 你的修改想法..." 
                  value={chatInput}
                  onChange={e => setChatInput(e.target.value)}
                  onPressEnter={() => setChatInput('')}
                  style={{ borderRadius: 4 }}
                />
                <Button type="primary" icon={<Send size={16} />} style={{ borderRadius: 4, background: 'var(--accent-amber)' }} />
              </div>
            </div>
          </div>
        </Col>
      </Row>
    </div>
  );
};
