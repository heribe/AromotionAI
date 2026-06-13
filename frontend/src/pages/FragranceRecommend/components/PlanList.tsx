import React from 'react';
import { useFragranceStore } from '../../../stores/useFragranceStore';
import { PlanCard } from './PlanCard';

export const PlanList: React.FC = () => {
  const { plans } = useFragranceStore();

  if (!plans || plans.length === 0) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-secondary)' }}>
        暂无香调方案...
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 700, margin: '0 auto' }}>
      {plans.map((plan, index) => (
        <PlanCard key={plan.planId} plan={plan} index={index} />
      ))}
    </div>
  );
};
