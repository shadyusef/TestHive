import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-037] Already registered active number shows the duplicate message in English @smoke @regression', async ({ page, data }) => {
  const form = new SignupPage(page);
  await form.open();
  await form.signUp(person(data, { mobile: '0500000037' }));  // registered in the test environment (a fixed test account)
  await expect(form.error).toHaveText('This mobile number is already registered. Log in instead?');
  await expect(page).toHaveURL(/\/signup$/);
  // Not automated here: "no OTP is sent" needs the SMS log (backend check).
});
