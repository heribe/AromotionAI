import { lazy } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';

// 路由级分包：每个页面单独 chunk，首屏只加载当前路由代码
const Dashboard = lazy(() => import('../pages/Dashboard').then(m => ({ default: m.Dashboard })));
const TaskProgress = lazy(() => import('../pages/TaskProgress').then(m => ({ default: m.TaskProgress })));
const ProfileReport = lazy(() => import('../pages/ProfileReport').then(m => ({ default: m.ProfileReport })));
const TagSelection = lazy(() => import('../pages/TagSelection').then(m => ({ default: m.TagSelection })));
const FragranceRecommend = lazy(() => import('../pages/FragranceRecommend').then(m => ({ default: m.FragranceRecommend })));

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'task/:taskId',
        element: <TaskProgress />,
      },
      {
        path: 'report/:taskId',
        element: <ProfileReport />,
      },
      {
        path: 'tags/:taskId',
        element: <TagSelection />,
      },
      {
        path: 'recommend/:id',
        element: <FragranceRecommend />,
      },
    ],
  },
]);
