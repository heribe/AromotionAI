import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { Dashboard } from '../pages/Dashboard';
import { FragranceRecommend } from '../pages/FragranceRecommend';
import { ProfileReport } from '../pages/ProfileReport';
import { TagSelection } from '../pages/TagSelection';

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
        path: 'report/:taskId',
        element: <ProfileReport />,
      },
      {
        path: 'tags/:taskId',
        element: <TagSelection />,
      },
      {
        path: 'recommend',
        element: <FragranceRecommend />,
      },
    ],
  },
]);
