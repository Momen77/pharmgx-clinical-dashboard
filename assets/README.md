# Assets Directory

This directory contains logo files and other static assets for the Pharmacogenomics Clinical Dashboard.

## Logo Files

### Official UGent Logos (Current)

The dashboard now uses **official Ghent University logos**:

1. **`ugent_faculty_logo.png`** (Primary) - Faculty of Pharmaceutical Sciences logo
   - High resolution (2400px width)
   - RGB color variant for digital use
   - Used in: Sidebar, Home page, PDF reports

2. **`ugent_main_logo.png`** (Fallback) - Main Ghent University logo
   - High resolution (2400px width)
   - RGB color variant for digital use

3. **`ugent_logo.svg`** (Legacy) - Custom simplified logo
   - Simplified logo using official UGent colors
   - Primary Blue: `#1E64C8`, Secondary Yellow: `#FFD200`
   - Used as final fallback if official logos are missing

---

## Replacing with Official Logo

If you have access to the official Ghent University logo, you can replace the current logo:

### Option 1: Download Official Logo from Wikimedia Commons

1. Visit the official logo page:
   - **English version**: https://commons.wikimedia.org/wiki/File:University_Ghent_logo.svg
   - **Dutch version**: https://commons.wikimedia.org/wiki/File:Universiteit_Gent_logo.svg

2. Click "Download" or right-click on the logo image and save as

3. Save the file as `ugent_logo.svg` or `ugent_logo.png` in this directory

### Option 2: Download from Official UGent Style Guide

1. Visit the official Ghent University style guide:
   https://styleguide.ugent.be/basic-principles/logos-and-faculty-icons.html

2. Download the appropriate logo variant (preferably the English "Ghent University" version)

3. Save the file in this directory as `ugent_logo.svg` or `ugent_logo.png`

### Option 3: Contact UGent Communications

For official use, contact Ghent University's communications department to obtain the official logo files.

---

## Logo Usage

The dashboard uses a **priority-based logo loading system**:

1. **First Priority**: `ugent_faculty_logo.png` - Official Faculty of Pharmaceutical Sciences logo
2. **Second Priority**: `ugent_main_logo.png` - Official main UGent logo
3. **Third Priority**: `ugent_logo.svg` - Custom simplified logo
4. **Final Fallback**: Embedded SVG (if all files are missing)

### Where Logos Appear

- **Sidebar**: Displays faculty logo with "Pharmacogenomics Laboratory" subtitle
- **Home Page**: Large faculty logo with institution name in header
- **PDF Reports**: Faculty logo on cover page with full institution details
- **All pages**: Consistent branding throughout the application

---

## Supported Formats

- **PNG** (Current - high-resolution raster images, 2400px width)
- **SVG** (Supported - scalable vector graphics)

**Current Files**:
- `ugent_faculty_logo.png` - Faculty of Pharmaceutical Sciences (61 KB)
- `ugent_main_logo.png` - Main university logo (45 KB)
- `ugent_logo.svg` - Custom simplified logo (692 bytes)

---

## Logo Copyright

⚠️ **Important**: All logo variants of Ghent University are copyrighted and should only be used when there is a direct link to Ghent University.

Please ensure you have proper authorization to use the official logo for your intended purpose.

---

## Technical Details

### Current Logo Specifications

- **Dimensions**: 400 × 100 px (viewBox)
- **Format**: SVG
- **Colors**:
  - Background: Ghent University Blue (#1E64C8)
  - Accent bar: Ghent University Yellow (#FFD200)
  - Text: White (#FFFFFF) and Yellow (#FFD200)
- **Fonts**: Arial, Helvetica, sans-serif

### Official Logo Specifications

From UGent Style Guide:
- Available in both Dutch ('Universiteit Gent') and English ('Ghent University')
- Both language variants have equal worth
- Standard format: SVG (vector)
- Typical dimensions: 142 × 113 px (nominal for SVG)
- File size: ~8 KB (SVG)

---

## Additional Assets

You can add other assets to this directory:
- Faculty icons
- Department logos
- Custom graphics
- Icons

Make sure to document any additional assets in this README.

---

## Source of Official Logos

The official UGent logos in this directory were sourced from:
- **Location**: `logo_UGent_EN/` directory (project root)
- **Variant**: RGB 2400px color-on-white PNG files
- **Official**: Compliant with UGent branding guidelines

---

**Last Updated**: 2025-10-30
**Status**: ✅ Official UGent logos integrated
**Maintained by**: Pharmacogenomics Dashboard Team
