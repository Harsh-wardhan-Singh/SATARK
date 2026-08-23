import React from 'react';
import { useStore } from '../../store';

export const StatusBar: React.FC = () => {
  const { activeCalamity } = useStore();

  return (
    <div className="status-bar">
      <span>Active Calamity: {activeCalamity ? activeCalamity.type : 'None'}</span>
    </div>
  );
};
