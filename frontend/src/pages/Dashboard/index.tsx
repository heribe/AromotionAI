import React from 'react';
import { Card, Typography, Row, Col, Statistic, Table } from 'antd';

const { Title, Text } = Typography;

export const Dashboard: React.FC = () => {
  // Mock 数据
  const mockTasks = [
    { id: '1', title: '2026 春夏新款花香调分析', status: '已完成', date: '2026-06-12' },
    { id: '2', title: '东方木质调受众画像挖掘', status: '进行中', date: '2026-06-13' },
    { id: '3', title: '柑橘调竞品博主粉丝分析', status: '排队中', date: '2026-06-14' },
  ];

  return (
    <div>
      <div style={{ marginBottom: 48, borderBottom: '1px solid rgba(47, 54, 48, 0.1)', paddingBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <Title level={1} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>工作台</Title>
          <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16 }}>Perfumer's Dashboard & Analysis</Text>
        </div>
        <Text style={{ color: 'var(--accent-amber)', letterSpacing: 2, fontSize: 11, textTransform: 'uppercase' }}>Session Active // Artisan</Text>
      </div>

      <Row gutter={[32, 32]}>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>分析任务总数</Text>} value={12} suffix="项" valueStyle={{ color: 'var(--text-primary)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>生成香调方案</Text>} value={45} suffix="个" valueStyle={{ color: 'var(--accent-amber)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>洞察博主画像</Text>} value={320} suffix="位" valueStyle={{ color: 'var(--text-primary)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
      </Row>

      <div style={{ marginTop: 64 }}>
        <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 400, marginBottom: 24 }}>近期调香任务 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>Recent Formulation Tasks</Text></Title>
        <Card bodyStyle={{ padding: '32px 40px' }}>
          <Table 
            dataSource={mockTasks} 
            rowKey="id"
            pagination={false}
            columns={[
              { title: '任务名称', dataIndex: 'title', key: 'title' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (text) => <span style={{ color: text === '进行中' ? 'var(--accent-amber)' : 'inherit' }}>{text}</span> },
              { title: '创建时间', dataIndex: 'date', key: 'date' },
              { title: '操作', key: 'action', render: () => <a style={{ color: 'var(--accent-amber)' }}>查看报告</a> }
            ]}
          />
        </Card>
      </div>
    </div>
  );
};
