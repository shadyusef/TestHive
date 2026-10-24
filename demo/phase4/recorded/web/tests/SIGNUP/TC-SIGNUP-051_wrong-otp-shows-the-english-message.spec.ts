import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-051] Wrong OTP shows the English message @smoke @regression', async ({ page, data }) => {
  await toOtpPage(page, person(data));
  const otp = new OtpPage(page);
  await otp.enter('654321');
  await expect(otp.error).toHaveText('The code is incorrect.');
  await expect(page).toHaveURL(/\/otp\?id=/);
});
