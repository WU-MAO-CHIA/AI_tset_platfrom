import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/cases',
  },
  {
    path: '/cases',
    name: 'Cases',
    component: () => import('../pages/CasesPage.vue'),
  },
  {
    path: '/cases/new',
    name: 'CaseCreate',
    component: () => import('../pages/CaseCreatePage.vue'),
  },
  {
    path: '/cases/:id',
    name: 'CaseDetail',
    component: () => import('../pages/CaseDetailPage.vue'),
  },
  {
    path: '/checklists',
    name: 'Checklists',
    component: () => import('../pages/ChecklistsPage.vue'),
  },
  {
    path: '/checklists/:id',
    name: 'ChecklistDetail',
    component: () => import('../pages/ChecklistDetailPage.vue'),
  },
  {
    path: '/checklists/:id/cases',
    name: 'ChecklistCases',
    component: () => import('../pages/ChecklistCasesPage.vue'),
  },
  {
    path: '/executions/:id',
    name: 'Execution',
    component: () => import('../pages/ExecutionPage.vue'),
  },
  {
    path: '/results/:id',
    name: 'Result',
    component: () => import('../pages/ResultPage.vue'),
  },
  {
    path: '/db-connections',
    name: 'DBConnections',
    component: () => import('../pages/DBConnectionPage.vue'),
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
