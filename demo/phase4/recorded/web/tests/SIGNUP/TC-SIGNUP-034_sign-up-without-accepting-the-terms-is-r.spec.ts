import { test, expect } from '../../fixtures/testhive';
import { SignupPage } from '../../pages/SIGNUP/SignupPage';
import { OtpPage } from '../../pages/SIGNUP/OtpPage';
import { person, toOtpPage } from '../../pages/SIGNUP/steps';

test('[TC-SIGNUP-034] Sign-up without accepting the terms is refused @smoke @regression', async ({ page, data }) => {
  const form = new SignupPage(page);
  await form.open();
  await form.signUp(person(data, { terms: false }));
  await expect(form.error).toHaveText('Please accept the terms and conditions');
  await expect(page).toHaveURL(/\/signup$/);
});
