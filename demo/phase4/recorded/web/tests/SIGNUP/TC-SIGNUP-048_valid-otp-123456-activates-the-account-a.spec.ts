import { test, expect } from '../../fixtures/testhive';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, signUpByApi } from '../../pages/SIGNUP/steps';

// A journey across the API and the web: the sign-up (the precondition) goes through the API, the OTP is entered in the browser.
test('[TC-SIGNUP-048] Valid OTP 123456 activates the account and gives 50 points @smoke @regression @e2e', async ({ page, data, api }) => {
  const signupId = await signUpByApi(api, person(data));
  await page.goto('/otp?id=' + encodeURIComponent(signupId));
  await new OtpPage(page).enter('123456');
  await expect(page.getByTestId('balance')).toHaveText('Your balance: 50 points');
});
