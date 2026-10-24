import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-049] Full journey from form to 50 points @smoke @regression @e2e', async ({ page, data }) => {
  const form = new SignupPage(page), otp = new OtpPage(page);
  await form.open();
  await form.signUp(person(data));
  await expect(otp.heading).toHaveText('Verify your mobile number');
  await otp.enter('123456');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Welcome to Nakhla Rewards');
  await expect(page.getByTestId('balance')).toHaveText('Your balance: 50 points');
  await expect(page.getByTestId('error')).toHaveCount(0);
});
