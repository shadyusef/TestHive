// Reusable steps of SIGNUP: a valid person with a unique mobile number, reaching the OTP page through the form, or signing up through the API.
import { Page, APIRequestContext, expect } from '@playwright/test';
import { SignupPage, Person } from './SignupPage';

export const person = (data: { digits: (n: number) => string }, extra: Partial<Person> = {}): Person =>
  ({ name: 'Sara Test', mobile: '05' + data.digits(8), password: 'Pass1234', birthDate: '1990-01-15', language: 'en', terms: true, ...extra });

export async function toOtpPage(page: Page, p: Person) {
  const form = new SignupPage(page);
  await form.open(); await form.signUp(p);
  await page.waitForURL(/\/otp\?id=/);
}

export async function signUpByApi(api: APIRequestContext, p: Person): Promise<string> {
  const r = await api.post('/v1/signup', { data: { fullName: p.name, mobile: p.mobile, password: p.password, birthDate: p.birthDate, language: p.language || 'en' } });
  expect(r.status(), await r.text()).toBe(201);
  return (await r.json()).signupId;
}
