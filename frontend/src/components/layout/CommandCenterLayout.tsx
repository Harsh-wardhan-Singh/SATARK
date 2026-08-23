import React from 'react';
import './CommandCenterLayout.css';

interface CommandCenterLayoutProps {
  header: React.ReactNode;
  leftSidebar: React.ReactNode;
  rightSidebar: React.ReactNode;
  main: React.ReactNode;
  footer: React.ReactNode;
}

export const CommandCenterLayout: React.FC<CommandCenterLayoutProps> = ({
  header,
  leftSidebar,
  rightSidebar,
  main,
  footer,
}) => {
  return (
    <div className="layout-container">
      <header className="layout-header">{header}</header>
      <div className="layout-body">
        {leftSidebar}
        <main className="layout-main">{main}</main>
        {rightSidebar}
      </div>
      <footer className="layout-footer">{footer}</footer>
    </div>
  );
};
