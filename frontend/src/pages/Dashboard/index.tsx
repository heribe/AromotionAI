import React, { useEffect, useState } from 'react';
import { Card, Typography, Row, Col, Statistic, Table, Button, Input, Radio, Space, Modal, Tag, Progress } from 'antd';
import { useNavigate } from 'react-router-dom';
import { Plus, Search, ArrowRight } from 'lucide-react';
import { useAnalysisStore } from '../../stores/useAnalysisStore';
import type { AnalysisTask } from '../../types/analysis';

const { Title, Text, Paragraph } = Typography;

/** 状态标签颜色映射 */
const statusConfig: Record<string, { color: string; label: string }> = {
  completed: { color: 'var(--accent-moss)', label: '已完成' },
  processing: { color: 'var(--accent-amber)', label: '生成配方中' },
  analyzing: { color: 'var(--accent-amber)', label: '分析中' },
  collecting: { color: 'var(--accent-amber)', label: '采集中' },
  waiting_tags: { color: 'var(--accent-amber)', label: '待筛选标签' },
  pending: { color: 'var(--text-secondary)', label: '排队中' },
  failed: { color: '#A0522D', label: '失败' },
};

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { taskList, taskListLoading, fetchTaskList } = useAnalysisStore();
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [bloggerUrl, setBloggerUrl] = useState('');
  const [analysisLevel, setAnalysisLevel] = useState('标准');

  useEffect(() => {
    fetchTaskList();
  }, [fetchTaskList]);

  // 按状态分类
  const runningTasks = taskList.filter(t => ['pending', 'collecting', 'analyzing', 'waiting_tags', 'processing'].includes(t.status));
  const completedTasks = taskList.filter(t => t.status === 'completed');
  const failedTasks = taskList.filter(t => t.status === 'failed');

  // 统计数据
  const stats = {
    totalTasks: taskList.length,
    completedCount: completedTasks.length,
    runningCount: runningTasks.length,
  };

  const handleCreateTask = () => {
    // Mock: 直接关闭并刷新
    setCreateModalOpen(false);
    setBloggerUrl('');
    fetchTaskList();
  };

  const columns = [
    {
      title: '博主名称',
      dataIndex: 'bloggerName',
      key: 'bloggerName',
      render: (text: string, record: AnalysisTask) => (
        <div>
          <Text strong style={{ color: 'var(--text-primary)' }}>{text}</Text>
          <br />
          <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{record.platform} · {record.analysisLevel}</Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const cfg = statusConfig[status] || { color: 'inherit', label: status };
        return <Tag color={cfg.color} style={{ borderRadius: 2, fontFamily: 'var(--font-sans)' }}>{cfg.label}</Tag>;
      },
    },
    {
      title: '时间',
      key: 'time',
      width: 160,
      render: (_: unknown, record: AnalysisTask) => (
        <Text style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          {record.completedAt || record.createdAt}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, record: AnalysisTask) => (
        <Space size={16}>
          {record.status === 'completed' && (
            <>
              <a
                style={{ color: 'var(--accent-amber)' }}
                onClick={() => navigate(`/report/${record.taskId}`)}
              >
                查看画像
              </a>
              <a
                style={{ color: 'var(--accent-moss)' }}
                onClick={() => navigate(`/recommend/${record.taskId}`)}
              >
                进入调配室
              </a>
            </>
          )}
          {['analyzing', 'collecting', 'processing'].includes(record.status) && (
            <a style={{ color: 'var(--accent-amber)' }}>查看进度</a>
          )}
          {record.status === 'failed' && (
            <Text style={{ color: '#A0522D', fontSize: 13 }}>{record.errorMessage || '分析失败'}</Text>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: 48, borderBottom: '1px solid rgba(47, 54, 48, 0.1)', paddingBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <div>
          <Title level={1} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>工作台</Title>
          <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16 }}>Perfumer's Dashboard & Analysis</Text>
        </div>
        <Text style={{ color: 'var(--accent-amber)', letterSpacing: 2, fontSize: 11, textTransform: 'uppercase' }}>Session Active // Artisan</Text>
      </div>

      {/* 新建分析区域 */}
      <Card bodyStyle={{ padding: '32px 40px' }} style={{ marginBottom: 48 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24 }}>
          <div>
            <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 400, margin: 0 }}>
              新建分析 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>New Analysis</Text>
            </Title>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, alignItems: 'flex-end' }}>
          <div style={{ flex: 1 }}>
            <Text style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, display: 'block' }}>博主链接</Text>
            <Input
              placeholder="https://www.douyin.com/user/..."
              value={bloggerUrl}
              onChange={(e) => setBloggerUrl(e.target.value)}
              prefix={<Search size={14} color="var(--text-secondary)" />}
              style={{ borderRadius: 2, height: 40 }}
            />
          </div>
          <Button
            type="primary"
            icon={<Plus size={14} />}
            onClick={() => setCreateModalOpen(true)}
            style={{ borderRadius: 2, background: 'var(--accent-amber)', height: 40, paddingInline: 24 }}
          >
            开始分析
          </Button>
        </div>

        <div style={{ marginTop: 20 }}>
          <Text style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8, display: 'block' }}>分析等级</Text>
          <Radio.Group value={analysisLevel} onChange={e => setAnalysisLevel(e.target.value)}>
            <Radio value="快速">快速 (3-5min)</Radio>
            <Radio value="标准">标准 (8-15min)</Radio>
            <Radio value="深度">深度 (20-40min)</Radio>
          </Radio.Group>
        </div>
      </Card>

      {/* 统计卡片 */}
      <Row gutter={[32, 32]} style={{ marginBottom: 48 }}>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>分析任务总数</Text>} value={stats.totalTasks} suffix="项" valueStyle={{ color: 'var(--text-primary)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>已完成</Text>} value={stats.completedCount} suffix="项" valueStyle={{ color: 'var(--accent-amber)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card bodyStyle={{ padding: '32px 24px' }}>
            <Statistic title={<Text style={{fontFamily: 'var(--font-serif)', color: 'var(--text-secondary)', fontSize: 16}}>进行中</Text>} value={stats.runningCount} suffix="项" valueStyle={{ color: 'var(--text-primary)', fontSize: 36, fontFamily: 'var(--font-serif)', fontWeight: 400 }} />
          </Card>
        </Col>
      </Row>

      {/* 进行中的任务 */}
      {runningTasks.length > 0 && (
        <div style={{ marginBottom: 48 }}>
          <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 400, marginBottom: 24 }}>
            进行中的任务 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>Running Tasks</Text>
          </Title>
          <Row gutter={[24, 24]} align="stretch">
            {runningTasks.map(task => (
              <Col span={12} key={task.taskId}>
                <Card 
                  style={{ height: '100%' }} 
                  bodyStyle={{ padding: '24px 32px', height: '100%', display: 'flex', flexDirection: 'column' }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                    <div>
                      <Text strong>{task.bloggerName}</Text>
                      <Text style={{ marginLeft: 12, fontSize: 12, color: 'var(--text-secondary)' }}>{task.analysisLevel}</Text>
                    </div>
                    <Tag color="var(--accent-amber)" style={{ borderRadius: 2 }}>{statusConfig[task.status]?.label}</Tag>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <Progress style={{ flex: 1 }} percent={task.progress} strokeColor="var(--accent-amber)" trailColor="var(--border-line)" size="small" />
                    {task.status === 'waiting_tags' && (
                      <Button 
                        type="primary" 
                        size="small" 
                        style={{ background: 'var(--accent-moss)', borderRadius: 2, fontSize: 12 }}
                        onClick={() => navigate(`/tags/${task.taskId}`)}
                      >
                        前往筛选标签
                      </Button>
                    )}
                    {task.status === 'processing' && (
                      <Button 
                        type="primary" 
                        size="small" 
                        style={{ background: 'var(--accent-amber)', borderRadius: 2, fontSize: 12 }}
                        onClick={() => navigate(`/recommend/${task.taskId}`)}
                      >
                        进入调配室
                      </Button>
                    )}
                    {['pending', 'collecting', 'analyzing'].includes(task.status) && (
                      <Button 
                        type="default" 
                        size="small" 
                        style={{ borderColor: 'var(--border-line)', color: 'var(--text-secondary)', borderRadius: 2, fontSize: 12 }}
                        onClick={() => navigate(`/task/${task.taskId}`)}
                      >
                        查看进度现场
                      </Button>
                    )}
                  </div>
                  <Text style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 'auto', paddingTop: 8, display: 'block' }}>{task.currentStep}</Text>
                </Card>
              </Col>
            ))}
          </Row>
        </div>
      )}

      {/* 历史记录 */}
      <div>
        <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 400, marginBottom: 24 }}>
          历史记录 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>History</Text>
        </Title>
        <Card bodyStyle={{ padding: '32px 40px' }}>
          <Table
            dataSource={[...completedTasks, ...failedTasks]}
            rowKey="taskId"
            loading={taskListLoading}
            pagination={{ pageSize: 10, size: 'small' }}
            columns={columns}
          />
        </Card>
      </div>

      {/* 新建分析弹窗（确认） */}
      <Modal
        title={<span style={{ fontFamily: 'var(--font-serif)' }}>确认创建分析任务</span>}
        open={createModalOpen}
        onOk={handleCreateTask}
        onCancel={() => setCreateModalOpen(false)}
        okText="开始分析"
        cancelText="取消"
        okButtonProps={{ style: { background: 'var(--accent-amber)', borderRadius: 2 } }}
      >
        <Paragraph style={{ color: 'var(--text-secondary)' }}>
          将对以下博主进行 <Text strong style={{ color: 'var(--accent-amber)' }}>{analysisLevel}</Text> 级别的受众画像分析：
        </Paragraph>
        <Paragraph code style={{ wordBreak: 'break-all' }}>
          {bloggerUrl || '(请在输入框填写博主链接)'}
        </Paragraph>
      </Modal>
    </div>
  );
};
