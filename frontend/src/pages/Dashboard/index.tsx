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
      <div style={{ marginBottom: 32 }}>
        <Title level={2} style={{ fontFamily: 'var(--font-serif)', margin: 0 }}>工作台</Title>
        <Text type="secondary">欢迎回来，调香师。这里是你的数据洞察中心。</Text>
      </div>

      <Row gutter={[24, 24]}>
        <Col span={8}>
          <Card>
            <Statistic title="分析任务总数" value={12} suffix="项" valueStyle={{ color: 'var(--accent-amber)' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="生成香调方案" value={45} suffix="个" valueStyle={{ color: 'var(--accent-moss)' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="洞察博主画像" value={320} suffix="位" />
          </Card>
        </Col>
      </Row>

      <div style={{ marginTop: 40 }}>
        <Title level={4} style={{ fontFamily: 'var(--font-serif)' }}>最近分析任务</Title>
        <Card bodyStyle={{ padding: 0 }}>
          <Table 
            dataSource={mockTasks} 
            rowKey="id"
            pagination={false}
            columns={[
              { title: '任务名称', dataIndex: 'title', key: 'title' },
              { title: '状态', dataIndex: 'status', key: 'status', render: (text) => <span style={{ color: text === '进行中' ? 'var(--accent-amber)' : 'inherit' }}>{text}</span> },
              { title: '创建时间', dataIndex: 'date', key: 'date' },
              { title: '操作', key: 'action', render: () => <a style={{ color: 'var(--accent-moss)' }}>查看报告</a> }
            ]}
          />
        </Card>
      </div>
    </div>
  );
};
