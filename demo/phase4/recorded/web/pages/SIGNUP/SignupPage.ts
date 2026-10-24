// Sign-up form of SIGNUP (no assertions here: the specs check).
import { Page, Locator } from '@playwright/test';

export type Person = { name: string; mobile: string; password: string; birthDate: string; language?: 'en' | 'ar'; terms?: boolean };

export class SignupPage {
  readonly error: Locator;
  constructor(private page: Page) { this.error = page.getByTestId('error'); }
  async open() { await this.page.goto('/signup'); }
  async signUp(p: Person) {
    await this.page.getByTestId('full-name').fill(p.name);
    await this.page.getByTestId('mobile').fill(p.mobile);
    await this.page.getByTestId('password').fill(p.password);
    await this.page.getByTestId('birth-date').fill(p.birthDate);
    await this.page.getByTestId('language').selectOption(p.language ?? 'en');
    if (p.terms ?? true) await this.page.getByTestId('terms').check();
    await this.page.getByTestId('sign-up').click();
  }
}
