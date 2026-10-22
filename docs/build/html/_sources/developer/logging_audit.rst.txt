Logging Configuration Audit
============================

Comprehensive audit of the chavi-prom logging configuration: patient PHI
exposure in log files and log-rotation gaps. Covers findings, remediation
applied, and outstanding follow-up items.

.. contents:: Table of Contents
   :local:
   :depth: 3

Overview
--------

**Audit date:** 2026-09-16
**Scope:** All log files under ``logs/`` and the project root, the Django
``LOGGING`` configuration in ``chaviprom/settings.py``, the gunicorn
configuration in ``gunicorn.conf.py``, and all ``logger.*()`` call sites
in ``patientapp``, ``promapp``, ``providerapp``, and ``chaviprom``.
**Method:** Static review of configuration + call sites, inspection of
existing log file contents and sizes.

The ``Patient`` model (``patientapp/models.py:59``) stores PHI in encrypted
fields (``name``, ``patient_id``, ``date_of_registration``, ``age``,
``gender``) via the ``secured_fields`` package. While these are encrypted
at rest in the database, numerous log call sites write the decrypted
values in plaintext to log files, which are not encrypted and are
gitignored (``.gitignore``: ``*.log``, ``logs/``).

Inventory of log files
----------------------

============================ =============== ===================== ================================= ==================
Path                         Size observed   Handler / source      Rotation                          Configured in
============================ =============== ===================== ================================= ==================
``logs/django.log``          916 KB          ``file``              RotatingFileHandler 10MB / 5      ``settings.LOGGING``
``logs/django_error.log``    756 KB          ``error_file``        RotatingFileHandler 10MB / 5      ``settings.LOGGING``
``logs/promapp_rules.log``   216 KB          ``promapp_rules_file`` RotatingFileHandler 10MB / 5     ``settings.LOGGING``
``logs/security.log``        82 KB           ``security_file``     RotatingFileHandler 10MB / 5      ``settings.LOGGING``
``logs/two_factor_auth.log`` 73 KB           ``tfa_file``          RotatingFileHandler 10MB / 5      ``settings.LOGGING``
``logs/plotting_data.log``   **87 MB**       ``plotting_file``     RotatingFileHandler 10MB / 5      ``settings.LOGGING`` *(was manual ``FileHandler``, no rotation)*
``celery_worker.log`` (root) 448 KB          manual redirect      **None**                          *(manual celery launch)*
``test_output.log`` (root)   860 KB          test harness capture  **None**                          *(test script)*
``logs/gunicorn-access.log`` *(future)*      ``access_file``       RotatingFileHandler 15MB / 10     ``gunicorn.conf.py``
``logs/gunicorn-error.log``  *(future)*      ``error_file``        RotatingFileHandler 15MB / 10     ``gunicorn.conf.py``
============================ =============== ===================== ================================= ==================

PHI exposure findings
---------------------

Each finding lists the log file, severity, sample evidence, and the
source call site. Severities reflect sensitivity of the data and breadth
of exposure.

A1. plotting_data.log — CRITICAL
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** Logs the index patient UUID, per-patient score dataframes,
and a full ``METADATA`` dict containing ``patient_details`` with each
patient's ``name``, ``id``, ``start_date``, and ``score_count``::

    2025-06-01 11:05:36,153 - INFO - Patient: PAT5
    2025-06-01 11:05:36,165 - INFO - METADATA: {... 'patient_details': {'contributing': [{'patient_name': 'PAT6', 'patient_id': 'PAT6', ...}]}}
    Patient: PAT6 (Start: 2024-09-01)

**Source:** ``patientapp/utils.py`` — ``plotting_logger`` call sites at
lines 813, 848, 856, 2233-2238, 2276-2317, 2321, 2546.

A2. django.log — HIGH (patient name in plaintext)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** Questionnaire submission registration logs the patient
**name** in plaintext::

    [2026-05-31 15:39:47,289] INFO promapp.construct_scores New questionnaire submission registered: 885846ac-... from patient Test Patient 0

**Source:** ``promapp/models.py:1207`` and ``promapp/models.py:1245``.

A3. django.log — HIGH (patient UUIDs)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** PRO Review and patient portal views log patient primary
keys and UUIDs::

    INFO patientapp.views PRO Review view called for patient ID: <pk>, print_mode=...
    INFO patientapp.views Found patient UUID: <uuid>
    INFO patientapp.views Patient portal accessed by: <name> (ID: <uuid>)

**Source:** ``patientapp/views.py:82,86,1666``.

A4. django.log — MEDIUM (middleware)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** Language middleware logs patient name and ID::

    INFO patientapp.middleware Patient <name> manually chose language ...
    INFO patientapp.middleware Language auto-switched ... for patient <name> (ID: <uuid>)

**Source:** ``patientapp/middleware.py:50,69``.

A5. django.log — MEDIUM (celery tasks)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** Batch plot generation tasks log the patient id::

    INFO patientapp.tasks Starting batch plot generation for patient <id>, ... plots

**Source:** ``patientapp/tasks.py:35,77``.

A6. promapp_rules.log — HIGH (questionnaire responses)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** The ``promapp.rules`` logger records each ``QuestionnaireItem``
UUID together with the full responses dict, i.e. the patient's
questionnaire answers (PHI)::

    INFO promapp.rules Evaluating rules for QuestionnaireItem <uuid> with responses: {'<item-uuid>': '3.00', ...}

**Source:** ``promapp/views.py:3675`` (``logger = logging.getLogger("promapp.rules")``).

A7. gunicorn-access.log — HIGH (patient UUIDs in URLs)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** The gunicorn access log format ``%(r)s`` records the full
request line. Patient UUIDs appear in URLs such as
``GET /patients/<uuid>/prom-review/`` and
``GET /patients/<uuid>/prom-review/construct-plot/<uuid>/``.

**Source:** ``gunicorn.conf.py`` ``access_log_format``.

A8. celery_worker.log — MEDIUM
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Evidence:** Celery task logs include task args/kwargs that carry patient
IDs. The file is created at the project root by the manual
``celery -A chaviprom worker`` launch (see ``test_output.log`` header:
"Logs are being written to: celery_worker.log").

A9. django_error.log — inherits A2-A5
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same call sites (A2-A5) write to ``django_error.log`` at ERROR level
via the shared ``error_file`` handler, so PHI propagates there too.

Log-rotation findings
---------------------

B1. plotting_data.log — FIXED
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Was:** ``patientapp/utils.py`` created a plain ``logging.FileHandler``
(no rotation) for the ``plotting_data`` logger, outside the ``LOGGING``
dict. The file grew to 87 MB.

**Now:** The ``plotting_data`` logger is configured in
``settings.LOGGING`` with a ``plotting_file`` ``RotatingFileHandler``
(10 MB, 5 backups) and the ``phi_mask`` filter. The manual handler setup
in ``patientapp/utils.py`` was removed.

B2. celery_worker.log — OUTSTANDING (follow-up)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Created by the manual celery worker launch; no rotation. There is no
supervisor configuration for celery in
``docs/source/developer/installation.rst`` (only gunicorn is supervised).

**Recommended remediation (follow-up):**

1. Launch celery under supervisor with
   ``--logfile=logs/celery_worker.log``.
2. Add a ``celery`` logger and ``celery_file`` ``RotatingFileHandler``
   (with the ``phi_mask`` filter) to ``settings.LOGGING``.
3. Set ``CELERY_WORKER_HIJACK_ROOT_LOGGER = True`` so celery uses the
   Django logging config.

B3. test_output.log — OUTSTANDING (low priority)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A one-off test-harness capture, not a production log. Already gitignored.
**Recommendation:** delete after test runs; no code change required.

B4. gunicorn access log — FIXED
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Was:** ``gunicorn.conf.py`` set ``accesslog`` to a file path with no
rotation handler; only ``error_file`` had a ``RotatingFileHandler`` in
``logconfig_dict``.

**Now:** ``accesslog``/``errorlog`` are set to ``None`` and both access
and error logging are routed through ``logconfig_dict`` handlers
(``access_file`` and ``error_file``), each a ``RotatingFileHandler``
(15 MB, 10 backups) with the ``phi_mask`` filter.

B5. two_factor_auth.log — orphaned handler (informational)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``tfa_file`` handler remains in ``settings.LOGGING`` and is still
used by the ``django.contrib.auth`` logger (``settings.py``). However, all
the ``two_factor.*`` and ``django_otp.*`` loggers that referenced it are
commented out (``settings.py:426-495``). The handler is retained to avoid
breaking the ``django.contrib.auth`` → ``tfa_file`` wiring; the ``phi_mask``
filter is now applied to it.

B6-B9. django.log, django_error.log, promapp_rules.log, security.log — OK
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

All use ``RotatingFileHandler`` (10 MB, 5 backups) and now carry the
``phi_mask`` filter.

Remediation applied
-------------------

1. **PHIMaskingFilter** (``chaviprom/logging_filters.py``): a
   ``logging.Filter`` that redacts:

   * Full UUIDs → ``<8-char-prefix>***`` (prefix retained for log
     correlation across entries).
   * Values after the introducers ``from patient``, ``Patient:``,
     ``patient ID:``, and ``accessed by:`` → ``[REDACTED]``.
   * Dict values whose keys match ``patient_name``, ``patient_id``, or
     ``name`` → ``[REDACTED]`` (best-effort for ``%s``-formatted dicts).

   The filter is attached to **all file handlers** in
   ``settings.LOGGING`` and in ``gunicorn.conf.py``. The console handler
   is intentionally left unfiltered so developers retain readable output.

2. **plotting_data rotation**: moved into ``settings.LOGGING`` with a
   ``RotatingFileHandler``; removed the unbounded ``FileHandler`` in
   ``patientapp/utils.py``.

3. **gunicorn access/error rotation + masking**: routed through
   ``logconfig_dict`` with ``RotatingFileHandler`` (15 MB, 10 backups)
   and the ``phi_mask`` filter.

4. **Tests**: ``patientapp/tests_logging.py`` covers UUID redaction,
   patient-name/ID redaction, dict-arg masking, and clean-message
   pass-through.

Existing log files were **left untouched** per project decision; the
remediation is forward-only. Accumulated PHI in
``logs/plotting_data.log`` (87 MB) and other files remains and should be
purged in a separate, explicitly-approved operation.

Outstanding / follow-up items
-----------------------------

* **celery_worker.log rotation** (B2): requires a supervisor/launch
  config in the repository; not implemented in this audit. See B2 above.
* **test_output.log cleanup** (B3): test artifact; recommend deleting
  after test runs.
* **Stop logging full ``metadata``/``patient_details`` dicts**: the
  cleanest fix for ``plotting_data.log`` is to stop emitting the full
  ``patient_details`` dict at ``patientapp/utils.py:2276-2317``. The
  filter redacts known PHI keys, but deeply nested or future-added
  patient fields could still leak. Recommended as a follow-up to
  reduce the dict to aggregate counts only.
* **Orphaned ``tfa_file`` handler** (B5): decide whether to remove the
  commented-out ``two_factor.*`` logger blocks and the handler, or
  re-enable them when two-factor auth is restored.
* **Existing PHI purge**: the existing ``logs/plotting_data.log`` and
  other log files contain real patient PHI accumulated before the
  filter was in place. A separate, explicitly-approved purge/truncation
  is recommended.
* **Questionnaire response logging** (A6): consider lowering the
  ``promapp.rules`` logger from DEBUG to INFO in production so
  per-item response dicts are not written to ``promapp_rules.log``.

Verification
------------

To confirm the remediation:

.. code-block:: bash

    # PHI-masking filter tests
    python manage.py test patientapp.tests_logging

    # Full patientapp suite (no regressions)
    python manage.py test patientapp

    # Django config check
    python manage.py check

    # Confirm plotting_data logger has one RotatingFileHandler with the filter
    python manage.py shell -c "import logging; h=logging.getLogger('plotting_data').handlers; print([(type(x).__name__, getattr(x,'maxBytes',None), [type(f).__name__ for f in x.filters]) for x in h])"
    # Expected: [('RotatingFileHandler', 10485760, ['PHIMaskingFilter'])]

    # Manual: trigger a masked line and inspect the file
    python manage.py shell -c "import logging; logging.getLogger('patientapp').info('from patient Test Patient 0')"
    tail -1 logs/django.log
    # Expected: ... from patient [REDACTED]

To confirm no existing log file was modified or deleted:

.. code-block:: bash

    git status -- logs/ celery_worker.log test_output.log
    # Expected: nothing to commit, working tree clean (logs are gitignored)
