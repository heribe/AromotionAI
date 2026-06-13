import React, { useEffect, useState } from 'react';
import { Typography, Button, Tabs, Card, Drawer, Space, Spin } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, ArrowRight } from 'lucide-react';
import { useAnalysisStore } from '../../stores/useAnalysisStore';
import { DimensionTabContent } from './components/DimensionTabContent';

const { Title, Text, Paragraph } = Typography;

export const ProfileReport: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { currentReport, reportLoading, fetchReport } = useAnalysisStore();
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    if (taskId) {
      fetchReport(taskId);
    }
  }, [taskId, fetchReport]);

  if (reportLoading || !currentReport) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  const report = currentReport;

  return (
    <div>
      {/* 顶部导航 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <Button
          type="text"
          icon={<ArrowLeft size={16} />}
          onClick={() => navigate('/dashboard')}
          style={{ color: 'var(--text-secondary)', padding: '4px 8px' }}
        >
          返回工作台
        </Button>
        <Space size={16}>
          <Button
            icon={<FileText size={14} />}
            onClick={() => setDrawerOpen(true)}
            style={{ borderRadius: 2, borderColor: 'var(--border-line)', color: 'var(--accent-moss)' }}
          >
            查看文字报告
          </Button>
          <Button
            type="primary"
            className="btn-amber-primary"
            icon={<ArrowRight size={14} />}
            onClick={() => navigate(`/tags/${taskId}`)}
          >
            前往标签筛选
          </Button>
        </Space>
      </div>

      {/* 页面标题 */}
      <div style={{ marginBottom: 32, borderBottom: '1px solid rgba(47, 54, 48, 0.1)', paddingBottom: 24 }}>
        <Title level={1} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>画像报告</Title>
        <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16 }}>Profile Analysis Report</Text>
      </div>

      {/* 博主信息卡片 */}
      <Card bodyStyle={{ padding: '28px 40px' }} style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={3} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--text-primary)', fontWeight: 500 }}>
              {report.bloggerName}
            </Title>
            <Text style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4, display: 'block' }}>
              {report.platform} · 粉丝 {report.followerCount} · {report.analysisLevel}分析
            </Text>
          </div>
          <Text style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
            分析时间：{report.analysisTime}
          </Text>
        </div>
      </Card>

      {/* 综合画像总结 */}
      <div style={{
        padding: '28px 40px',
        background: 'var(--bg-ceramic)',
        border: '1px solid var(--border-line)',
        borderRadius: 2,
        marginBottom: 40,
        position: 'relative',
      }}>
        <div style={{
          position: 'absolute', top: -12, left: 32,
          background: 'var(--bg-ceramic)', padding: '0 8px',
          color: 'var(--accent-moss)', fontFamily: 'var(--font-serif)', fontStyle: 'italic', fontSize: 14,
        }}>
          综合画像总结
        </div>
        <Paragraph style={{ color: 'var(--text-primary)', marginBottom: 0, lineHeight: 1.8, fontSize: 15 }}>
          {report.overallSummary}
        </Paragraph>
      </div>

      {/* 四维度 Tab */}
      <Tabs
        type="card"
        items={report.dimensions.map(dim => ({
          key: dim.dimensionId,
          label: (
            <span style={{ padding: '0 8px' }}>
              {dim.dimensionName}
            </span>
          ),
          children: <DimensionTabContent dimension={dim} />,
        }))}
        style={{ marginBottom: 48 }}
      />

      {/* 底部操作 */}
      <div style={{
        textAlign: 'center',
        padding: '32px 0',
        borderTop: '1px solid rgba(47, 54, 48, 0.1)',
      }}>
        <Button
          type="primary"
          size="large"
          icon={<ArrowRight size={16} />}
          onClick={() => navigate(`/tags/${taskId}`)}
          className="btn-amber-primary"
          style={{ paddingInline: 40, height: 48, fontSize: 16 }}
        >
          前往标签筛选
        </Button>
      </div>

      {/* 文字报告抽屉 */}
      <Drawer
        title={<span style={{ fontFamily: 'var(--font-serif)' }}>文字报告</span>}
        placement="right"
        width={640}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{ body: { background: 'var(--bg-paper)', padding: '32px 40px' } }}
      >
        <div style={{ fontFamily: 'var(--font-sans)', lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
          {report.fullReportMarkdown.split('\n').map((line, i) => {
            if (line.startsWith('# ')) {
              return <Title key={i} level={2} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 500, marginTop: i > 0 ? 32 : 0 }}>{line.replace('# ', '')}</Title>;
            }
            if (line.startsWith('## ')) {
              return <Title key={i} level={3} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 500, marginTop: 24 }}>{line.replace('## ', '')}</Title>;
            }
            if (line.startsWith('### ')) {
              return <Title key={i} level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontWeight: 500, marginTop: 16 }}>{line.replace('### ', '')}</Title>;
            }
            if (line.startsWith('**') && line.endsWith('**')) {
              return <Paragraph key={i} strong style={{ color: 'var(--accent-moss)' }}>{line.replace(/\*\*/g, '')}</Paragraph>;
            }
            if (line.startsWith('- ')) {
              return <Paragraph key={i} style={{ paddingLeft: 16, marginBottom: 4, color: 'var(--text-primary)' }}>• {line.replace('- ', '')}</Paragraph>;
            }
            if (line.trim() === '') {
              return <div key={i} style={{ height: 8 }} />;
            }
            return <Paragraph key={i} style={{ color: 'var(--text-primary)', marginBottom: 4 }}>{line}</Paragraph>;
          })}
        </div>
      </Drawer>
    </div>
  );
};
