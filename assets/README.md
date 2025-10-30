# Assets Directory

This directory contains logo files and other static assets for the Pharmacogenomics Clinical Dashboard.

## Logo Files

### Current Logo

**File**: `ugent_logo.svg`

This is a simplified logo using official Ghent University colors:
- **Primary Blue**: `#1E64C8`
- **Secondary Yellow**: `#FFD200`

The logo displays "GHENT UNIVERSITY" with "Pharmacogenomics Laboratory" subtitle.

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

The dashboard automatically:
1. **First** checks for `assets/ugent_logo.svg` or `assets/ugent_logo.png`
2. **Fallback** to the embedded simplified SVG logo if file not found

To use the official logo:
- Place your downloaded logo file in this directory as `ugent_logo.svg` or `ugent_logo.png`
- Restart the Streamlit dashboard
- The application will automatically use your logo

---

## Supported Formats

- **SVG** (Recommended - scalable vector graphics)
- **PNG** (Also supported - raster image)

**File naming**:
- `ugent_logo.svg` (preferred)
- `ugent_logo.png` (alternative)

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

**Last Updated**: 2025-10-30
**Maintained by**: Pharmacogenomics Dashboard Team
