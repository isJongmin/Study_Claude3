import { expect, test, type Page } from '@playwright/test'

async function login(page: Page, id: string, pw: string, otp?: string) {
  await page.goto('/')
  await page.getByTestId('login-id').fill(id)
  await page.getByTestId('login-pw').fill(pw)
  await page.getByTestId('login-submit').click()
  if (otp) {
    await page.getByTestId('otp-code').fill(otp)
    await page.getByTestId('otp-submit').click()
  }
  await expect(page.getByTestId('shell')).toBeVisible()
}

test('로그인 실패 메시지, OTP 오류 후 재입력', async ({ page }) => {
  await page.goto('/')
  await page.getByTestId('login-id').fill('park.pm')
  await page.getByTestId('login-pw').fill('wrong-pass')
  await page.getByTestId('login-submit').click()
  await expect(page.getByTestId('auth-err')).toContainText('올바르지 않습니다')
  await page.getByTestId('login-id').fill('admin')
  await page.getByTestId('login-pw').fill('admin1234')
  await page.getByTestId('login-submit').click()
  await page.getByTestId('otp-code').fill('000000')
  await page.getByTestId('otp-submit').click()
  await expect(page.getByTestId('auth-err')).toContainText('인증 코드')
  await page.getByTestId('otp-code').fill('123456')
  await page.getByTestId('otp-submit').click()
  await expect(page.getByTestId('shell')).toBeVisible()
})

test('대시보드: KPI·호선 5척·날씨', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await expect(page.getByTestId('dashboard')).toBeVisible()
  await expect(page.getByTestId('kpi-delay')).toContainText('1')
  await expect(page.locator('[data-test^=ship-]')).toHaveCount(5)
  await expect(page.getByTestId('weather')).toContainText('°C')
  await expect(page.getByTestId('card-impact')).toBeVisible()
})

test('조회 전용 계정은 쓰기 버튼이 없고 메뉴도 제한된다', async ({ page }) => {
  await login(page, 'choi.qa', 'qa1234')
  await page.getByTestId('menu-hull-list').click()
  await expect(page.getByTestId('hull-table')).toBeVisible()
  await expect(page.getByTestId('hull-new')).toHaveCount(0)
  await expect(page.getByTestId('menu-user-mgmt')).toHaveCount(0)
})

test('호선 등록 → 인도일 검증 → 삭제', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-hull-list').click()
  await page.getByTestId('hull-new').click()
  await page.getByTestId('h-no').fill('9300')
  await page.getByTestId('h-nm').fill('E2E Ship')
  await page.getByTestId('h-contract').fill('2026-05-01')
  await page.getByTestId('h-delivery').fill('2026-04-01')
  await page.getByTestId('h-save').click()
  await expect(page.getByTestId('toast').last()).toContainText('인도 예정일이 계약일보다 빠릅니다')
  await page.getByTestId('h-delivery').fill('2027-04-01')
  await page.getByTestId('h-save').click()
  await expect(page.getByTestId('toast').last()).toContainText('등록되었습니다')
  await page.getByTestId('htab-ms').click()
  await expect(page.locator('[data-test=modal] tbody tr')).toHaveCount(5)
  await page.getByTestId('htab-info').click()
  await page.getByTestId('h-del').click()
  await page.getByTestId('confirm-yes').click()
  await expect(page.getByTestId('toast').last()).toContainText('삭제되었습니다')
  await expect(page.getByTestId('hull-row-9300')).toHaveCount(0)
})

test('도면 상세: PDF 뷰어와 회원가입 중복 오류', async ({ page }) => {
  await login(page, 'lee.dwg', 'dwg1234', '123456')
  await page.getByTestId('menu-dwg-list').click()
  await page.getByTestId('dwg-row-8001-HULL-101').click()
  await expect(page.getByTestId('pdf-frame')).toBeVisible()
  await expect(page.getByTestId('rev-actions')).toContainText('신규')
  await page.getByTestId('modal-close').click()
  await page.getByTestId('acct-btn').click()
  await page.getByTestId('logout').click()
  await page.getByTestId('go-signup').click()
  for (const [k, v] of [['ln', '김'], ['fn', '신규'], ['bd', '1990-01-01'], ['ph', '010-2222-0002'], ['em', 'new@swp.co.kr'], ['id', 'new.user1'], ['pw', 'abcd1234'], ['pw2', 'abcd1234']])
    await page.getByTestId('su-' + k).fill(v)
  await page.getByTestId('su-submit').click()
  await expect(page.getByTestId('auth-err')).toContainText('이미 등록된 전화번호')
})

test('도면 게이트: 첫 실적이 409 메시지로 막힌다', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-progress').click()
  await page.getByTestId('pg-hull').selectOption('8003')
  await page.getByTestId('pg-done').check()
  const rows = page.locator('[data-test^=pg-row-]')
  await expect(rows.first()).toBeVisible()
  await rows.first().click()
  await page.getByTestId('pg-rate').fill('0')
  await page.getByTestId('pg-save').click()
  await expect(page.getByTestId('toast').last()).toContainText('배포되지 않아 착수할 수 없습니다')
})

const WIDTHS = [1440, 768, 390]
const SCREENS = ['menu-dashboard', 'menu-hull-list', 'menu-plan-gantt', 'menu-progress', 'menu-dwg-list', 'menu-dwg-approval', 'menu-user-mgmt']
for (const w of WIDTHS) {
  test(`반응형 ${w}px: 가로 넘침·콘솔 오류 없음`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', (e) => errors.push(e.message))
    page.on('console', (m) => { if (m.type() === 'error' && m.location().url.includes('127.0.0.1')) errors.push(m.text()) })
    await page.setViewportSize({ width: w, height: 900 })
    await login(page, 'admin', 'admin1234', '123456')
    for (const s of SCREENS) {
      if (w < 1024) await page.getByTestId('menu-btn').click()
      await page.getByTestId(s).click()
      await page.waitForTimeout(250)
      const over = await page.evaluate(() => {
        const bad: string[] = []
        const vw = document.documentElement.clientWidth
        if (document.documentElement.scrollWidth > vw) bad.push('page')
        const work = document.querySelector('.work') as HTMLElement
        if (work && work.scrollWidth > work.clientWidth + 1) bad.push('work')
        document.querySelectorAll('button, .btn').forEach((b) => { if (b.closest('.tabs')) return; const r = b.getBoundingClientRect(); if (r.width && r.right > vw + 1) bad.push('btn:' + (b.textContent || '').trim()) })
        return bad
      })
      expect(over, `${s} @${w}`).toEqual([])
    }
    // 팝업이 열리면 뒤 페이지는 고정된다
    await page.getByTestId(w < 1024 ? 'menu-btn' : 'menu-hull-list').click()
    if (w < 1024) await page.getByTestId('menu-hull-list').click()
    await page.getByTestId('hull-row-8001').click()
    await expect(page.getByTestId('hull-modal')).toBeVisible()
    expect(await page.evaluate(() => (document.querySelector('.work') as HTMLElement).classList.contains('locked'))).toBe(true)
    expect(errors).toEqual([])
  })
}

const BARS = '[data-test^=bar-]:not([data-test^=bar-l-]):not([data-test^=bar-r-])'
const parse = (t: string) => { const m = t.match(/(\d{4}-\d\d-\d\d)~(\d{4}-\d\d-\d\d)/)!; return { s: m[1], e: m[2] } }

test('간트: 오른쪽 끝 드래그 → 패널 값 즉시 변경 → 닫기로 원복 → 다시 끌어 저장', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-plan-gantt').click()
  await expect(page.getByTestId('gantt')).toBeVisible()
  const handle = page.locator('[data-test^=bar-r-]').first()
  const bar = handle.locator('xpath=..')
  const orig = parse((await bar.getAttribute('title'))!)
  const wBefore = (await bar.boundingBox())!.width
  const drag = async () => {
    await handle.scrollIntoViewIfNeeded()
    const box = (await handle.boundingBox())!
    const x = box.x + box.width / 2, y = box.y + box.height / 2
    await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 18, y, { steps: 4 })
    await expect(page.getByTestId('drag-tip')).toContainText('~')
    await page.mouse.up()
  }
  await drag()
  // 놓자마자 패널 값이 바뀌고 차트도 미리 보여 주되 저장은 안 된 상태
  await expect(page.getByTestId('plan-panel')).toBeVisible()
  await expect(page.getByTestId('p-end')).not.toHaveValue(orig.e)
  await expect(page.getByTestId('p-start')).toHaveValue(orig.s)
  expect((await bar.boundingBox())!.width).toBeGreaterThan(wBefore)
  // 닫기 → 원래대로
  await page.getByTestId('plan-panel').getByRole('button', { name: '닫기' }).click()
  await expect(page.getByTestId('plan-panel')).toHaveCount(0)
  expect(Math.round((await bar.boundingBox())!.width)).toBe(Math.round(wBefore))
  expect(parse((await bar.getAttribute('title'))!)).toEqual(orig)
  // 다시 끌어 저장
  await drag()
  await page.getByTestId('p-save').click()
  await expect(page.getByTestId('toast').last()).toContainText('저장')
  await expect.poll(async () => parse((await bar.getAttribute('title'))!).e).not.toBe(orig.e)
})

test('간트: 막대 몸통 드래그는 기간을 유지한 채 패널 값만 바꾼다', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-plan-gantt').click()
  const bar = page.locator(BARS).first()
  const orig = parse((await bar.getAttribute('title'))!)
  const box = (await bar.boundingBox())!
  const x = box.x + box.width / 2, y = box.y + box.height / 2
  await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + 18, y, { steps: 4 }); await page.mouse.up()
  const s = await page.getByTestId('p-start').inputValue(), e = await page.getByTestId('p-end').inputValue()
  expect(s).not.toBe(orig.s)
  expect((Date.parse(e) - Date.parse(s)) / 864e5).toBe((Date.parse(orig.e) - Date.parse(orig.s)) / 864e5)
  expect(parse((await bar.getAttribute('title'))!)).toEqual(orig) // 저장 전이라 서버 값은 그대로
})

test('도면 상세: 신규 Rev 작성 때 PDF를 골라 함께 올린다(이력 행에는 파일 버튼 없음)', async ({ page }) => {
  await login(page, 'lee.dwg', 'dwg1234', '123456')
  await page.getByTestId('menu-dwg-list').click()
  await page.getByTestId('dwg-row-8001-HULL-101').click()
  await expect(page.locator('[data-test^=rev-file-]')).toHaveCount(0)
  await page.getByTestId('nr-desc').fill('파일 포함 개정')
  const pdf = Buffer.from(['%PDF-1.4', '1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj', '2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj', '3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj', 'trailer<</Root 1 0 R>>', '%%EOF'].join('\n'))
  await page.getByTestId('nr-pdf').setInputFiles({ name: 'rev1-new.pdf', mimeType: 'application/pdf', buffer: pdf })
  await expect(page.locator('.fdrop .picked')).toContainText('rev1-new.pdf')
  await page.getByTestId('nr-save').click()
  await expect(page.getByTestId('toast').last()).toContainText('PDF를 첨부')
  await expect(page.locator('.rfn', { hasText: 'rev1-new.pdf' })).toBeVisible()
  // 끌어 놓기: 드롭존에 DataTransfer로 파일 전달(새 Rev는 이미 작성중이라 신규 등록 화면에서 확인)
})

test('신규 도면 등록: PDF 드래그앤드롭 선택', async ({ page }) => {
  await login(page, 'lee.dwg', 'dwg1234', '123456')
  await page.getByTestId('menu-dwg-list').click()
  await page.getByTestId('dwg-new').click()
  const dt = await page.evaluateHandle(() => { const d = new DataTransfer(); d.items.add(new File(['%PDF-1.4'], 'dropped.pdf', { type: 'application/pdf' })); return d })
  await page.locator('.fdrop .drop').dispatchEvent('drop', { dataTransfer: dt })
  await expect(page.locator('.fdrop .picked')).toContainText('dropped.pdf')
  await page.getByRole('button', { name: '선택 취소' }).click()
  await expect(page.locator('.fdrop .picked')).toHaveCount(0)
})

test('간트: 연속으로 여러 번 끌어도 이전 변경이 유지되고, 다른 공정을 눌러도 보관된다', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-plan-gantt').click()
  const handle = page.locator('[data-test^=bar-r-]').first()
  const bar = handle.locator('xpath=..')
  const orig = parse((await bar.getAttribute('title'))!)
  const drag = async (dx: number) => {
    await handle.scrollIntoViewIfNeeded()
    const box = (await handle.boundingBox())!
    const x = box.x + box.width / 2, y = box.y + box.height / 2
    await page.mouse.move(x, y); await page.mouse.down(); await page.mouse.move(x + dx, y, { steps: 4 }); await page.mouse.up()
  }
  const days = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 864e5)
  await drag(18)
  const e1 = await page.getByTestId('p-end').inputValue()
  expect(days(orig.e, e1)).toBe(3)
  await drag(18) // 두 번째 드래그가 처음 값으로 되돌아가지 않고 이어서 +3일
  const e2 = await page.getByTestId('p-end').inputValue()
  expect(days(orig.e, e2)).toBe(6)
  await expect(page.getByTestId('draft-bar')).toContainText('1건')
  // 다른 공정을 눌러도 첫 공정의 변경은 보관된다
  await page.locator('[data-test^=plan-row-]').nth(1).click()
  await expect(page.getByTestId('draft-bar')).toContainText('1건')
  await page.locator('[data-test^=plan-row-]').first().click()
  await expect(page.getByTestId('p-end')).toHaveValue(e2)
  await page.getByTestId('draft-reset').click()
  await expect(page.getByTestId('draft-bar')).toHaveCount(0)
})

test('탭: 다른 탭 닫기, 사이드바 접기 핸들(좁은 화면에서는 숨김)', async ({ page }) => {
  await login(page, 'park.pm', 'pm1234')
  await page.getByTestId('menu-hull-list').click()
  await page.getByTestId('menu-plan-gantt').click()
  await expect(page.locator('.tab')).toHaveCount(3)
  await page.getByTestId('close-others').click()
  await expect(page.locator('.tab')).toHaveCount(1)
  await expect(page.getByTestId('tab-plans')).toHaveClass(/act/)
  await expect(page.getByTestId('close-others')).toHaveCount(0)
  await expect(page.getByTestId('collapse')).toBeVisible()
  await page.getByTestId('collapse').click()
  await expect(page.locator('.body.col')).toHaveCount(1)
  await page.setViewportSize({ width: 900, height: 700 })
  await expect(page.getByTestId('collapse')).toBeHidden()
})
