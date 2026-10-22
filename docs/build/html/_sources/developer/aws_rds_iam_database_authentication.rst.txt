AWS RDS IAM Database Authentication
====================================

A step-by-step guide to replacing static Postgres passwords with AWS IAM
database authentication, for deployments of SATHI on Amazon EC2 + Amazon RDS.

This guide is deployment-agnostic: every AWS-specific value is a
placeholder (``<...>``) that you fill in from your own account. The steps
were executed end-to-end on a live deployment (October 2026), and every
pitfall documented here was hit and fixed on that deployment.

.. contents:: Table of Contents
   :local:
   :depth: 2

How it works
------------

- The app server's EC2 **instance profile** (IAM role) lets the application
  mint a signed, **15-minute authentication token** that is used *in place
  of the password* when connecting to RDS.
- Token minting happens **client-side** (SigV4 signing inside the SDK): no
  AWS API call is made and nothing is recorded in CloudTrail. The IAM
  policy is evaluated by RDS when it validates the presented token.
- A token only matters **at connect time** — established connections
  persist past token expiry. A fresh token is minted for every new
  connection, so long-lived web workers are fine at any ``CONN_MAX_AGE``.
- The RDS setting is a mode: **"Password and IAM database
  authentication"**. Enabling it never breaks existing password logins,
  which makes the migration staged and reversible.
- A PostgreSQL user must be granted the **``rds_iam`` role** to
  authenticate with tokens. A user with that role can use exactly one
  authentication method — the token, not a password.

Prerequisites
-------------

- An RDS for PostgreSQL instance (9.6 or later; any current version works).
- The application deployed on EC2 in the same VPC as the RDS instance
  (recommended; see the hardening phase).
- AWS CLI v2 or AWS CloudShell, with a user holding IAM + RDS management
  rights, configured for the correct region.
- The RDS **master user password** (needed once, in Phase 4).
- ``psql`` is **not** preinstalled on a standard EC2 VM or in CloudShell.
  Install it where you need it:

  .. code-block:: bash

     sudo apt update && sudo apt install -y postgresql-client

Phase 0 — Gather facts
----------------------

From the AWS CLI (or CloudShell):

.. code-block:: bash

   aws sts get-caller-identity
   aws rds describe-db-instances \
     --query "DBInstances[].{id:DBInstanceIdentifier, resource:DbiResourceId, ver:EngineVersion, endpoint:Endpoint.Address, port:Endpoint.Port, public:PubliclyAccessible, vpcsg:VpcSecurityGroups}"

Collect:

- **``DbiResourceId``** (``db-XXXXXXXXXXXXX`` form) — required for the IAM
  policy ARN. The instance *name* (``DBInstanceIdentifier``) does **not**
  work in that ARN; using it is a very common cause of silent
  "access denied".
- Account ID, region, endpoint + port, engine version.
- VPC ID, attached security group IDs, instance class.
- The instance's *master* database name versus the database the app uses —
  an RDS instance can host multiple databases.
- The app server's EC2 instance ID (on the VM:
  ``curl -s http://169.254.169.254/latest/meta-data/instance-id``).
- ``PubliclyAccessible`` — if ``true``, treat that as an incident-level
  finding and harden first (Phase 6).
- Whether the instance is **shared** with other clients (other apps,
  DMS, other EC2 instances). Enabling IAM auth is inert to them, but
  later network changes are not — know who connects before you change
  anything.

.. warning::

   If another workload shares the RDS instance, plan for it: it keeps
   working on password auth, but security-group and
   ``PubliclyAccessible`` changes affect it too.

Phase 1 — Create the IAM role and policy
----------------------------------------

Create the role (trust policy for EC2):

.. code-block:: json

   {"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}

.. code-block:: bash

   aws iam create-role --role-name <app>-app-role \
     --assume-role-policy-document file:///tmp/trust.json

Create a scoped policy. Note the **``DbiResourceId``** in the resource ARN:

.. code-block:: json

   {
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Action": "rds-db:Connect",
       "Resource": "arn:aws:rds-db:<region>:<account-id>:dbuser:db-<dbi-resource-id>/<app-db-user>"
     }]
   }

.. code-block:: bash

   aws iam create-policy --policy-name <app>-rds-iam-db-connect \
     --policy-document file:///tmp/rds-connect.json
   aws iam attach-role-policy --role-name <app>-app-role \
     --policy-arn arn:aws:iam::<account-id>:policy/<app>-rds-iam-db-connect

The username in the ARN must match the database user name
**case-sensitively**.

.. warning::

   **Do not add VPC condition keys to this policy.** A tool may
   recommend adding ``"Condition": {"StringEquals": {"aws:SourceVpc":
   "<vpc-id>"}}`` to restrict token use to one VPC. That is wrong: IAM
   database authentication does **not support** the global condition keys
   ``aws:SourceVpc``, ``aws:SourceVpce``, ``aws:SourceIp``,
   ``aws:VpcSourceIp``, ``aws:UserAgent`` or ``aws:Referer`` (see the RDS
   User Guide, "Limitations for IAM database authentication"). The
   ``rds-db`` service supports exactly one condition key:
   ``aws:ResourceTag/${TagKey}``. An unsupported key is never present in
   the request context, so the condition never matches and **every
   token-based connection is denied** — the cutover breaks completely.
   The "only from this VPC" property is enforced at the network layer
   (private instance + security-group rules), not in the policy.

Phase 2 — Attach the role to the EC2 instance
---------------------------------------------

A role cannot be attached to an instance directly — EC2 uses an
**instance profile** (a container that holds the role):

.. code-block:: bash

   aws iam create-instance-profile --instance-profile-name <app>-app-profile
   aws iam add-role-to-instance-profile \
     --instance-profile-name <app>-app-profile \
     --role-name <app>-app-role
   aws ec2 associate-iam-instance-profile \
     --instance-id i-<instance-id> \
     --iam-instance-profile Name=<app>-app-profile

.. note::

   ``--iam-instance-profile Name=`` expects the **profile** name, not the
   role name. Passing the role name fails with ``InvalidParameterValue``.
   The console flow masks this by auto-creating a profile named after the
   role — so "it worked from the console" does not mean the CLI form with
   the role name is valid.

Verify:

.. code-block:: bash

   # from the AWS CLI:
   aws ec2 describe-iam-instance-profile-associations \
     --filters Name=instance-id,Values=i-<instance-id>

   # or from the VM (should report the role):
   curl -s http://169.254.169.254/latest/meta-data/iam/info

The change is immediate; no reboot, and nothing running on the VM is
affected until it next fetches credentials.

Phase 3 — Enable IAM authentication on the RDS instance
-------------------------------------------------------

.. code-block:: bash

   aws rds modify-db-instance --db-instance-identifier <db-identifier> \
     --enable-iam-database-authentication --apply-immediately

The response is a snapshot at request time: it may still show
``IAMDatabaseAuthenticationEnabled: false`` with the change listed under
``PendingModifiedValues`` — that is normal. Re-verify within minutes:

.. code-block:: bash

   aws rds describe-db-instances --db-instance-identifier <db-identifier> \
     --query 'DBInstances[0].{iam: IAMDatabaseAuthenticationEnabled, pending: PendingModifiedValues}'

Expect ``iam: true`` and ``pending: {}``. If it is still pending after
~10 minutes it has slipped to the maintenance window — investigate.

Also enable the **``iam-db-auth-error``** log export (console: Modify →
Log exports). It is the troubleshooting trail for Phase 5.

Phase 4 — Create the database user and grants
---------------------------------------------

From a machine with ``psql`` (the app VM, after the install from the
prerequisites), connect as the master user:

.. code-block:: bash

   PGPASSWORD='<master-password>' psql \
     "host=<endpoint> port=5432 dbname=<db-name> user=<master-user> sslmode=require"

Confirm who owns the existing tables (this drives the default-privilege
``FOR ROLE`` choice):

.. code-block:: sql

   SELECT tablename, tableowner FROM pg_tables
   WHERE schemaname='public' ORDER BY tablename LIMIT 10;

Create the user and grants (all as the master user):

.. code-block:: sql

   CREATE USER <app-db-user>;              -- LOGIN by default, no password
   GRANT rds_iam TO <app-db-user>;         -- REQUIRED for token auth

   GRANT CONNECT, TEMP ON DATABASE <db-name> TO <app-db-user>;
   GRANT USAGE ON SCHEMA public TO <app-db-user>;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO <app-db-user>;
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO <app-db-user>;
   -- sequence grants: auto-increment / bigserial primary keys need them

   -- covers objects created *later* by the role that currently owns the
   -- schema objects (<owner> — usually the master user):
   ALTER DEFAULT PRIVILEGES FOR ROLE <owner> IN SCHEMA public
     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO <app-db-user>;
   ALTER DEFAULT PRIVILEGES FOR ROLE <owner> IN SCHEMA public
     GRANT USAGE, SELECT ON SEQUENCES TO <app-db-user>;

Migrations need DDL (``CREATE``/``ALTER``/``DROP``), which the grants above
do not include. Choose one:

- **A.** ``ALTER SCHEMA public OWNER TO <app-db-user>;`` — the app user
  owns the schema and can migrate; broadest runtime rights.
- **B.** A separate migration user with a password, used only by the
  deploy script — cleanest separation, one secret to manage.
- **C.** ``GRANT CREATE ON SCHEMA public TO <app-db-user>;`` — the
  least-privilege option that fully suffices for ``migrate`` (new objects
  are self-owned). Recommended for a single-app deployment.

If the app user runs migrations, execute the chosen statement **before**
the cutover, so a pending migration cannot fail at deploy time.

One role and one database user per connecting instance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If a second EC2 instance also connects to the same database, give it its
**own** IAM role and its **own** least-privilege database user (its policy
scoped to ``...dbuser:db-<dbi-resource-id>/<second-db-user>``). Rationale:
least privilege (a compromised box inherits only its own grants),
per-instance audit attribution, and independent lifecycle. Exception: if
the second instance runs the *same* application (spare/replica web
server), sharing one DB user — and thus one role — is acceptable. Migrating
one app does not block the others: the instance stays in
Password-and-IAM mode, so other clients keep working on passwords until
their own cutover.

Phase 5 — Verify the token path before touching the app
-------------------------------------------------------

On the app VM, mint a token using the instance role. With the AWS CLI:

.. code-block:: bash

   TOKEN=$(aws rds generate-db-auth-token \
     --region <region> \
     --hostname <endpoint> \
     --port 5432 \
     --username <app-db-user>)

Without the AWS CLI (using the venv's ``boto3``, which the app package
pulls in anyway):

.. code-block:: bash

   cd /var/www/<app> && source venv/bin/activate
   TOKEN=$(python -c "import boto3; print(boto3.session.Session().client('rds', region_name='<region>').generate_db_auth_token(DBHostname='<endpoint>', Port=5432, DBUsername='<app-db-user>'))")

Sanity-check, then connect:

.. code-block:: bash

   echo ${#TOKEN}    # a real token is ~1800 chars; 0 means the var is empty

   PGPASSWORD="$TOKEN" psql \
     "host=<endpoint> port=5432 dbname=<db-name> user=<app-db-user> sslmode=require" \
     -c 'SELECT current_user' -c '\dt'

Expect ``current_user`` to be the app user and the table list to be
returned. That one success proves the whole chain: role → policy → token →
``rds_iam`` grant → table grants → security-group path → TLS.

If ``psql`` is unavailable, the app-level equivalent is
``python manage.py check --database default`` (it opens a real
connection).

If it fails, check in this order:

1. IAM policy ARN — ``db-…`` resource ID, username case, region, account.
2. ``GRANT rds_iam TO <app-db-user>;`` present.
3. Security-group path from the VM to the instance.
4. The ``iam-db-auth-error`` CloudWatch log (Phase 3).

App-side changes
----------------

Requirements
~~~~~~~~~~~~

.. code-block:: text

   django-iam-dbauth==0.2.1

Pin the version. The package wraps Django's own PostgreSQL backend
(works with psycopg2), mints a fresh token in
``get_connection_params()`` (per connection — safe with long-lived
workers), and resolves CNAMEs so tokens are signed for the canonical
endpoint (disable with ``resolve_cname_enabled: False`` for private
endpoints or custom CNAMEs).

.. note::

   There is **no pip package** for the RDS CA certificate bundle (the
   ``rds-ca-bundle`` name does not exist on PyPI), and ``certifi`` is the
   **wrong** bundle (Mozilla's public CAs — Amazon's RDS CA is not in
   it). Certificate verification uses a downloaded PEM; see the TLS
   section below.

Settings (open-source friendly)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The app also deploys in non-AWS environments, so IAM auth must be
**opt-in**: a single flag switches the backend; without it the app
behaves exactly as before. Nothing AWS-specific is loaded unless a
deployment explicitly opts in:

.. code-block:: python

   DATABASES = {
       'default': {
           'ENGINE': os.environ.get('DJANGO_DATABASE_ENGINE', 'django.db.backends.sqlite3'),
           'NAME': os.environ.get('DJANGO_DATABASE_NAME', 'db.sqlite3'),
           'USER': os.environ.get('DJANGO_DATABASE_USER', ''),
           'HOST': os.environ.get('DJANGO_DATABASE_HOST', 'localhost'),
           'PORT': os.environ.get('DJANGO_DATABASE_PORT', '5432'),
       }
   }

   if os.getenv('DJANGO_DATABASE_IAM_AUTH', 'False') == 'True':
       # Postgres-only path (RDS). The password is never read or sent.
       DATABASES['default'].update({
           'ENGINE': 'django_iam_dbauth.aws.postgresql',
           'PASSWORD': '',
           'OPTIONS': {
               'use_iam_auth': True,
               'sslmode': os.getenv('DJANGO_DATABASE_SSL_MODE', 'require'),
               # once the RDS CA bundle PEM is available on the host:
               # 'sslmode': 'verify-full',
               # 'sslrootcert': '/path/to/rds-global-bundle.pem',
           },
       })
   else:
       DATABASES['default']['PASSWORD'] = os.environ.get('DJANGO_DATABASE_PASSWORD', '')

Properties of this design:

- The flag is orthogonal to the environment variable that selects
  dev/staging/prod — every non-AWS deployment keeps working unchanged.
- ``django_iam_dbauth`` is imported only when the engine is actually used,
  so non-AWS hosts never touch it (keeping it in ``requirements.txt``
  makes deploys uniform).
- ``sslmode`` is environment-driven, so the follow-up to ``verify-full``
  is a ``.env`` change, not a code change.

Environment (``.env``)
~~~~~~~~~~~~~~~~~~~~~~

AWS production host:

.. code-block:: text

   AWS_DEFAULT_REGION=<region>     # botocore reads *credentials* from the
                                   # instance metadata but not the *region* —
                                   # without it: NoRegionError on first connect
   DJANGO_DATABASE_IAM_AUTH=True
   DJANGO_DATABASE_ENGINE=django.db.backends.postgresql_psycopg2
   DJANGO_DATABASE_NAME=<db-name>
   DJANGO_DATABASE_USER=<app-db-user>
   DJANGO_DATABASE_HOST=<endpoint>
   DJANGO_DATABASE_PORT=5432
   # DJANGO_DATABASE_PASSWORD is no longer needed

Any non-AWS production (unchanged from today): the flag stays unset and
``DJANGO_DATABASE_PASSWORD`` is provided as usual.

.. warning::

   ``NoRegionError: You must specify a region`` on the first connection
   with the IAM backend means the host has no region configured anywhere
   botocore looks (no ``AWS_DEFAULT_REGION`` env var, no
   ``~/.aws/config``). botocore resolves **credentials** from instance
   metadata but **not** the region. Set ``AWS_DEFAULT_REGION=<region>`` in
   the app's ``.env`` (``load_dotenv`` puts it in the environment before
   any DB connection); the alternative is passing ``region_name`` in the
   ``OPTIONS`` dict.

TLS hardening (fast follow-up, after the cutover works)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``sslmode=require`` (the default) encrypts but does not verify the server.
To verify, download the RDS CA bundle from AWS's PKI trust store (the
global bundle covers all current RDS CAs and supersedes the legacy
``s3.amazonaws.com/rds-downloads/…`` URLs):

.. code-block:: bash

   sudo mkdir -p /var/www/<app>/certs
   sudo curl -o /var/www/<app>/certs/rds-global-bundle.pem \
     https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem

Then switch ``OPTIONS`` to ``sslmode: verify-full`` plus
``sslrootcert`` pointing at the PEM, and re-test the connection. Do **not**
point ``sslrootcert`` at ``certifi`` — the RDS CA is not in it and
verification will fail.

Deployment and cutover
----------------------

Cutover order (why it is safe):

.. code-block:: text

   Phase 1–2  role + profile + attach   → inert
   Phase 3    enable IAM auth           → inert (password logins unaffected)
   Phase 4    user + grants             → inert
   Phase 5    token test                → proves readiness without deploying
   Deploy     app-side changes + restart → the actual cutover
   Phase 6    hardening

Deploy (typical supervisor/gunicorn setup):

.. code-block:: bash

   # update the server's .env as above, commit + push, then:
   git pull
   pip install -r requirements.txt
   python manage.py migrate        # first live exercise of the new path —
                                   # also proves the migration DDL grant
   python manage.py collectstatic --noinput
   sudo supervisorctl restart all  # gunicorn and the celery worker

Verify after restart:

.. code-block:: bash

   python manage.py check --database default   # must report no issues

Plus a quick look at the app itself, and watch CloudWatch
``IamDbAuthConnectionFailure`` and the ``iam-db-auth-error`` log for the
first few minutes.

Rollback
~~~~~~~~

If anything fails after the switch: redeploy the previous settings
(commit) and restart — the password path still works, because the instance
runs in *Password and IAM* mode. Full reversal, if ever needed:

.. code-block:: bash

   aws rds modify-db-instance --db-instance-identifier <db-identifier> \
     --no-enable-iam-database-authentication

.. code-block:: sql

   -- as the master user; a token-only user has no password, so revoke
   -- first, then set a password only if you want one:
   REVOKE rds_iam FROM <app-db-user>;
   -- ALTER USER <app-db-user> PASSWORD '...';

Phase 6 — Hardening and operations
----------------------------------

- **Break-glass access:** store the master password in AWS Secrets
  Manager (or a password manager) and document the Phase 5 token +
  ``psql`` commands so a human can reach the database in an incident.
- **Remove old credentials:** drop the ``DJANGO_DATABASE_PASSWORD`` line
  from the server ``.env``; rotate or delete any former application
  account. Check supervisor environment files — any process still reading
  a stale password will silently keep the old path.
- **Clock:** confirm NTP (chrony/systemd-timesyncd) is active — signed
  tokens are clock-sensitive.
- **IMDS:** confirm IMDSv2 (Require) on the instance; relevant if you ever
  containerise (IMDSv2 hop limit).
- **Monitoring:** CloudWatch publishes
  ``IamDbAuthConnectionRequests`` / ``IamDbAuthConnectionSuccess`` /
  ``IamDbAuthConnectionFailure`` — alarm on any failure.
- **Snapshots:** restores inherit the IAM-auth setting; no action needed.
- **Network posture:** ``PubliclyAccessible`` should be ``false`` (for a
  VPC-resident instance that is a one-parameter
  ``modify-db-instance --no-publicly-accessible`` change), and 5432
  reachable only from the app security groups — never ``0.0.0.0/0``
  (leftover "for DMS migration"-style rules are a common finding and
  should be revoked). Remember the shared-instance caveat when changing
  anything network-level.
- **Future move to ECS/EKS:** replace the instance profile with a task
  role / service account carrying the same policy.

Known limits and pitfalls
-------------------------

- **Token expiry (15 min) is a non-issue** for established connections,
  but connection churn (e.g. ``CONN_MAX_AGE = 0`` with many workers)
  multiplies token minting and IAM-auth connection attempts. Keep
  ``CONN_MAX_AGE`` sensible.
- **Connection-rate ceiling:** RDS historically capped new IAM-auth
  connections at ~200/second; as of June 2026 the rate scales with
  instance resources. On the smallest instance classes expect the
  traditional low ceiling.
- **``NoRegionError``** → set ``AWS_DEFAULT_REGION`` in the app ``.env``
  (see the warning above).
- **``aws:SourceVpc`` and friends are unsupported** for ``rds-db`` —
  adding them breaks every connection (see the Phase 1 warning).
- **Instance profile ≠ role** for ``associate-iam-instance-profile``.
- **``psql`` is not preinstalled** anywhere by default.
- **``sslmode=require``** encrypts without verifying; move to
  ``verify-full`` with the truststore PEM for the stronger posture.
