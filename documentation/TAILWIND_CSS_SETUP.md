# Tailwind CSS v4 Integration Guide

This project uses Tailwind CSS v4 compiled locally instead of the CDN for production-ready performance.

## Overview

Tailwind CSS is integrated using the official `@tailwindcss/cli` tool which compiles the CSS at build time, providing:
- **Better Performance**: Smaller CSS file size with only used utilities
- **Production Ready**: No CDN dependency
- **Faster Load Times**: Compiled CSS is cached by browsers
- **Offline Support**: Works without internet connection

## File Structure

```
chavi-prom/
├── package.json                    # NPM configuration with Tailwind scripts
├── static/
│   └── src/
│       ├── input.css              # Source CSS file (tracked in git)
│       └── output.css             # Compiled CSS (gitignored)
└── templates/
    └── base.html                  # References compiled output.css
```

## Setup Instructions

### Initial Setup (Already Done)

The following has already been configured:

1. **NPM Initialization**
   ```bash
   npm init -y
   ```

2. **Install Tailwind CSS v4**
   ```bash
   npm install tailwindcss @tailwindcss/cli
   ```

3. **Created Input CSS** (`static/src/input.css`)
   ```css
   @import "tailwindcss";
   ```

4. **Updated base.html**
   - Removed CDN script tag
   - Added link to compiled CSS: `{% static 'src/output.css' %}`

## Development Workflow

### During Development

Run the Tailwind CLI in watch mode to automatically recompile CSS when you make changes:

```bash
npm run tailwind:watch
```

This command will:
- Monitor your HTML templates for Tailwind class usage
- Automatically rebuild `static/src/output.css` when changes are detected
- Keep running in the background (keep this terminal open)

**Important**: Keep this running in a separate terminal while developing!

### Building for Production

Before deploying or committing changes, build the final CSS:

```bash
npm run tailwind:build
```

This creates an optimized `static/src/output.css` file.

## NPM Scripts

The following scripts are available in `package.json`:

- **`npm run tailwind:build`** - Build CSS once (for production)
- **`npm run tailwind:watch`** - Watch mode for development (auto-rebuild)

## Django Static Files

### Development
In development mode, Django serves static files directly from the `static/` directory.

### Production
For production deployment:

1. Build Tailwind CSS:
   ```bash
   npm run tailwind:build
   ```

2. Collect static files:
   ```bash
   python manage.py collectstatic
   ```

This copies `static/src/output.css` to `staticfiles/src/output.css` for serving.

## Git Configuration

The following files are tracked in git:
- ✅ `package.json` - NPM configuration
- ✅ `static/src/input.css` - Source CSS file

The following files are **gitignored**:
- ❌ `node_modules/` - NPM packages
- ❌ `package-lock.json` - NPM lock file
- ❌ `static/src/output.css` - Compiled CSS (regenerated on each machine)

## Customizing Tailwind

To add custom Tailwind configuration or extend the default theme:

1. Create a `tailwind.config.js` file in the project root
2. Add your custom configuration
3. Rebuild the CSS with `npm run tailwind:build`

Example `tailwind.config.js`:
```javascript
module.exports = {
  theme: {
    extend: {
      colors: {
        'brand-blue': '#0066cc',
      },
    },
  },
}
```

## Adding Custom CSS

To add custom CSS alongside Tailwind:

1. Edit `static/src/input.css`:
   ```css
   @import "tailwindcss";
   
   /* Your custom CSS here */
   .custom-class {
     /* custom styles */
   }
   ```

2. Rebuild: `npm run tailwind:build`

## Troubleshooting

### CSS Not Updating
- Make sure `npm run tailwind:watch` is running
- Check that you're using valid Tailwind classes
- Try rebuilding: `npm run tailwind:build`

### Styles Not Appearing
- Verify `static/src/output.css` exists
- Check Django static files configuration in `settings.py`
- Run `python manage.py collectstatic` for production

### Node Modules Missing
If you clone the repository on a new machine:
```bash
npm install
npm run tailwind:build
```

## Migration from CDN

This project was previously using Tailwind CSS from CDN. The migration involved:

1. ✅ Removed `<script src="https://cdn.tailwindcss.com"></script>`
2. ✅ Removed inline `tailwind.config` script
3. ✅ Added compiled CSS link: `<link rel="stylesheet" href="{% static 'src/output.css' %}">`
4. ✅ Set up NPM build process

## Resources

- [Tailwind CSS v4 Documentation](https://tailwindcss.com/docs/)
- [Tailwind CLI Documentation](https://tailwindcss.com/docs/installation)
- [Django Static Files Guide](https://docs.djangoproject.com/en/stable/howto/static-files/)

## Quick Reference

**Start development:**
```bash
# Terminal 1: Tailwind watch mode
npm run tailwind:watch

# Terminal 2: Django development server
python manage.py runserver
```

**Before deploying:**
```bash
npm run tailwind:build
python manage.py collectstatic
```
