# Module intake: <MODULE NAME>
Copy to `workflow/intake/<module>.md` and fill in. Short, numbered, exact. Leave a field empty if unknown; do not guess.

## 1. Scope
- Module: <e.g. Signup> | Module code for IDs: <e.g. SIGNUP>
- Platforms: [ ] Android [ ] iOS [ ] API [ ] Web
- Build / URL / environment: <>

## 2. Business rules (numbered, exact values)
1. <e.g. Email must be unique>
2. <e.g. Password: 8+ characters, at least 1 number>
3. <e.g. OTP expires after 5 minutes, max 3 attempts>

## 3. Flow and screens
- Steps in order: <screen A -> screen B -> ...>
- Screenshots / recording: <paths, e.g. docs/signup/*.png>
- Or: [ ] let TestHive explore the app and report back

## 4. Expected results (exact wording)
| Situation | Expected result / message |
|---|---|
| Success | <> |
| Invalid <field> | <> |
| Duplicate <field> | <> |

## 5. API / backend (if any)
- Endpoints or collection: <Postman / Swagger path or sample requests>
- Auth and test data needs: <>

## 6. Priorities
- P0 (must work): <>
- P1: <>
- P2 / nice to have: <>

## 7. Out of scope
- <what to skip>

## 8. Test data and cleanup
- How to create unique users: <script / pattern>
- Data that must not be touched: <>
- OTP / captcha / email handling: <>

## 9. Known issues and open questions
- <known bugs, unclear rules; say which is right: app or spec>
