"""
Regression tests for the CSRF-token resolution bug.

Background
----------
AJAX/fetch POSTs were failing with 403 (surfacing in the browser as a cryptic
``JSON.parse`` error because the 403 body is HTML, not JSON). The root cause was
that the front-end could not always resolve a valid CSRF token:

* ``templates/promapp/prom_review.html`` read the CSRF cookie with the hard-coded
  name ``csrftoken``, but the server writes the cookie under the app-specific name
  ``CSRF_COOKIE_NAME = 'chaviprom_csrftoken'``. The lookup returned nothing, so an
  empty/undefined ``X-CSRFToken`` header was sent and Django returned 403.

The fix standardizes every AJAX/htmx call on ``window.getCsrfToken()`` (defined in
``templates/base.html``), which resolves the token from the server-rendered hidden
``csrfmiddlewaretoken`` input first, then falls back to the server-rendered
``{{ csrf_token }}`` variable, and throws if neither is available. It never parses
``document.cookie`` with a hard-coded cookie name.

These tests pin that behaviour down:
  1. A page that extends base.html renders a non-empty token via BOTH the hidden
     input and the ``{{ csrf_token }}`` variable (the two sources the JS helper uses).
  2. A CSRF-enforced POST carrying the resolved token succeeds (200), while the same
     POST with an empty token is rejected (403).
"""

import json
import re

from django.test import Client, TestCase
from django.urls import reverse

from promapp.models import Item, Questionnaire, QuestionnaireItem


def js_get_csrf_token(html):
    """
    Mirror of ``window.getCsrfToken()`` in templates/base.html.

    Resolution order (cookie-name independent):
      1. the hidden ``csrfmiddlewaretoken`` input value, if present;
      2. the rendered ``{{ csrf_token }}`` value embedded in the ``window.getCsrfToken()``
         helper in base.html;
      3. '' if neither is available (the JS throws instead of returning '').
    """
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]*)"', html)
    if m and m.group(1):
        return m.group(1)
    m = re.search(r"var rendered = '([^']*)'", html)
    if m and m.group(1):
        return m.group(1)
    return ''


def _htmx_var_token(html):
    """
    Return the ``{{ csrf_token }}`` value rendered into the ``window.getCsrfToken()``
    helper in base.html (path 2 - the fallback source used on pages that have no form).
    """
    m = re.search(r"var rendered = '([^']*)'", html)
    return m.group(1) if m else ''


def _hidden_input_token(html):
    """Return the hidden ``csrfmiddlewaretoken`` input value (path 1)."""
    m = re.search(r'name="csrfmiddlewaretoken"\s+value="([^"]*)"', html)
    return m.group(1) if m else ''


class CsrfTokenRegressionTest(TestCase):
    def setUp(self):
        # enforce_csrf_checks makes the test client actually run the CSRF middleware
        # (by default the Django test client does NOT enforce CSRF).
        self.client = Client(enforce_csrf_checks=True)

    def _fetch_page_with_token(self):
        """
        Fetch a representative logged-out page that extends base.html. The
        ``{% csrf_token %}`` tag on the login form makes Django set the CSRF cookie
        (under the app-specific name), and the page contains both token sources the
        JS helper relies on.
        """
        resp = self.client.get(reverse('account_login'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('chaviprom_csrftoken', [c.key for c in resp.cookies.values()])
        return resp.content.decode()

    def test_both_token_sources_render_non_empty(self):
        html = self._fetch_page_with_token()

        hidden = _hidden_input_token(html)
        var_token = _htmx_var_token(html)

        # Path 1: the {% csrf_token %} tag renders a real token into the hidden input.
        self.assertTrue(
            hidden,
            'The hidden csrfmiddlewaretoken input rendered empty - '
            '{% csrf_token %} tag failed.',
        )
        # Path 2: the {{ csrf_token }} variable (used by the base.html htmx handler and
        # the helper's fallback) renders a real token, not an empty string.
        self.assertTrue(
            var_token,
            'The {{ csrf_token }} variable rendered empty - the CSRF context processor '
            'is not available. base.html htmx calls and the getCsrfToken() fallback '
            'would send an empty token.',
        )
        # Both sources agree on the same session token.
        self.assertEqual(hidden, var_token)

    def test_js_helper_resolves_a_real_token(self):
        html = self._fetch_page_with_token()
        token = js_get_csrf_token(html)
        self.assertTrue(token, 'window.getCsrfToken() resolved to an empty token')

    def test_resolved_token_passes_csrf_and_empty_fails(self):
        # Representative AJAX endpoint that enforces CSRF and returns JSON. With no
        # visibility rules it returns 200 {'should_show': True}.
        questionnaire = Questionnaire.objects.create()
        item = Item.objects.create(response_type='Text')
        qi = QuestionnaireItem.objects.create(
            questionnaire=questionnaire, item=item, question_number=1
        )
        url = reverse('evaluate_question_rules', args=[qi.id])

        html = self._fetch_page_with_token()
        token = js_get_csrf_token(html)
        self.assertTrue(token)

        # 1) POST with the token exactly as the JS would resolve/send it -> 200.
        ok = self.client.post(
            url,
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(
            ok.status_code, 200,
            f'Expected 200 with resolved token, got {ok.status_code}: {ok.content[:200]!r}',
        )
        self.assertEqual(ok.json(), {'should_show': True})

        # 2) The same POST with an EMPTY token (the old broken behaviour) -> 403.
        bad = self.client.post(
            url,
            data=json.dumps({}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN='',
        )
        self.assertEqual(
            bad.status_code, 403,
            f'Expected 403 with empty token, got {bad.status_code}',
        )
        # The 403 body is HTML, which is why the browser saw a JSON.parse error.
        self.assertIn('text/html', bad['Content-Type'])
