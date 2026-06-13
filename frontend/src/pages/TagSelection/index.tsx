import React, { useEffect } from 'react';
import { Typography, Button, Spin, Row, Col, Card, Space, Checkbox, Radio, message } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkles, AlertCircle } from 'lucide-react';
import { useAnalysisStore } from '../../stores/useAnalysisStore';
import type { TagSubDimension } from '../../types/analysis';

const { Title, Text, Paragraph } = Typography;

export const TagSelection: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { 
    tagDimensions, 
    tagSelections, 
    tagsLoading, 
    fetchTags, 
    toggleTag, 
    getSelectedTags 
  } = useAnalysisStore();

  useEffect(() => {
    if (taskId) {
      fetchTags(taskId);
    }
  }, [taskId, fetchTags]);

  if (tagsLoading || tagDimensions.length === 0) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
        <Spin size="large" />
      </div>
    );
  }

  // 生成所有的已选标签的一维数组，用于底部预览展示
  const allSelectedTagsList: string[] = [];
  getSelectedTags().forEach(item => {
    allSelectedTagsList.push(...item.tags);
  });

  const handleGenerate = async () => {
    if (allSelectedTagsList.length === 0) {
      message.warning('请至少保留一个标签用于生成推荐！');
      return;
    }
    
    /* =========================================================================
     * [TODO] 接入真实后端时的替换逻辑：
     * =========================================================================
     * 1. 整理好选中的标签，调用真实后端接口（如 POST /api/v1/fragrance/generate）
     *    const res = await backendApi.submitTags(taskId, getSelectedTags());
     * 2. 调用成功后，后端任务状态可能变为 processing，拿到 sessionId
     *    const newSessionId = res.sessionId || taskId;
     * 3. 跳转到调配室页面：
     *    navigate(`/recommend/${newSessionId}`);
     * =========================================================================
     */
     
    // 当前 Mock 环境下直接写死跳转
    navigate('/recommend');
  };

  /** 渲染单个子维度的标签组 */
  const renderSubDimension = (sub: TagSubDimension) => {
    const selected = tagSelections[sub.subId] || [];

    return (
      <div key={sub.subId} style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Text style={{ fontFamily: 'var(--font-serif)', color: 'var(--text-primary)', fontSize: 14 }}>
            {sub.subName}
          </Text>
          <Text style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
            {sub.isMutuallyExclusive ? '(单选)' : sub.maxSelect ? `(最多选 ${sub.maxSelect} 个)` : '(多选)'}
          </Text>
        </div>

        {sub.isMutuallyExclusive ? (
          // 单选 Radio
          <Radio.Group 
            value={selected[0]} 
            onChange={e => toggleTag(sub.subId, e.target.value, true, null)}
          >
            <Space size={[12, 12]} wrap>
              {sub.tags.map(tag => (
                <Radio key={tag.name} value={tag.name}>
                  <span style={{ color: selected.includes(tag.name) ? 'var(--accent-moss)' : 'var(--text-primary)' }}>
                    {tag.name} <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{tag.percentage}%</span>
                  </span>
                </Radio>
              ))}
            </Space>
          </Radio.Group>
        ) : (
          // 多选 Checkbox
          <Space size={[12, 12]} wrap>
            {sub.tags.map(tag => {
              const isChecked = selected.includes(tag.name);
              const isDisabled = !isChecked && sub.maxSelect !== null && selected.length >= sub.maxSelect;
              
              return (
                <Checkbox
                  key={tag.name}
                  checked={isChecked}
                  disabled={isDisabled}
                  onChange={() => toggleTag(sub.subId, tag.name, false, sub.maxSelect)}
                >
                  <span style={{ color: isChecked ? 'var(--accent-moss)' : isDisabled ? 'rgba(0,0,0,0.25)' : 'var(--text-primary)' }}>
                    {tag.name} <span style={{ color: 'var(--text-secondary)', fontSize: 12 }}>{tag.percentage}%</span>
                  </span>
                </Checkbox>
              );
            })}
          </Space>
        )}
      </div>
    );
  };

  return (
    <div style={{ paddingBottom: 160 }}> {/* 为底部固定栏留出空间 */}
      {/* 顶部导航 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <Button
          type="text"
          icon={<ArrowLeft size={16} />}
          onClick={() => navigate(`/report/${taskId}`)}
          style={{ color: 'var(--text-secondary)', padding: '4px 8px' }}
        >
          返回报告
        </Button>
      </div>

      {/* 页面标题 */}
      <div style={{ marginBottom: 32, borderBottom: '1px solid rgba(47, 54, 48, 0.1)', paddingBottom: 24 }}>
        <Title level={1} style={{ fontFamily: 'var(--font-serif)', margin: 0, color: 'var(--accent-moss)', fontSize: 42, fontWeight: 400 }}>标签筛选</Title>
        <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontFamily: 'var(--font-serif)', fontSize: 16 }}>Tag Selection & Refinement</Text>
      </div>

      {/* 提示文案 */}
      <div style={{ 
        padding: '16px 24px', 
        background: 'var(--bg-ceramic)', 
        borderLeft: '3px solid var(--accent-amber)',
        borderRadius: 2,
        marginBottom: 32,
        display: 'flex',
        gap: 12,
        alignItems: 'flex-start'
      }}>
        <AlertCircle size={18} color="var(--accent-amber)" style={{ marginTop: 2 }} />
        <Paragraph style={{ margin: 0, color: 'var(--text-primary)', fontSize: 14, lineHeight: 1.6 }}>
          系统已根据受众分析结果预选了每个维度的核心标签。您可以根据实际调香需求对标签进行删减或替换。<br/>
          <Text style={{ color: 'var(--text-secondary)' }}>选中的标签将直接作为下一步大模型生成香调配方的 Context。</Text>
        </Paragraph>
      </div>

      {/* 标签选择区 */}
      <Row gutter={[32, 32]}>
        {tagDimensions.map(dim => (
          <Col span={12} key={dim.dimensionId}>
            <Card 
              bodyStyle={{ padding: '28px 32px' }}
              style={{ height: '100%', display: 'flex', flexDirection: 'column' }}
            >
              <div style={{ borderBottom: '1px dashed var(--border-line)', paddingBottom: 16, marginBottom: 24 }}>
                <Title level={4} style={{ fontFamily: 'var(--font-serif)', color: 'var(--accent-moss)', margin: 0, fontWeight: 400 }}>
                  {dim.dimensionName}
                </Title>
              </div>
              <div style={{ flex: 1 }}>
                {dim.subDimensions.map(sub => renderSubDimension(sub))}
              </div>
            </Card>
          </Col>
        ))}
      </Row>

      {/* 底部悬浮预览栏 */}
      <div style={{
        position: 'fixed',
        bottom: 0,
        left: 240, // 假设侧边栏宽度，因为实际是在 Layout 内部
        right: 0,
        background: 'var(--bg-paper)',
        borderTop: '1px solid var(--border-line)',
        padding: '24px 48px',
        boxShadow: '0 -4px 12px rgba(0,0,0,0.02)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        zIndex: 10,
        transform: 'translateX(0)', // 这里在实际应用中如果侧边栏自适应可能需要微调，现在假设占据了主内容区
        width: 'calc(100% - 240px)' // 因为我们是左侧导航栏布局
      }}>
        <div style={{ flex: 1, marginRight: 32 }}>
          <Text style={{ display: 'block', fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>已选标签预览</Text>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxHeight: 80, overflowY: 'auto' }}>
            {allSelectedTagsList.map(tag => (
              <span key={tag} style={{ 
                padding: '4px 12px', 
                background: 'var(--bg-ceramic)', 
                border: '1px solid var(--border-line)',
                borderRadius: 2,
                fontSize: 13,
                color: 'var(--accent-moss)'
              }}>
                {tag}
              </span>
            ))}
            {allSelectedTagsList.length === 0 && (
              <Text style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>尚未选择任何标签...</Text>
            )}
          </div>
        </div>
        
        <Button
          type="primary"
          size="large"
          icon={<Sparkles size={16} />}
          onClick={handleGenerate}
          style={{ 
            borderRadius: 2, 
            background: 'var(--accent-amber)', 
            height: 48, 
            paddingInline: 32,
            fontSize: 16,
            flexShrink: 0
          }}
        >
          生成香调推荐方案
        </Button>
      </div>
    </div>
  );
};
