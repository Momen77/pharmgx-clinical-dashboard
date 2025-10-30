# Assets Directory

This directory contains logo files and other static assets for the Pharmacogenomics Clinical Dashboard.

## Logo Files

### Official UGent Logos (Current)

The dashboard uses **official Ghent University logos** with proper transparent backgrounds:

1. **`ugent_main_logo.png`** (Primary) - Main Ghent University logo
   - **Format**: PNG with RGBA transparency
   - **Resolution**: 3543 × 2835 px (high resolution)
   - **Background**: Transparent
   - **Colors**: UGent Blue (#1E64C8) and Yellow (#FFD200)
   - **Usage**: Light backgrounds (white, light gray)
   - **File size**: 55 KB
   - **Used in**: Sidebar, Home page, PDF reports

2. **`ugent_white_logo.png`** (Alternative) - White variant
   - **Format**: PNG with RGBA transparency
   - **Resolution**: 3543 × 2835 px
   - **Background**: Transparent
   - **Colors**: White logo for dark backgrounds
   - **Usage**: Dark or colored backgrounds
   - **File size**: 60 KB
   - **Reserved for**: Future dark mode or colored backgrounds

3. **`ugent_logo.svg`** (Fallback) - Custom simplified logo
   - **Format**: SVG (scalable vector)
   - **Background**: Transparent
   - **Colors**: UGent Blue (#1E64C8) text, Yellow (#FFD200) accent
   - **Usage**: Fallback if PNG files missing
   - **File size**: <1 KB

### ⚠️ Logo Usage Guidelines (UGent Style Guide)

Based on official Ghent University branding:

**✅ DO:**
- Use color logo on white or light backgrounds
- Use white logo on dark or colored backgrounds
- Maintain clear space around the logo
- Keep proportions intact
- Use provided file formats (PNG with transparency)

**❌ DON'T:**
- Use color logo on dark backgrounds
- Use white logo on light backgrounds
- Add backgrounds to transparent logos
- Distort, rotate, or modify the logo
- Use low-resolution versions
- Combine with other logos without permission

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

## Logo Usage in Application

The dashboard uses a **priority-based logo loading system** with proper transparency:

1. **First Priority**: `ugent_main_logo.png` - Official main UGent logo (RGBA transparent)
2. **Second Priority**: `ugent_logo.svg` - Custom simplified logo (transparent SVG)
3. **Final Fallback**: Embedded SVG with transparent background

### Current Implementation

**Background Handling:**
- All logos have **transparent backgrounds**
- Logos adapt to their container's background color
- Color logo used on light backgrounds (Streamlit's default light gray sidebar)
- White logo available for future dark mode implementation

**Where Logos Appear:**
- **Sidebar**: Main UGent logo (transparent, adapts to sidebar background)
- **Home Page**: Main UGent logo (150px width)
- **PDF Reports**: Main UGent logo on cover page
- **All Pages**: Consistent transparent branding throughout

---

## Supported Formats

The application supports multiple logo formats with transparency:

**Current Files:**
- **`ugent_main_logo.png`** - Main logo (55 KB, 3543×2835px, RGBA transparent)
- **`ugent_white_logo.png`** - White variant (60 KB, 3543×2835px, RGBA transparent)
- **`ugent_logo.svg`** - Simplified vector (<1 KB, transparent background)

---

## Logo Copyright

⚠️ **Important**: All logo variants of Ghent University are copyrighted and should only be used when there is a direct link to Ghent University.

Please ensure you have proper authorization to use the official logo for your intended purpose.

---

## Technical Details

### Main Logo (PNG) Specifications

- **File**: `ugent_main_logo.png`
- **Format**: PNG with RGBA transparency
- **Dimensions**: 3543 × 2835 px
- **Color Mode**: RGBA (with alpha channel)
- **Background**: Transparent
- **Colors**: UGent Blue (#1E64C8), Yellow (#FFD200)
- **File Size**: 55 KB
- **DPI**: High resolution for print and digital use

### Simplified SVG Logo Specifications

- **File**: `ugent_logo.svg`
- **Format**: Scalable Vector Graphics (SVG)
- **ViewBox**: 400 × 100 px
- **Background**: Transparent (no background rect)
- **Colors**:
  - Text: Ghent University Blue (#1E64C8)
  - Accent bar: Ghent University Yellow (#FFD200)
- **Fonts**: Arial, Helvetica, sans-serif
- **File Size**: <1 KB

### Official UGent Logo Guidelines

From UGent Style Guide:
- Available in both Dutch ('Universiteit Gent') and English ('Ghent University')
- Both language variants have equal worth
- Use color variant on white/light backgrounds
- Use white variant on dark/colored backgrounds
- Maintain clear space around logo (minimum 10% of logo width)
- Do not modify, distort, or add effects to the logo

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
- **Location**: `logo_UGent_EN/logo_UGent_EN/` directory (project root)
- **Main Logo**: `logo_UGent_EN_RGB_2400_color.png` (RGBA transparent)
- **White Logo**: `logo_UGent_EN_RGB_2400_white.png` (RGBA transparent)
- **Official**: Compliant with UGent branding guidelines
- **Style Guide**: https://styleguide.ugent.be/basic-principles/logos-and-faculty-icons.html

### Logo Variants Available

The project includes the complete official UGent logo package in `logo_UGent_EN/`:
- Color variants (for light backgrounds) - ✅ Currently used
- White variants (for dark backgrounds) - Available
- EPS, CMYK, PANTONE, RGB formats - All available
- High resolution 2400px PNG files - ✅ Currently used

---

**Last Updated**: 2025-10-30
**Status**: ✅ Official UGent logos with transparent backgrounds integrated
**Compliant with**: UGent Style Guide (transparent, proper color usage)
**Maintained by**: Pharmacogenomics Dashboard Team
