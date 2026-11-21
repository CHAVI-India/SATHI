// Empirical test of the real JS in templates/promapp/questionnaire_response.html
// Runs the actual script blocks inside jsdom and simulates keystrokes.
const fs = require('fs');
const { JSDOM } = require('jsdom');

const tpl = fs.readFileSync('../../templates/promapp/questionnaire_response.html', 'utf8');
const blocks = [...tpl.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
// Neutralize Django template tags/expressions (they were rendered server-side
// in production; here they just become literals).
const js = blocks.map(b => b.replace(/\{%[\s\S]*?%\}|\{\{[\s\S]*?\}\}/g, 'X')).join('\n;\n');

function inputPart(base, part, max, label) {
  return `<div class="flex flex-col">
    <label for="${base}_${part}">${label}</label>
    <input type="text" inputmode="numeric" data-dt-part="${part}" id="${base}_${part}"
           name="${base}_${part}" maxlength="${max}" placeholder="${label}"></div>`;
}
function composite(type, base) {
  const date = (type === 'Date' || type === 'DateTime')
    ? `<fieldset class="dt-date-group">${inputPart(base,'day',2,'DD')}${inputPart(base,'month',2,'MM')}
       <span class="dt-month-name"></span>${inputPart(base,'year',4,'YYYY')}</fieldset>` : '';
  const time = (type === 'Time' || type === 'DateTime')
    ? `<fieldset class="dt-time-group">${inputPart(base,'hour',2,'HH')}${inputPart(base,'minute',2,'MM')}
       ${inputPart(base,'second',2,'SS')}<span class="dt-meridiem-echo"></span></fieldset>` : '';
  return `<div class="dt-composite" data-dt-type="${type}" data-dt-base="${base}">
    <input type="hidden" name="${base}" class="dt-combined">${date}${time}
    <p class="dt-error hidden" role="alert"></p></div>`;
}
const nav = `<button type="button" class="prev-btn"></button>
             <button type="button" class="next-btn"></button>
             <button type="button" class="skip-to-submit-btn"></button>`;

const html = `<!DOCTYPE html><html><body>
<div id="thank-you-section" style="display:none"></div>
<button id="back-to-questionnaire-btn"></button>
<div id="progress-bar"></div><span id="current-question-number"></span>
<form id="questionnaire-form">
  <div class="question-item" data-question-id="q1" style="display:block">
    ${composite('Date', 'response_q1')}${nav}</div>
  <div class="question-item" data-question-id="q2" style="display:none">
    ${composite('Time', 'response_q2')}${nav}</div>
</form></body></html>`;

const dom = new JSDOM(html, { runScripts: 'outside-only', pretendToBeVisual: true, url: 'http://localhost/' });
const { window } = dom;
window.getCsrfToken = () => 'tok';
// No fetch in jsdom: evaluateRules catches and returns true (question visible).
window.eval(js + `\n;(function(){\n  document.dispatchEvent(new window.Event("DOMContentLoaded"));\n})();`);

const q = i => window.document.querySelectorAll('.question-item')[i];
const part = (base, p) => window.document.getElementById(`${base}_${p}`);
const combined = base => window.document.querySelector(`[data-dt-base="${base}"] .dt-combined`);
const errText = base => window.document.querySelector(`[data-dt-base="${base}"] .dt-error`).textContent;
const visibleQ = () => [...window.document.querySelectorAll('.question-item')]
  .findIndex(el => el.style.display === 'block');
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function type(base, p, text) {
  const el = part(base, p);
  el.focus();
  for (const ch of text) {
    el.value += ch;
    el.dispatchEvent(new window.Event('input', { bubbles: true }));
  }
  await sleep(30);
}

(async () => {
  await sleep(650); // let DOMContentLoaded + fade code settle
  let pass = 0, fail = 0;
  const t = (name, cond) => { if (cond) { pass++; console.log('PASS', name); } else { fail++; console.log('FAIL', name); } };

  // ---- Scenario 1: invalid date 31/04/2025 must NOT advance ----
  await type('response_q1', 'day', '31');
  await type('response_q1', 'month', '04');
  await type('response_q1', 'year', '2025');
  await sleep(400);
  t('invalid date stays on question 1', visibleQ() === 0);
  t('invalid date shows inline error', errText('response_q1').length > 0);
  t('invalid date keeps combined value empty', combined('response_q1').value === '');
  t('invalid date blocks advance flag', combined('response_q1').dataset.dtAdvance !== '1');

  // ---- Scenario 2: correct to valid 14/03/2025 -> auto-advance ----
  await type('response_q1', 'day', '');
  part('response_q1', 'day').value = ''; part('response_q1', 'day').dispatchEvent(new window.Event('input', { bubbles: true }));
  part('response_q1', 'month').value = ''; part('response_q1', 'month').dispatchEvent(new window.Event('input', { bubbles: true }));
  part('response_q1', 'year').value = ''; part('response_q1', 'year').dispatchEvent(new window.Event('input', { bubbles: true }));
  await type('response_q1', 'day', '14');
  await type('response_q1', 'month', '03');
  await type('response_q1', 'year', '2025');
  await sleep(500);
  t('valid date auto-advances to question 2', visibleQ() === 1);
  t('valid date stored canonically', combined('response_q1').value === '2025-03-14');

  // ---- Scenario 3: time with hour+minute only must NOT advance ----
  await type('response_q2', 'hour', '09');
  await type('response_q2', 'minute', '30');
  await sleep(400);
  t('time without seconds stays on question 2', visibleQ() === 1);
  t('time without seconds still valid in rules', combined('response_q2').value === '09:30:00');
  t('time without seconds blocks advance flag', combined('response_q2').dataset.dtAdvance !== '1');

  // ---- Scenario 4: fill seconds -> advance ----
  await type('response_q2', 'second', '00');
  await sleep(500);
  t('time with seconds is complete', combined('response_q2').value === '09:30:00');
  t('seconds-filled time allows advance (last q -> thank you)',
    window.document.getElementById('thank-you-section').style.display === 'block');

  // ---- Scenario 5: illogical time 25:00 must not advance nor validate ----
  window.document.getElementById('thank-you-section').style.display = 'none';
  part('response_q2', 'hour').value = ''; part('response_q2', 'hour').dispatchEvent(new window.Event('input', { bubbles: true }));
  await type('response_q2', 'hour', '25');
  await type('response_q2', 'minute', '00');
  await type('response_q2', 'second', '00');
  await sleep(300);
  t('hour 25 rejected inline', errText('response_q2').length > 0 && combined('response_q2').value === '');

  // ---- Scenario 6: the reported repro - valid mid-edit answer advances,
  // then the final value becomes impossible. Stale value must be cleared.
  q(1).querySelector('.prev-btn').click();  // back to question 1
  await sleep(450);
  part('response_q1', 'day').value = '';
  await type('response_q1', 'day', '31');   // 31/03/2025 -> valid, advances
  await sleep(500);
  const advancedMidEdit = visibleQ() === 1;
  part('response_q1', 'month').value = '';
  await type('response_q1', 'month', '04'); // now 31/04/2025 -> impossible
  await sleep(200);
  t('repro: valid mid-edit state auto-advanced (known behavionr)', advancedMidEdit);
  t('repro: impossible final value clears the stored answer', combined('response_q1').value === '');
  const q1container = window.document.querySelector('[data-dt-base="response_q1"]');
  t('repro: container records the error', (q1container._dtError || '').length > 0);

  // ---- Scenario 7: submit is blocked client-side and jumps to the bad question
  const form = window.document.getElementById('questionnaire-form');
  form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
  await sleep(500);
  t('submit blocked and jumped back to the date question', visibleQ() === 0);
  t('error text now visible on that question', errText('response_q1').length > 0);

  console.log(`\n${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
})();
