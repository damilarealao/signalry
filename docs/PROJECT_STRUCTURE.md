signalry/
├── README.md
│   Purpose:
│   - What Signalry is
│   - What it is NOT
│   - High-level usage and guarantees
│   - Privacy-first positioning

├── ROADMAP.md
│   Purpose:
│   - Phase-based development plan
│   - Feature sequencing
│   - Explicit “not yet” list

├── .env.example
│   Purpose:
│   - Environment variables contract
│   - Never contains secrets

├── .gitignore
│   Purpose:
│   - Keep garbage and secrets out of Git

├── docs/
│   ├── architecture.yaml
│   │   Purpose:
│   │   - Canonical system blueprint
│   │   - Source of truth for the entire project
│   │
│   ├── plans.md
│   │   Purpose:
│   │   - Free vs Premium definitions
│   │   - Limits, retention, queue priority
│   │
│   ├── privacy.md
│   │   Purpose:
│   │   - Data collection guarantees
│   │   - What is hashed, truncated, or never stored
│   │
│   ├── queues.md
│   │   Purpose:
│   │   - Celery + RabbitMQ behavior
│   │   - Retry rules, backoff, DLQ logic
│   │
│   ├── non_goals.md
│   │   Purpose:
│   │   - Explicitly rejected features
│   │   - Prevents scope creep and ad-tech nonsense
│   │
│   └── domain/
│       ├── users.md
│       │   Purpose:
│       │   - User lifecycle
│       │   - Isolation rules
│       │   - Permissions model
│       │
│       ├── smtp_accounts.md
│       │   Purpose:
│       │   - SMTP health logic
│       │   - Rotation rules
│       │   - Auto-disable behavior
│       │
│       ├── campaigns.md
│       │   Purpose:
│       │   - Campaign lifecycle
│       │   - Safeguards and rate limits
│       │
│       ├── messages.md
│       │   Purpose:
│       │   - Message states
│       │   - UUID rules
│       │   - Retry semantics
│       │
│       ├── message_opens.md
│       │   Purpose:
│       │   - Read tracking rules
│       │   - Privacy constraints
│       │   - Beacon behavior
│       │
│       └── email_validation.md
│           Purpose:
│           - Deliverability & SMTP validation
│           - Single & bulk endpoints
│           - Status: valid, invalid, unknown
│           - Domain type: free, premium, disposable
│           - Downloadable CSV
│           - Retention per plan
│           - Privacy-first: no IPs or timestamps

├── backend/
│   ├── manage.py
│   ├── config/
│   │   ├── settings/
│   │   │   - base.py, dev.py, prod.py
│   │   ├── urls.py
│   │   └── celery.py
│   ├── common/
│   │   ├── permissions.py
│   │   ├── rate_limits.py
│   │   ├── encryption.py
│   │   └── constants.py
│   └── apps/
│       ├── users/
│       ├── plans/
│       ├── smtp/
│       ├── campaigns/
│       ├── messages/
│       ├── tracking/
│       ├── email_validation/
│       │   Purpose:
│       │   - Deliverability module
│       │   - Single & bulk email validation
│       │   - Domain classification
│       │   - CSV download
│       │   - Retention per plan
│       │   - Privacy-first
│       ├── queues/
│       ├── analytics/
│       └── monitoring/

├── infra/
│   ├── docker/
│   ├── rabbitmq/
│   └── nginx/

└── scripts/
    ├── seed_dev_data.py
    └── maintenance_tasks.py
