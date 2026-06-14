import React, { useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Typography, Progress, Tag, Button, Space, Spin } from 'antd';
import { CheckCircle, Loader, Circle, MinusCircle, AlertCircle, ArrowLeft } from 'lucide-react';
import { useAnalysisStore } from '../../stores/useAnalysisStore';
import type { SubStepStatus } from '../../services/sse';

const { Title, Text } = Typography;

/** 子步骤状态图标 */
const StepIcon: React.FC<{ status: SubStepStatus }> = ({ status }) => {
  if (status === 'completed') return <CheckCircle size={18} color="var(--accent-moss)" />;
  if (status === 'running')
    return <Loader size={18} color="var(--accent-amber)" className="ant-spin-dot" />;
  if (status === 'skipped') return <MinusCircle size={18} color="var(--text-secondary)" />;
  return <Circle size={18} color="var(--text-secondary)" />;
};

/** 子步骤状态文字色 */
const stepTextStyle = (status: SubStepStatus): React.CSSProperties => ({
  color: status === 'completed' ? 'var(--text-primary)' : 'var(--text-secondary)',
  fontWeight: status === 'running' ? 600 : 400,
});

export const TaskProgress: React.FC = () => {
  const { taskId = '' } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const {
    progress,
    progressStatus,
    currentStep,
    subSteps,
    stepSummaries,
    progressError,
    fetchTaskStatus,
    subscribeProgress,
    unsubscribeProgress,
    resetProgress,
  } = useAnalysisStore();
  const navigatedRef = useRef(false);

  // mount 时先查任务真实状态：已终态则直接处理，未终态才订阅 SSE
  useEffect(() => {
    if (!taskId) return;
    let cancelled = false;
    (async () => {
      try {
        const task = await fetchTaskStatus(taskId);
        if (cancelled) return;
        if (task.status === 'completed') {
          // 已完成，直接跳报告页（不再订阅 SSE）
          if (!navigatedRef.current) {
            navigatedRef.current = true;
            navigate(`/report/${taskId}`, { replace: true });
          }
          return;
        }
        if (task.status === 'failed' || task.status === 'cancelled') {
          // 已失败/取消，展示终态错误，不订阅
          return;
        }
      } catch {
        // 查询失败则继续尝试订阅 SSE
      }
      // 任务仍在运行 → 订阅进度
      subscribeProgress(taskId);
    })();

    return () => {
      cancelled = true;
      unsubscribeProgress();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskId]);

  // 收到 complete 事件后跳报告页（用 ref 防重复，不调 resetProgress 避免闪烁）
  useEffect(() => {
    if (progressStatus === 'completed' && !navigatedRef.current) {
      navigatedRef.current = true;
      const timer = setTimeout(() => {
        navigate(`/report/${taskId}`, { replace: true });
      }, 1000);
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [progressStatus, taskId]);

  const isFailed = progressStatus === 'failed';
  const isCancelled = progressStatus === 'cancelled';

  return (
    <div>
      {/* 页头 */}
      <div style={{ marginBottom: 32, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Button
            type="text"
            icon={<ArrowLeft size={16} />}
            onClick={() => {
              resetProgress();
              navigate('/dashboard');
            }}
            style={{ marginBottom: 8, color: 'var(--text-secondary)' }}
          >
            返回工作台
          </Button>
          <Title level={2} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', margin: 0, fontWeight: 400 }}>
            分析进度 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16, color: 'var(--text-secondary)' }}>Analysis Progress</Text>
          </Title>
        </div>
        <Tag
          color={isFailed ? '#A0522D' : progressStatus === 'completed' ? 'var(--accent-moss)' : 'var(--accent-amber)'}
          style={{ borderRadius: 2, fontSize: 14, padding: '4px 12px' }}
        >
          {isFailed ? '失败' : isCancelled ? '已取消' : progressStatus === 'completed' ? '已完成' : '进行中'}
        </Tag>
      </div>

      {/* 总进度条 */}
      <Card bodyStyle={{ padding: '32px 40px' }} style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
          <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontSize: 18 }}>
            {isFailed ? '分析失败' : currentStep || '准备开始'}
          </Text>
          <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-amber)', fontSize: 24 }}>
            {progress}%
          </Text>
        </div>
        <Progress
          percent={progress}
          strokeColor={isFailed ? '#A0522D' : 'var(--accent-amber)'}
          trailColor="var(--border-line)"
          showInfo={false}
          status={isFailed ? 'exception' : progressStatus === 'completed' ? 'success' : 'active'}
        />
        {isFailed && progressError && (
          <div style={{ marginTop: 16, padding: 16, background: 'rgba(160, 82, 45, 0.08)', borderRadius: 4 }}>
            <Space align="start">
              <AlertCircle size={18} color="#A0522D" />
              <Text style={{ color: '#A0522D', fontSize: 13, wordBreak: 'break-all' }}>{progressError}</Text>
            </Space>
          </div>
        )}
      </Card>

      {/* 子步骤瀑布 */}
      <Card bodyStyle={{ padding: '32px 40px' }}>
        <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', fontWeight: 400, marginBottom: 24 }}>
          步骤详情 <Text style={{ fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 14, color: 'var(--text-secondary)', fontWeight: 400 }}>Steps</Text>
        </Title>
        {subSteps.length === 0 && (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
            <Text style={{ display: 'block', marginTop: 12, color: 'var(--text-secondary)' }}>等待进度推送…</Text>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
          {subSteps.map((step, idx) => (
            <div key={step.name} style={{ display: 'flex', gap: 16, paddingBottom: idx === subSteps.length - 1 ? 0 : 20 }}>
              {/* 左侧连线 */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', paddingTop: 2 }}>
                <StepIcon status={step.status} />
                {idx < subSteps.length - 1 && (
                  <div
                    style={{
                      width: 2,
                      flex: 1,
                      minHeight: 24,
                      background: step.status === 'completed' ? 'var(--accent-moss)' : 'var(--border-line)',
                      marginTop: 4,
                    }}
                  />
                )}
              </div>
              {/* 右侧内容 */}
              <div style={{ flex: 1, paddingBottom: idx === subSteps.length - 1 ? 0 : 0 }}>
                <Text style={{ fontSize: 15, ...stepTextStyle(step.status) }}>{step.name}</Text>
                {stepSummaries[step.name] && (
                  <Text style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                    {stepSummaries[step.name]}
                  </Text>
                )}
                {step.status === 'running' && !stepSummaries[step.name] && (
                  <Text style={{ display: 'block', fontSize: 13, color: 'var(--accent-amber)', marginTop: 4 }}>
                    正在处理…
                  </Text>
                )}
                {step.status === 'skipped' && !stepSummaries[step.name] && (
                  <Text style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }}>
                    已跳过（当前模式不执行此步骤）
                  </Text>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default TaskProgress;
