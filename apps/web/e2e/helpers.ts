import { execFileSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { expect, type Page } from '@playwright/test'

export const E2E_EMAIL = process.env.PETROSENSE_E2E_EMAIL ?? 'admin@petrosense.local'
export const E2E_PASSWORD = process.env.PETROSENSE_E2E_PASSWORD ?? ''
export const ALLOW_WRITES = process.env.PETROSENSE_E2E_ALLOW_WRITES === '1'

const repositoryRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../..',
)
const defaultPython =
  process.platform === 'win32'
    ? 'apps/api/.venv/Scripts/python.exe'
    : 'apps/api/.venv/bin/python'
const edgePython = process.env.PETROSENSE_EDGE_PYTHON ?? defaultPython

export async function signIn(page: Page, identifier = E2E_EMAIL): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identifier)
  await page.getByLabel('Password', { exact: true }).fill(E2E_PASSWORD)
  await page.getByRole('button', { name: /sign in to workspace/i }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

export function runSimulator(args: string[]): void {
  execFileSync(
    path.resolve(repositoryRoot, edgePython),
    ['-m', 'petrosense_edge.cli', ...args],
    {
      cwd: repositoryRoot,
      env: { ...process.env, PETROSENSE_EDGE_PASSWORD: E2E_PASSWORD },
      encoding: 'utf8',
      timeout: 60_000,
    },
  )
}
