// Reusable steps of SIGNUP: a valid person with a unique mobile number, and reaching the OTP page.
import { Page } from '@playwright/test';
import { SignupPage, Person } from './SignupPage';

export const person = (data: { digits: (n: number) => string }, extra: Partial<Person> = {}): Person =>
  ({ name: 'Sara Test', mobile: '05' + data.digits(8), password: 'Pass1234', birthDate: '1990-01-15', language: 'en', terms: true, ...extra });

export async function toOtpPage(page: Page, p: Person) {
  const form = new SignupPage(page);
  await form.open(); await form.signUp(p);
  await page.waitForURL(/\/otp\?id=/);
}
