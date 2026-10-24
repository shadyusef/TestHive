import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-048] Valid OTP 123456 activates the account and gives 50 points @smoke @regression', async ({ page, data }) => {
  await toOtpPage(page, person(data));
  await new OtpPage(page).enter('123456');
  await expect(page.getByTestId('balance')).toHaveText('Your balance: 50 points');
});
