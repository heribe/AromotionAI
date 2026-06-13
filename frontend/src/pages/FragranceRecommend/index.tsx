import React, { useEffect, useState } from 'react';
import { Button, Typography, Modal, Spin } from 'antd';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, BarChart2 } from 'lucide-react';
import { useFragranceStore } from '../../stores/useFragranceStore';
import { PlanList } from './components/PlanList';
import { ChatPanel } from './components/ChatPanel';
import { ReferenceDock } from './components/ReferenceDock';
import { ExtractionAnimation } from './components/ExtractionAnimation';
import './index.css';

const { Title, Text } = Typography;

export const FragranceRecommend: React.FC = () => {
  const navigate = useNavigate();
  // 在实际项目中，sessionId 应该从 useParams 获取。这里作为 Mock 演示先写死 'session-001'
  const sessionId = 'session-001'; 
  const { initSession, isLoading, taskId } = useFragranceStore();

  const [animState, setAnimState] = useState<'processing' | 'fading_out' | 'completed'>('processing');

  useEffect(() => {
    initSession(sessionId);
  }, [initSession, sessionId]);

  // 处理状态流转编排
  useEffect(() => {
    if (isLoading) {
      setAnimState('processing');
    } else if (animState === 'processing') {
      setAnimState('fading_out');
      setTimeout(() => {
        setAnimState('completed');
      }, 500); // 等待退场动画结束
    }
  }, [isLoading, animState]);

  const handleRegenerate = () => {
    Modal.confirm({
      title: '确认重新生成？',
      content: '重新生成将清空当前的对话历史，并基于原始标签生成全新的方案。',
      okText: '重新生成',
      cancelText: '取消',
      okButtonProps: { style: { background: 'var(--accent-amber)', borderRadius: 2 } },
      onOk: () => {
        // Mock 刷新
        initSession(sessionId);
      }
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px - 48px)' }}>
      {/* 顶部导航 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '16px 24px',
        borderBottom: '1px solid var(--border-line)',
        background: 'var(--bg-paper)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <Button
            type="text"
            icon={<ArrowLeft size={16} />}
            onClick={() => navigate('/')}
            style={{ color: 'var(--text-secondary)', padding: '4px 8px' }}
          >
            返回首页
          </Button>
          <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', margin: 0 }}>
            动态配方工坊 <Text style={{ fontStyle: 'italic', fontSize: 13, color: 'var(--text-secondary)', fontWeight: 'normal' }}>Dynamic Formulation</Text>
          </Title>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <Button
            onClick={() => {
              Modal.confirm({
                title: '确认重新设置标签？',
                content: '这将离开当前调配室，未保存的进度可能会丢失。',
                okText: '确认',
                cancelText: '取消',
                okButtonProps: { style: { background: 'var(--accent-moss)', borderRadius: 2 } },
                onOk: () => navigate(`/tags/${taskId}`)
              });
            }}
            style={{ borderRadius: 2, borderColor: 'var(--border-line)', color: 'var(--text-primary)' }}
          >
            重新设置标签
          </Button>
          <Button
            icon={<RefreshCw size={14} />}
            onClick={handleRegenerate}
            style={{ borderRadius: 2, borderColor: 'var(--border-line)', color: 'var(--text-primary)' }}
          >
            重新生成
          </Button>
        </div>
      </div>

      {/* 三栏主体 */}
      <div className="recommend-page" style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        
        {/* 左侧参考资料区 */}
        <ReferenceDock isSkeleton={animState !== 'completed'} />

        {/* 中间方案区 / 加载区 */}
        <div className="plan-panel" style={{ flex: 1, overflowY: 'auto', padding: '32px 48px', position: 'relative' }}>
          {animState !== 'completed' ? (
            <ExtractionAnimation isFadingOut={animState === 'fading_out'} />
          ) : (
            <PlanList />
          )}
        </div>

        {/* 右侧对话区 */}
        <div style={{ width: 400, minWidth: 360, flexShrink: 0, opacity: animState === 'completed' ? 1 : 0.6, pointerEvents: animState === 'completed' ? 'auto' : 'none', transition: 'opacity 0.5s' }}>
          <ChatPanel />
        </div>
      </div>
    </div>
  );
};
