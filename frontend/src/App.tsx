import { ConfigProvider, theme } from 'antd';
import { TestComponent } from '@/components/TestComponent';

function App() {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#B76E79',
          colorSuccess: '#7B8B6F',
          colorWarning: '#C9A96E',
          colorError: '#F67280',
          colorBgContainer: '#1a1a2e',
          borderRadius: 12,
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        },
      }}
    >
      <div style={{ padding: '50px', textAlign: 'center' }}>
        <h1>AromotionAI Frontend initialized!</h1>
        <TestComponent />
      </div>
    </ConfigProvider>
  )
}

export default App
