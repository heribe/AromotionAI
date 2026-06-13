import React, { useEffect, useState } from 'react';
import { Typography } from 'antd';
import './ExtractionAnimation.css';

const { Text } = Typography;

const LOGS = [
  { text: '> 正在解析用户潜意识需求...', detail: 'EXTRACTING ICEBERG MODEL', delay: 0 },
  { text: '> 正在匹配香调维度库...', detail: 'MAPPING FRAGRANCE FAMILIES', delay: 3000 },
  { text: '> 正在重组配方分子...', detail: 'COMPOSING FORMULAS', delay: 6000 },
  { text: '> 提纯完毕，配方已封存', detail: 'EXTRACTION COMPLETE', delay: 9000 },
];

interface Props {
  isFadingOut?: boolean;
}

export const ExtractionAnimation: React.FC<Props> = ({ isFadingOut = false }) => {
  const [currentLogIndex, setCurrentLogIndex] = useState(0);

  useEffect(() => {
    const timers = LOGS.map((log, index) => {
      return setTimeout(() => {
        setCurrentLogIndex(index);
      }, log.delay);
    });

    return () => {
      timers.forEach(clearTimeout);
    };
  }, []);

  return (
    <div className={`extraction-container ${isFadingOut ? 'fade-out' : ''}`}>
      <div className="decor-line"></div>

      <div className="animation-container">
        {/* 滴管 */}
        <div className="dropper"></div>
        {/* 滴落的精油 (退场时停止下落) */}
        {!isFadingOut && <div className="drop"></div>}
        
        {/* 底部的涟漪 */}
        <div className="surface"></div>
        {!isFadingOut && (
          <>
            <div className="ripple"></div>
            <div className="ripple ripple-2"></div>
          </>
        )}
      </div>

      {/* 打字机日志 */}
      <div className="terminal">
        <div className="log-line active">
          <span style={{ color: 'var(--text-secondary)' }}>{LOGS[currentLogIndex].text.split('用户潜意识需求')[0]}</span>
          {LOGS[currentLogIndex].text.includes('用户潜意识需求') && <span className="highlight">用户潜意识需求</span>}
          {LOGS[currentLogIndex].text.includes('香调维度库') && <span className="highlight">香调维度库</span>}
          {LOGS[currentLogIndex].text.includes('配方分子') && <span className="highlight">配方分子</span>}
          <span style={{ color: 'var(--text-secondary)' }}>{LOGS[currentLogIndex].text.split('...')[1] ? '...' : ''}</span>
          <br />
          <span style={{ fontSize: 11, opacity: 0.6, color: 'var(--text-secondary)' }}>
            {LOGS[currentLogIndex].detail}
          </span>
        </div>
      </div>
    </div>
  );
};
