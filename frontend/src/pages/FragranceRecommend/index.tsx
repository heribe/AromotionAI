import React, { useEffect, useState } from 'react';
import { Button, Typography, Modal, message } from 'antd';
import { useNavigate, useParams, useLocation } from 'react-router-dom';
import { ArrowLeft, RefreshCw } from 'lucide-react';
import { useFragranceStore } from '../../stores/useFragranceStore';
import { regenerate } from '../../services/api';
import { PlanList } from './components/PlanList';
import { ChatPanel } from './components/ChatPanel';
import { ReferenceDock } from './components/ReferenceDock';
import { ExtractionAnimation } from './components/ExtractionAnimation';
import './index.css';

const { Title, Text } = Typography;

/** router state 形态 */
interface RecommendLocationState {
  // 标签页点「生成」跳来：携带待生成的参数，进入「生成中」动画
  pendingGenerate?: { taskId: string; selectedTags: Record<string, Record<string, string[]>> };
}

export const FragranceRecommend: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const pendingGenerate = (location.state as RecommendLocationState | null)?.pendingGenerate;
  // pendingGenerate 场景下 id 是占位 "pending"，真实 sessionId 等 generate 完成后才有
  const sessionId = id === 'pending' ? null : id;
  const { initSession, generateAndLoad, isLoading, sessionId: storeSessionId, taskId } = useFragranceStore();

  const [animState, setAnimState] = useState<'processing' | 'fading_out' | 'completed'>('processing');
  const [regenerating, setRegenerating] = useState(false);

  useEffect(() => {
    // 场景一：标签页点「生成」跳来 → 进入生成中动画，后台调 generate
    if (pendingGenerate) {
      generateAndLoad(pendingGenerate.taskId, pendingGenerate.selectedTags, (realSessionId) => {
        // generate 完成，把占位路由替换成真实 sessionId（便于刷新/分享）
        navigate(`/recommend/${realSessionId}`, { replace: true });
      });
      return;
    }
    // 场景二：已有 sessionId（切回/直接进） → 拉取 session
    if (sessionId) {
      initSession(sessionId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
    if (!storeSessionId) return;
    Modal.confirm({
      title: '确认重新生成？',
      content: '重新生成将清空当前的对话历史，并基于原始标签生成全新的方案。',
      okText: '重新生成',
      cancelText: '取消',
      okButtonProps: { className: 'btn-amber-primary', loading: regenerating },
      onOk: async () => {
        setRegenerating(true);
        try {
          const result = await regenerate(storeSessionId, { planCount: 3 });
          useFragranceStore.getState().hydrateFromResult(result);
          message.success('已生成新方案');
        } catch {
          message.error('重新生成失败');
        } finally {
          setRegenerating(false);
        }
      },
    });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
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
        <div className="plan-panel" style={{ flex: 1, overflowY: 'auto', padding: '40px 48px', position: 'relative', background: 'var(--bg-green)' }}>
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
