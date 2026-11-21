# Browser-behaviour tests for date/time question boxes

These tests run the *actual* JavaScript embedded in
`templates/promapp/questionnaire_response.html` inside `jsdom` and simulate
keystrokes (invalid dates, half-typed times, mid-edit auto-advance, submit
guard). They guard behaviours Django unit tests cannot reach: auto-advance
timing, box focus movement, and the client-side submit guard.

```sh
cd scripts/js-tests
npm init -y && npm i jsdom   # once
node dt_behaviour_test.js    # all assertions must PASS
```
