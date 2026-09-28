import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { NavComponent } from './shared/nav/nav.component';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    loadComponent: () => import('./pages/register/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: '',
    component: NavComponent,
    canActivate: [authGuard],
    children: [
      {
        path: '',
        pathMatch: 'full',
        loadComponent: () => import('./pages/home-redirect/home-redirect.component').then((m) => m.HomeRedirectComponent),
      },
      {
        path: 'dashboard',
        canActivate: [roleGuard('admin', 'gate_controller', 'ground_staff')],
        loadComponent: () => import('./pages/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'service-requests',
        loadComponent: () => import('./pages/service-requests/service-requests.component').then((m) => m.ServiceRequestsComponent),
      },
      {
        path: 'reports/gate-assignments',
        canActivate: [roleGuard('admin', 'gate_controller', 'ground_staff')],
        loadComponent: () => import('./pages/reports/gate-report/gate-report.component').then((m) => m.GateReportComponent),
      },
      {
        path: 'reports/analytics',
        canActivate: [roleGuard('admin', 'gate_controller', 'ground_staff')],
        loadComponent: () => import('./pages/reports/analytics/analytics.component').then((m) => m.AnalyticsComponent),
      },
      {
        path: 'admin/users',
        canActivate: [roleGuard('admin')],
        loadComponent: () => import('./pages/admin-users/admin-users.component').then((m) => m.AdminUsersComponent),
      },
      {
        path: 'forbidden',
        loadComponent: () => import('./pages/forbidden/forbidden.component').then((m) => m.ForbiddenComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'login' },
];
