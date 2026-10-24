import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-001] Valid sign-up opens the OTP page without a message @smoke @regression', async ({ page, data }) => {
  const form = new SignupPage(page);
  await form.open();
  await expect(page.getByRole('textbox', { name: /email/i })).toHaveCount(0);
  await form.signUp(person(data));
  await expect(new OtpPage(page).heading).toHaveText('Verify your mobile number');
  await expect(page).toHaveURL(/\/otp\?id=/);
});
