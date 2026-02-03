# Language & Internationalization (i18n) Implementation

## Overview

The East Africa Flood Watch system supports multiple languages for the East African region. This document describes the complete implementation of internationalization.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LANGUAGE SYSTEM                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Django     │    │   Wagtail    │    │    Translation       │  │
│  │   i18n       │◄──►│   CMS        │◄──►│    Files (.po)       │  │
│  │   Framework  │    │   Settings   │    │                      │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                   │                      │                │
│         ▼                   ▼                      ▼                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    Context Processor                          │  │
│  │              (language_context function)                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                │
│         ▼                    ▼                    ▼                │
│  ┌────────────┐      ┌────────────┐      ┌────────────────┐       │
│  │  Navbar    │      │  Templates │      │   Mapviewer    │       │
│  │  Language  │      │  {% trans  │      │   (Future)     │       │
│  │  Switcher  │      │   %}       │      │                │       │
│  └────────────┘      └────────────┘      └────────────────┘       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Supported Languages

| Code | Language | Region |
|------|----------|--------|
| `en` | English | Kenya, Uganda, South Sudan |
| `sw` | Swahili (Kiswahili) | Kenya, Uganda, Tanzania |
| `ar` | Arabic (العربية) | Sudan, South Sudan, Somalia, Djibouti, Eritrea |
| `am` | Amharic (አማርኛ) | Ethiopia |
| `fr` | French (Français) | Djibouti |
| `so` | Somali (Soomaali) | Somalia |
| `om` | Oromo (Oromoo) | Ethiopia |
| `ti` | Tigrinya (ትግርኛ) | Eritrea, Ethiopia |
| `pt` | Portuguese (Português) | (Optional) |
| `es` | Spanish (Español) | (Optional) |

---

## Implementation Details

### 1. Django Settings Configuration

**File:** `geomanagerweb/settings/base.py`

```python
# Internationalization
from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = "en"  # Default language

# Supported languages
LANGUAGES = [
    ("en", _("English")),
    ("sw", _("Swahili")),
    ("ar", _("العربية")),
    ("am", _("አማርኛ")),
    ("fr", _("Français")),
    ("so", _("Soomaali")),
    ("om", _("Oromoo")),
    ("ti", _("ትግርኛ")),
]

# Wagtail content languages (same as LANGUAGES)
WAGTAIL_CONTENT_LANGUAGES = LANGUAGES

# Enable Wagtail internationalization
WAGTAIL_I18N_ENABLED = True

# Locale paths - where translation files are stored
LOCALE_PATHS = [
    BASE_DIR / "locale",
    BASE_DIR / "home" / "locale",
]

# Middleware for language detection
MIDDLEWARE = [
    # ... other middleware
    'django.middleware.locale.LocaleMiddleware',  # Must be after SessionMiddleware
    # ... other middleware
]
```

---

### 2. URL Configuration for Language Switching

**File:** `geomanagerweb/urls.py`

```python
from django.conf.urls.i18n import i18n_patterns
from django.urls import path, include

urlpatterns = [
    # Language switching endpoint
    path('i18n/', include('django.conf.urls.i18n')),

    # ... other URLs
]

# Optionally wrap URLs with i18n_patterns for URL-based language
# urlpatterns += i18n_patterns(
#     path('', include('home.urls')),
# )
```

---

### 3. CMS Language Settings Model

**File:** `home/models.py`

```python
from django.db import models
from django.utils.translation import gettext_lazy as _
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel
from wagtail.contrib.settings.models import BaseGenericSetting, register_setting
from wagtail.models import Orderable
from modelcluster.models import ClusterableModel
from modelcluster.fields import ParentalKey

# Available language choices
LANGUAGE_CHOICES = [
    ("en", _("English")),
    ("sw", _("Swahili")),
    ("ar", _("العربية (Arabic)")),
    ("am", _("አማርኛ (Amharic)")),
    ("fr", _("Français (French)")),
    ("so", _("Soomaali (Somali)")),
    ("om", _("Oromoo (Oromo)")),
    ("ti", _("ትግርኛ (Tigrinya)")),
    ("pt", _("Português (Portuguese)")),
    ("es", _("Español (Spanish)")),
]


class EnabledLanguage(Orderable):
    """Individual enabled language for the site."""

    language_setting = ParentalKey(
        "home.LanguageSettings",
        on_delete=models.CASCADE,
        related_name="enabled_languages",
    )

    language_code = models.CharField(
        max_length=10,
        choices=LANGUAGE_CHOICES,
        verbose_name=_("Language"),
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name=_("Default Language"),
        help_text=_("Check if this is the default site language"),
    )

    panels = [
        FieldPanel("language_code"),
        FieldPanel("is_default"),
    ]

    class Meta:
        ordering = ["sort_order"]
        verbose_name = _("Enabled Language")
        verbose_name_plural = _("Enabled Languages")


@register_setting
class LanguageSettings(ClusterableModel, BaseGenericSetting):
    """
    CMS-configurable language settings.
    Admins can enable/disable languages for the site.
    """

    panels = [
        MultiFieldPanel(
            [
                InlinePanel(
                    "enabled_languages",
                    label=_("Enabled Language"),
                    min_num=1,
                ),
            ],
            heading=_("Site Languages"),
            help_text=_("Add languages available on the site. Mark one as default."),
        ),
    ]

    class Meta:
        verbose_name = _("Language Settings")
        verbose_name_plural = _("Language Settings")

    def get_enabled_languages(self):
        """Return list of (code, name) tuples for enabled languages."""
        return [
            (lang.language_code, dict(LANGUAGE_CHOICES).get(lang.language_code, lang.language_code))
            for lang in self.enabled_languages.all()
        ]

    def get_default_language(self):
        """Return the default language code."""
        default = self.enabled_languages.filter(is_default=True).first()
        return default.language_code if default else "en"
```

---

### 4. Context Processor

**File:** `home/context_processors.py`

```python
from django.core.cache import cache
from django.utils.translation import get_language
from .models import LanguageSettings


def language_context(request):
    """Load enabled languages from CMS settings."""
    enabled_languages = cache.get("enabled_languages")

    if enabled_languages is None:
        try:
            lang_settings = LanguageSettings.objects.first()
            if lang_settings:
                enabled_languages = lang_settings.get_enabled_languages()
            else:
                enabled_languages = [("en", "English")]
            cache.set("enabled_languages", enabled_languages, 60 * 60)  # Cache 1 hour
        except Exception:
            enabled_languages = [("en", "English")]

    return {
        "cms_languages": enabled_languages,
        "current_language": get_language() or "en",
    }
```

**Register in settings:**

```python
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                # ... other processors
                'home.context_processors.language_context',
            ],
        },
    },
]
```

---

### 5. Language Switcher Template

**File:** `home/templates/partials/language_switcher.html`

```html
{% load i18n %}

<div class="language-switcher">
  <div class="language-dropdown-wrapper">
    <button class="language-dropdown-trigger" aria-label="{% trans 'Select language' %}">
      <svg class="globe-icon" width="18" height="18" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
        <ellipse cx="12" cy="12" rx="4" ry="10" stroke="currentColor" stroke-width="2"/>
        <path d="M2 12h20" stroke="currentColor" stroke-width="2"/>
      </svg>
      <span class="current-lang">{{ current_language|upper }}</span>
      <svg class="dropdown-arrow" width="10" height="10" viewBox="0 0 12 12">
        <path d="M2 4L6 8L10 4" stroke="currentColor" stroke-width="2"/>
      </svg>
    </button>
    <div class="language-dropdown-menu">
      {% for lang_code, lang_name in cms_languages %}
        <a href="#"
           class="language-dropdown-item {% if lang_code == current_language %}is-active{% endif %}"
           data-lang="{{ lang_code }}">
          {{ lang_name }}
        </a>
      {% endfor %}
    </div>
  </div>
</div>

<script>
document.addEventListener("DOMContentLoaded", function() {
  const langItems = document.querySelectorAll(".language-dropdown-item");

  langItems.forEach(function(item) {
    item.addEventListener("click", function(e) {
      e.preventDefault();
      const lang = this.getAttribute("data-lang");

      // Submit to Django's set_language view
      const form = document.createElement("form");
      form.method = "POST";
      form.action = "/i18n/setlang/";

      const csrfInput = document.createElement("input");
      csrfInput.type = "hidden";
      csrfInput.name = "csrfmiddlewaretoken";
      csrfInput.value = getCookie("csrftoken");

      const langInput = document.createElement("input");
      langInput.type = "hidden";
      langInput.name = "language";
      langInput.value = lang;

      const nextInput = document.createElement("input");
      nextInput.type = "hidden";
      nextInput.name = "next";
      nextInput.value = window.location.pathname;

      form.appendChild(csrfInput);
      form.appendChild(langInput);
      form.appendChild(nextInput);
      document.body.appendChild(form);
      form.submit();
    });
  });

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
});
</script>
```

---

## Translation Files

### Directory Structure

```
geomanager-web/
├── locale/                          # Project-wide translations
│   ├── sw/
│   │   └── LC_MESSAGES/
│   │       ├── django.po           # Swahili translations
│   │       └── django.mo           # Compiled translations
│   ├── ar/
│   │   └── LC_MESSAGES/
│   │       ├── django.po
│   │       └── django.mo
│   ├── am/
│   │   └── LC_MESSAGES/
│   │       ├── django.po
│   │       └── django.mo
│   └── fr/
│       └── LC_MESSAGES/
│           ├── django.po
│           └── django.mo
│
└── home/
    └── locale/                      # App-specific translations
        ├── sw/
        │   └── LC_MESSAGES/
        │       ├── django.po
        │       └── django.mo
        └── ...
```

### Creating Translation Files

```bash
# 1. Mark strings for translation in code/templates
#    Python: from django.utils.translation import gettext_lazy as _
#            message = _("Hello World")
#    Template: {% load i18n %} {% trans "Hello World" %}

# 2. Extract translatable strings
python manage.py makemessages -l sw  # Swahili
python manage.py makemessages -l ar  # Arabic
python manage.py makemessages -l am  # Amharic
python manage.py makemessages -l fr  # French

# 3. Edit the .po files with translations

# 4. Compile translations
python manage.py compilemessages
```

### Example .po File

**File:** `locale/sw/LC_MESSAGES/django.po`

```po
# Swahili translations for East Africa Flood Watch
# Copyright (C) 2024 ICPAC
# This file is distributed under the same license as the EAFW package.
#
msgid ""
msgstr ""
"Project-Id-Version: EAFW 1.0\n"
"Report-Msgid-Bugs-To: \n"
"POT-Creation-Date: 2024-01-01 00:00+0000\n"
"PO-Revision-Date: 2024-01-01 00:00+0000\n"
"Last-Translator: ICPAC Team\n"
"Language-Team: Swahili\n"
"Language: sw\n"
"MIME-Version: 1.0\n"
"Content-Type: text/plain; charset=UTF-8\n"
"Content-Transfer-Encoding: 8bit\n"
"Plural-Forms: nplurals=2; plural=(n != 1);\n"

#: home/templates/partials/navbar.html:55
msgid "Select language"
msgstr "Chagua lugha"

#: home/models.py:xxx
msgid "Language"
msgstr "Lugha"

#: home/models.py:xxx
msgid "Default Language"
msgstr "Lugha ya Msingi"

#: templates/home/home_page.html:xxx
msgid "Welcome"
msgstr "Karibu"

#: templates/home/home_page.html:xxx
msgid "Flood Watch"
msgstr "Uangalizi wa Mafuriko"

#: templates/home/home_page.html:xxx
msgid "Climate Information"
msgstr "Taarifa za Hali ya Hewa"

#: templates/home/home_page.html:xxx
msgid "Reports"
msgstr "Ripoti"
```

---

## Auto-Download Translation Updates

### Management Command for Auto-Download

**File:** `home/management/commands/sync_translations.py`

```python
"""
Management command to auto-download and sync translations from a remote source.
Can be integrated with translation services like Transifex, Crowdin, or custom API.
"""

import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Sync translations from remote translation service'

    # Configuration - update with your translation service
    TRANSLATION_API_URL = os.environ.get(
        'TRANSLATION_API_URL',
        'https://your-translation-service.com/api/v1'
    )
    TRANSLATION_API_KEY = os.environ.get('TRANSLATION_API_KEY', '')

    SUPPORTED_LANGUAGES = ['sw', 'ar', 'am', 'fr', 'so', 'om', 'ti']

    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            '-l',
            type=str,
            help='Specific language code to sync (e.g., sw, ar)',
        )
        parser.add_argument(
            '--compile',
            action='store_true',
            help='Compile messages after download',
        )

    def handle(self, *args, **options):
        languages = [options['language']] if options['language'] else self.SUPPORTED_LANGUAGES

        for lang_code in languages:
            self.stdout.write(f'Syncing translations for: {lang_code}')

            try:
                self.download_translations(lang_code)
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Downloaded {lang_code} translations')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ Failed to download {lang_code}: {e}')
                )

        if options['compile']:
            self.stdout.write('Compiling messages...')
            call_command('compilemessages')
            self.stdout.write(self.style.SUCCESS('✓ Messages compiled'))

    def download_translations(self, lang_code):
        """Download translation file for a specific language."""

        # Option 1: Download from custom API
        if self.TRANSLATION_API_URL and self.TRANSLATION_API_KEY:
            response = requests.get(
                f'{self.TRANSLATION_API_URL}/translations/{lang_code}/django.po',
                headers={'Authorization': f'Bearer {self.TRANSLATION_API_KEY}'},
                timeout=30
            )
            response.raise_for_status()

            # Save to locale directory
            locale_dir = settings.BASE_DIR / 'locale' / lang_code / 'LC_MESSAGES'
            locale_dir.mkdir(parents=True, exist_ok=True)

            po_file = locale_dir / 'django.po'
            po_file.write_text(response.text, encoding='utf-8')

            return True

        # Option 2: Copy from shared network location
        # shared_path = Path('/shared/translations') / lang_code / 'django.po'
        # if shared_path.exists():
        #     shutil.copy(shared_path, locale_dir / 'django.po')

        # Option 3: Pull from Git repository
        # subprocess.run(['git', 'pull'], cwd=translations_repo_path)

        return False
```

### Celery Task for Scheduled Sync

**File:** `home/tasks.py` (add to existing file)

```python
from celery import shared_task
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@shared_task
def sync_translations_task():
    """
    Celery task to sync translations from remote service.
    Schedule this to run periodically (e.g., daily).
    """
    try:
        call_command('sync_translations', '--compile')
        logger.info('Translation sync completed successfully')
        return {'status': 'success'}
    except Exception as e:
        logger.error(f'Translation sync failed: {e}')
        return {'status': 'error', 'message': str(e)}
```

### Celery Beat Schedule

**File:** `geomanagerweb/celery.py` (add to beat schedule)

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # ... other schedules

    'sync-translations-daily': {
        'task': 'home.tasks.sync_translations_task',
        'schedule': crontab(hour=2, minute=0),  # Run at 2 AM daily
    },
}
```

---

## Using Translations in Code

### Python Files

```python
from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext, ngettext

# Model fields
class MyModel(models.Model):
    title = models.CharField(
        max_length=100,
        verbose_name=_("Title"),
        help_text=_("Enter the title"),
    )

# Views
def my_view(request):
    message = gettext("Welcome to Flood Watch")

    # Pluralization
    count = 5
    message = ngettext(
        "%(count)d alert",
        "%(count)d alerts",
        count
    ) % {'count': count}
```

### Django Templates

```html
{% load i18n %}

{# Simple translation #}
<h1>{% trans "Welcome" %}</h1>

{# Translation with context #}
<p>{% trans "Read more" context "link text" %}</p>

{# Block translation for longer text #}
{% blocktrans %}
  This is a longer piece of text that needs translation.
{% endblocktrans %}

{# With variables #}
{% blocktrans with name=user.name %}
  Hello, {{ name }}!
{% endblocktrans %}

{# Pluralization #}
{% blocktrans count counter=alert_count %}
  There is {{ counter }} alert.
{% plural %}
  There are {{ counter }} alerts.
{% endblocktrans %}
```

---

## Mapviewer (React/Next.js) i18n

The mapviewer currently does not have full i18n support. To implement:

### Option 1: next-i18next (Recommended)

```bash
cd geomapviewer
npm install next-i18next react-i18next i18next
```

**File:** `next-i18next.config.js`

```javascript
module.exports = {
  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'sw', 'ar', 'am', 'fr'],
  },
  localePath: './public/locales',
};
```

**File:** `public/locales/en/common.json`

```json
{
  "mapviewer": "Map Viewer",
  "legend": "Legend",
  "layers": "Layers",
  "search": "Search",
  "alert_levels": {
    "normal": "Normal",
    "warning": "Warning",
    "alarm": "Alarm",
    "emergency": "Emergency"
  }
}
```

### Option 2: Fetch from CMS API

```javascript
// Fetch translations from Django backend
const fetchTranslations = async (locale) => {
  const response = await fetch(`/api/translations/${locale}/`);
  return response.json();
};
```

---

## Docker Setup

**File:** `docker-compose.yml` (environment variables)

```yaml
services:
  geomanager_web:
    environment:
      - TRANSLATION_API_URL=${TRANSLATION_API_URL:-}
      - TRANSLATION_API_KEY=${TRANSLATION_API_KEY:-}
```

---

## Quick Reference Commands

```bash
# Extract all translatable strings
python manage.py makemessages -a

# Extract for specific languages
python manage.py makemessages -l sw -l ar -l am -l fr

# Compile translations
python manage.py compilemessages

# Sync from remote (custom command)
python manage.py sync_translations --compile

# Clear language cache
python manage.py shell -c "from django.core.cache import cache; cache.delete('enabled_languages')"
```

---

## Troubleshooting

### Common Issues

1. **Translations not showing:**
   - Check `LocaleMiddleware` is in MIDDLEWARE
   - Verify `.mo` files exist (run `compilemessages`)
   - Clear cache: `cache.delete('enabled_languages')`

2. **Language not switching:**
   - Ensure `django.conf.urls.i18n` is in urlpatterns
   - Check CSRF token is being sent

3. **RTL languages (Arabic) not displaying correctly:**
   - Add `dir="rtl"` to HTML when language is Arabic
   - Use CSS `direction: rtl` for Arabic content

---

## Adding a New Language

1. Add to `LANGUAGES` in settings
2. Add to `LANGUAGE_CHOICES` in models
3. Create locale directory: `mkdir -p locale/{code}/LC_MESSAGES`
4. Run: `python manage.py makemessages -l {code}`
5. Translate the `.po` file
6. Run: `python manage.py compilemessages`
7. Enable in CMS: Settings > Language Settings
