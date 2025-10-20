# Automatic Language Switching Implementation

## Overview
This implementation enables automatic language switching for patients based on their preferred language setting. When a patient logs into the website, the system automatically switches to their preferred language using URL-based language prefixes (e.g., `/en/`, `/hi/`, `/bn/`).

## Components Modified/Created

### 1. **Patient Model** (`patientapp/models.py`)
- Already contains `preferred_language` field (lines 51-59)
- Uses `settings.LANGUAGES` for choices
- Defaults to `settings.LANGUAGE_CODE`
- Indexed for performance

### 2. **Patient Forms** (`patientapp/forms.py`)
#### PatientForm (for creating new patients)
- Added `preferred_language` to the `fields` list in Meta class (line 32)
- Added `preferred_language` field to the crispy forms layout (line 69)

#### PatientRestrictedUpdateForm (for updating existing patients)
- Added `preferred_language` to the `fields` list in Meta class (line 115)

### 3. **Custom Middleware** (`patientapp/middleware.py`) - **NEW FILE**
Created `PatientLanguageMiddleware` that:
- Runs after authentication middleware
- Checks if the logged-in user has an associated Patient profile
- Retrieves the patient's `preferred_language`
- Activates the preferred language using Django's translation system
- Stores the language preference in the session for persistence
- Redirects to the appropriate language-prefixed URL if necessary
- Handles edge cases (non-patient users, missing preferences, etc.)

**Key Features:**
- Only processes authenticated users
- Gracefully handles users without patient profiles
- Preserves query strings during redirects
- Avoids redirecting static/media/i18n URLs
- Comprehensive error logging

### 4. **Settings Configuration** (`chaviprom/settings.py`)
- Added `patientapp.middleware.PatientLanguageMiddleware` to MIDDLEWARE (line 96)
- Placed after `AuthenticationMiddleware` and `AccountMiddleware`
- Placed before `ClickjackingMiddleware` to ensure proper request processing

### 5. **Templates**

#### `templates/patientapp/patient_form.html`
- Added `{{ form.preferred_language|as_crispy_field }}` to display the language selection field (line 65)

#### `templates/patientapp/patient_restricted_update_form.html`
- Added `{{ form.preferred_language|as_crispy_field }}` to allow patients to update their language preference (line 35)

#### `templates/patientapp/patient_detail.html`
- Added display of preferred language using `c-field_display` component (lines 88-93)
- Shows language as a green badge for visual emphasis

## How It Works

### Patient Registration Flow:
1. Admin/Provider creates a new patient using the patient form
2. Selects the patient's preferred language from the dropdown
3. Patient record is saved with the preferred language

### Patient Login Flow:
1. Patient logs in using their credentials
2. `PatientLanguageMiddleware` detects the authenticated user
3. Middleware checks if user has a Patient profile
4. Retrieves the `preferred_language` from the patient record
5. Activates the language in Django's translation system
6. Stores language preference in the session
7. Redirects to the language-prefixed URL (e.g., `/en/` → `/hi/`)
8. All subsequent pages are displayed in the patient's preferred language

### Patient Update Flow:
1. Patient or provider navigates to patient detail page
2. Clicks "Edit Patient Details"
3. Can update the preferred language along with other fields
4. On next login or page refresh, the new language preference takes effect

## URL Structure

The application uses Django's `i18n_patterns` for language-based URLs:
- English: `https://example.com/en/patientapp/...`
- Hindi: `https://example.com/hi/patientapp/...`
- Bengali: `https://example.com/bn/patientapp/...`

The middleware automatically redirects users to the correct language prefix based on their preference.

## Configuration

Languages are configured in `settings.py`:
```python
LANGUAGES = [
    (code.strip(), _(name.strip()))
    for lang in language_settings.split(',')
    for code, name in [lang.split(':', 1)]
]
```

Set in `.env` file:
```
DJANGO_LANGUAGES=en:English,hi:Hindi,bn:Bengali
```

## Benefits

1. **Automatic**: No manual language switching required by patients
2. **Persistent**: Language preference is stored in the database and session
3. **User-Friendly**: Patients see the interface in their preferred language immediately upon login
4. **Flexible**: Patients can change their language preference at any time
5. **Secure**: Only authenticated patients can trigger language switching
6. **Performant**: Uses database indexing and session caching

## Testing

To test the implementation:

1. **Create a patient** with a specific preferred language (e.g., Hindi)
2. **Log out** and then **log in** as that patient
3. **Verify** that the URL changes to include the language prefix (e.g., `/hi/`)
4. **Verify** that all interface text is displayed in the preferred language
5. **Update** the patient's preferred language
6. **Refresh** the page or log in again to see the new language take effect

## Error Handling

The middleware includes comprehensive error handling:
- Logs all language switches for debugging
- Gracefully handles missing patient profiles
- Catches and logs unexpected errors without breaking the application
- Preserves normal functionality for non-patient users

## Future Enhancements

Potential improvements:
1. Add a language switcher widget for temporary language changes
2. Allow patients to change language without logging out
3. Add language preference to patient registration form
4. Support for right-to-left (RTL) languages
5. Language-specific content recommendations
