// 화면 스크린샷을 docs/screens/에 저장한다(폰·클라우드에서 AI가 화면을 보고 검토하도록).
// 평소 verify에서는 건너뛴다. 실행: npm --prefix frontend run build && cd frontend && SHOTS=1 npx playwright test shots
import { expect, test, type Page } from '@playwright/test'

const OUT = '../docs/screens/'
test.skip(!process.env.SHOTS, 'SHOTS=1 일 때만 실행')

async function login(page: Page, id: string, pw: string, otp?: string) {
  await page.goto('/')
  await page.getByTestId('login-id').fill(id)
  await page.getByTestId('login-pw').fill(pw)
  await page.getByTestId('login-submit').click()
  if (otp) { await page.getByTestId('otp-code').fill(otp); await page.getByTestId('otp-submit').click() }
  await expect(page.getByTestId('shell')).toBeVisible()
}
const snap = async (page: Page, name: string, full = false) => { await page.waitForTimeout(700); await page.screenshot({ path: `${OUT}${name}.png`, fullPage: full }) }
const go = async (page: Page, menu: string) => { await page.getByTestId(`menu-${menu}`).click(); await page.waitForTimeout(300) }

test('화면 스크린샷(데스크톱 1440×900, 모바일 390)', async ({ page }) => {
  test.setTimeout(120000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await login(page, 'park.pm', 'pm1234')
  await snap(page, '01-dashboard')
  await page.locator('.work').evaluate((e) => { e.scrollTop = e.scrollHeight }); await snap(page, '01-dashboard-bottom')
  await go(page, 'hull-list'); await snap(page, '02-hull-list')
  await page.locator('[data-test^=hull-row-]').first().click()
  await snap(page, '03-hull-modal-info')
  await page.getByTestId('htab-sum').click(); await snap(page, '03-hull-modal-sum')
  await page.keyboard.press('Escape')
  await go(page, 'plan-gantt'); await snap(page, '04-plan-gantt')
  await page.locator('[data-test^=plan-row-]').nth(2).click(); await snap(page, '04-plan-gantt-panel-open')
  await go(page, 'progress'); await page.locator('[data-test^=pg-row-]').first().click(); await snap(page, '05-progress')
  await go(page, 'dwg-list'); await snap(page, '06-dwg-list')
  await page.locator('[data-test^=dwg-row-]').first().click(); await page.getByTestId('pdf-card').waitFor(); await snap(page, '07-dwg-modal')
  await page.keyboard.press('Escape')
  await page.setViewportSize({ width: 390, height: 844 })
  await snap(page, '08-mobile-dwg-list')
  await page.getByTestId('menu-btn').click(); await snap(page, '08-mobile-menu')
  await page.getByTestId('menu-dashboard').click(); await snap(page, '08-mobile-dashboard', true)
  // 다른 권한: 결재함(lee.dwg), 회원관리(admin)
  await page.getByTestId('menu-btn').click()
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.getByTestId('acct-btn').click(); await page.getByTestId('logout').click()
  await login(page, 'lee.dwg', 'dwg1234', '123456'); await go(page, 'dwg-approval'); await snap(page, '09-approval')
  await page.getByTestId('acct-btn').click(); await page.getByTestId('logout').click()
  await login(page, 'admin', 'admin1234', '123456'); await go(page, 'user-mgmt'); await snap(page, '10-users')
})
