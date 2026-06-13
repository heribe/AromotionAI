import React from 'react';
import { Layout, Menu, Typography } from 'antd';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { FlaskConical, LayoutDashboard } from 'lucide-react';

const { Header, Content } = Layout;
const { Title } = Typography;

export const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/dashboard',
      icon: <LayoutDashboard size={18} />,
      label: '项目工作台',
    },
    {
      key: '/recommend',
      icon: <FlaskConical size={18} />,
      label: '香调调配室',
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Header style={{ 
        display: 'flex', 
        alignItems: 'center', 
        padding: '0 40px',
        background: 'var(--bg-card)',
        borderBottom: '1px solid var(--border-line)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', marginRight: '40px' }}>
          <FlaskConical color="var(--accent-moss)" size={24} style={{ marginRight: 12 }} />
          <Title level={4} style={{ margin: 0, fontFamily: 'var(--font-serif)', color: 'var(--text-primary)' }}>
            AromotionAI
          </Title>
        </div>
        
        <Menu
          mode="horizontal"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ flex: 1, borderBottom: 'none', background: 'transparent' }}
        />
      </Header>
      
      <Content style={{ padding: '40px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
        <Outlet />
      </Content>
    </Layout>
  );
};
