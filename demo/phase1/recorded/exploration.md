# Web exploration: file:///<project>/demo/phase1/site/index.html
Explored 2026-10-21T20:24 with msedge. Pages: 2. Everything below is OBSERVED behaviour, not confirmed requirements.
Values tried per form: empty; invalid (e.g. "not-an-email", "12", "1", numeric boxes "x"); valid (e.g. "Test User", "0551234567", numeric boxes "1", first option, boxes ticked). A real valid code or password is not known to the explorer.

## Page 01: Nakhla Rewards - Sign up
- URL: file:///<project>/demo/phase1/site/index.html
- Language: en, direction: ltr
- Screenshot: 01-page.png
- Headings: Create your account

### Form 0 (GET same page, browser validation off, so browser messages are not shown) buttons: Sign up
| Field | Label | Type | Required | Rules |
|---|---|---|---|---|
| fullName | Full name | text | yes | maxlength=40 |
| mobile | Mobile number | tel | yes | pattern=^05[0-9]{8}$ |
| password | Password | password | yes | minlength=6 |
| birthDate | Date of birth | date | yes |  |
| language | Language | select-one | no | options: العربية, English |
| terms | I accept the terms and conditions | checkbox | yes |  |
- Submitted **empty**: "Please enter your full name"; "Enter a Saudi mobile number starting with 05"; "Password must be at least 6 characters"; "You must be 18 or older"; "Please accept the terms and conditions" (screenshot 01-form0-empty.png)
- Submitted **invalid**: "Enter a Saudi mobile number starting with 05"; "Password must be at least 6 characters"; "Please accept the terms and conditions" (screenshot 01-form0-invalid.png)
- Submitted **valid**: no message shown -> went to file:///<project>/demo/phase1/site/otp.html (screenshot 01-form0-valid.png)

<details><summary>Visible text</summary>

```
Nakhla Rewards
Create your account
Full name
Mobile number
Password
Date of birth
Language
العربية
English
I accept the terms and conditions
Sign up
```
</details>

## Page 02: Nakhla Rewards - Verify your number
- URL: file:///<project>/demo/phase1/site/otp.html
- Language: en, direction: ltr
- Screenshot: 02-page.png
- Headings: Verify your mobile number

### Form 0 (GET same page, browser validation off, so browser messages are not shown) buttons: Verify
| Field | Label | Type | Required | Rules |
|---|---|---|---|---|
| d1 | Digit 1 | text (numeric) | yes | maxlength=1 |
| d2 | Digit 2 | text (numeric) | yes | maxlength=1 |
| d3 | Digit 3 | text (numeric) | yes | maxlength=1 |
| d4 | Digit 4 | text (numeric) | yes | maxlength=1 |
| d5 | Digit 5 | text (numeric) | yes | maxlength=1 |
| d6 | Digit 6 | text (numeric) | yes | maxlength=1 |
- Submitted **empty**: "الرمز غير صحيح" (screenshot 02-form0-empty.png)
- Submitted **invalid**: "الرمز غير صحيح" (screenshot 02-form0-invalid.png)
- Submitted **valid**: "الرمز غير صحيح" (screenshot 02-form0-valid.png)

<details><summary>Visible text</summary>

```
Nakhla Rewards
Verify your mobile number

We sent a code by SMS. Enter it below.

Verify
Resend code (30)
```
</details>
