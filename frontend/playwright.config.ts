import { defineConfig } from '@playwright/test'

import { resolve } from 'node:path'

const root = resolve(process.cwd(), '..') // 항상 frontend 폴더에서 실행
const py = resolve(root, process.platform === 'win32' ? 'backend/.venv/Scripts/python.exe' : 'backend/.venv/bin/python')
const server = resolve(root, 'scripts/e2e_server.py')

export default defineConfig({
  testDir: './e2e',
  timeout: 40000,
  expect: { timeout: 10000 },
  workers: 1,
  fullyParallel: false,
  use: { baseURL: 'http://127.0.0.1:8100', headless: true, testIdAttribute: 'data-test' },
  // 빌드된 화면(dist)을 임시 DB의 FastAPI가 제공한다. /api/health(인증 불필요)로 서버 준비를 확인한다.
  webServer: { command: `"${py}" "${server}" 8100`, url: 'http://127.0.0.1:8100/api/health', reuseExistingServer: false, timeout: 60000 },
})
