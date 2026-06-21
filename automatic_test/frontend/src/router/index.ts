import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../pages/LoginPage.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/cases',
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('../pages/CasesPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/cases/new',
    name: 'CaseCreate',
    component: () => import('../pages/CaseCreatePage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/cases/:id',
    name: 'CaseDetail',
    component: () => import('../pages/CaseDetailPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/checklists',
    name: 'Checklists',
    component: () => import('../pages/ChecklistsPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/checklists/:id',
    name: 'ChecklistDetail',
    component: () => import('../pages/ChecklistDetailPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/checklists/:id/cases',
    name: 'ChecklistCases',
    component: () => import('../pages/ChecklistCasesPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/executions/:id',
    name: 'Execution',
    component: () => import('../pages/ExecutionPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/results/:id',
    name: 'Result',
    component: () => import('../pages/ResultPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/db-connections',
    name: 'DBConnections',
    component: () => import('../pages/DBConnectionPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('../pages/AdminPage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  const userRole = localStorage.getItem('user_role')

  if (to.meta.requiresAuth !== false && !token) {
    return '/login'
  }

  if (to.meta.requiresAdmin && userRole !== 'admin') {
    return '/'
  }

  if (to.path === '/login' && token) {
    return '/'
  }
})

export default router
