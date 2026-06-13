import React from 'react';
import { Typography } from 'antd';

const { Title, Text } = Typography;

export const TagSelection: React.FC = () => {
  return (
    <div>
      <Title level={1} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>
        标签筛选
      </Title>
      <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)' }}>
        (此页面即将开发...)
      </Text>
    </div>
  );
};
