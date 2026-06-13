import { ConfigProvider } from 'antd';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';

function App() {
  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#8B6A47',      // 琥珀色 (Amber)
          colorSuccess: '#4A5D4E',      // 深苔藓绿 (Moss Green)
          colorWarning: '#B8860B',      // 暖金
          colorError: '#A0522D',        // 赤褐
          colorBgContainer: '#F9F9F9',  // 浅陶瓷灰/试香纸背景
          borderRadius: 4,              // 极小圆角，偏硬朗纸质感
          colorText: '#2F3330',         // 炭灰文字
          colorBorder: '#E0E0E0',       // 极细的浅色分割线
          fontFamily: "'Inter', 'Georgia', serif, -apple-system, sans-serif",
        },
      }}
    >
      <RouterProvider router={router} />
    </ConfigProvider>
  )
}

export default App
