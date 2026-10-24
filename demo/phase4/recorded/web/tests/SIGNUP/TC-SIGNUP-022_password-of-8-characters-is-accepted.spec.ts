import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-022] Password of 8 characters is accepted @smoke @regression', async ({ page, data }) => {
  const form = new SignupPage(page);
  await form.open();
  await form.signUp(person(data, { password: 'Pass1234' }));
  await expect(new OtpPage(page).heading).toHaveText('Verify your mobile number');
});
