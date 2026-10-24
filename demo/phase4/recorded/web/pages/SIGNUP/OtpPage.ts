// OTP page of SIGNUP: six digit boxes and Verify.
import { Page, Locator } from '@playwright/test';

export class OtpPage {
  readonly heading: Locator;
  readonly error: Locator;
  constructor(private page: Page) { this.heading = page.getByRole('heading', { level: 1 }); this.error = page.getByTestId('error'); }
  async enter(code: string) {
    for (const [i, d] of [...code].entries()) await this.page.getByTestId(`otp-${i + 1}`).fill(d);
    await this.page.getByTestId('verify').click();
  }
}
