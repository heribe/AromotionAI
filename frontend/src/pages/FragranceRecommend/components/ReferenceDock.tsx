import React from 'react';
import { Typography, Tag, Space, Skeleton } from 'antd';
import { useFragranceStore } from '../../../stores/useFragranceStore';
import '../index.css';

const { Title, Paragraph, Text } = Typography;

interface Props {
  isSkeleton?: boolean;
}

export const ReferenceDock: React.FC<Props> = ({ isSkeleton = false }) => {
  const { icebergAnalysis, selectedTags } = useFragranceStore();

  return (
    <div style={{
      width: 300,
      flexShrink: 0,
      height: '100%',
      borderRight: '1px solid var(--border-line)',
      background: 'var(--bg-paper)',
      display: 'flex',
      flexDirection: 'column',
      overflowY: 'auto'
    }}>
      <div style={{ padding: '24px' }}>
        <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', marginBottom: 24, fontSize: 18, fontWeight: 'normal' }}>
          参考资料坞
          <Text style={{ display: 'block', fontStyle: 'italic', fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>Reference Context</Text>
        </Title>

        {/* 标签上下文 */}
        {selectedTags && Object.keys(selectedTags).length > 0 && (
          <div style={{ marginBottom: 32 }}>
            <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontSize: 15, marginBottom: 16, display: 'block' }}>
              用户标签画像
            </Text>
            
            {Object.entries(selectedTags).map(([dimName, subDims]) => {
              const allTagsInDim = Object.values(subDims).flat();
              if (allTagsInDim.length === 0) return null;
              
              return (
                <div key={dimName} style={{ marginBottom: 16 }}>
                  <Text style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, display: 'block' }}>
                    {dimName}
                  </Text>
                  <Space size={[8, 8]} wrap>
                    {Object.entries(subDims).map(([subName, tags]) => 
                      tags.map(tag => (
                        <Tag 
                          key={`${dimName}-${subName}-${tag}`}
                          style={{ 
                            margin: 0, 
                            borderRadius: 2, 
                            background: 'rgba(47, 54, 48, 0.04)', 
                            border: '1px solid var(--border-line)',
                            color: 'var(--text-secondary)'
                          }}
                        >
                          {tag}
                        </Tag>
                      ))
                    )}
                  </Space>
                </div>
              );
            })}
          </div>
        )}

        {/* 冰山分析 */}
        <div>
          <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontSize: 15, marginBottom: 16, display: 'block' }}>
            冰山需求分析
          </Text>
          
          {isSkeleton || !icebergAnalysis ? (
            <div style={{ marginTop: 24 }}>
              <Skeleton active paragraph={{ rows: 2 }} title={{ width: 80 }} />
              <Skeleton active paragraph={{ rows: 2 }} title={{ width: 80 }} style={{ marginTop: 24 }} />
              <Skeleton active paragraph={{ rows: 2 }} title={{ width: 80 }} style={{ marginTop: 24 }} />
            </div>
          ) : (
            <>
              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ color: 'var(--text-primary)', fontSize: 13, marginBottom: 8, display: 'block' }}>
                  显性行为层 <Text style={{ color: 'var(--text-secondary)', fontWeight: 'normal', fontSize: 12 }}>(Surface)</Text>
                </Text>
                <Paragraph style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                  {icebergAnalysis.surface}
                </Paragraph>
              </div>

              <div style={{ marginBottom: 24 }}>
                <Text strong style={{ color: 'var(--text-primary)', fontSize: 13, marginBottom: 8, display: 'block' }}>
                  情感价值层 <Text style={{ color: 'var(--text-secondary)', fontWeight: 'normal', fontSize: 12 }}>(Middle)</Text>
                </Text>
                <Paragraph style={{ color: 'var(--text-secondary)', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                  {icebergAnalysis.middle}
                </Paragraph>
              </div>

              <div>
                <Text strong style={{ color: 'var(--accent-amber)', fontSize: 13, marginBottom: 8, display: 'block' }}>
                  深层核心需求 <Text style={{ color: 'var(--text-secondary)', fontWeight: 'normal', fontSize: 12 }}>(Deep)</Text>
                </Text>
                <div style={{
                  padding: '12px 16px',
                  background: 'rgba(193, 136, 65, 0.05)',
                  border: '1px solid rgba(193, 136, 65, 0.25)'
                }}>
                  <Paragraph style={{ color: 'var(--text-primary)', fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                    {icebergAnalysis.deep}
                  </Paragraph>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
