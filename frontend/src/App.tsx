import { ConfigProvider } from 'antd';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#C18841',
          colorSuccess: '#2A332C',
          colorWarning: '#B8860B',
          colorError: '#A0522D',
          colorBgContainer: '#FDFDFB',
          colorBgLayout: 'transparent',
          borderRadius: 2,
          colorText: '#2A332C',
          colorBorder: '#CDD1CA',
          fontFamily: "'Outfit', -apple-system, sans-serif",
        },
      }}
    >
      <RouterProvider router={router} />
    </ConfigProvider>
  )
}

export default App
