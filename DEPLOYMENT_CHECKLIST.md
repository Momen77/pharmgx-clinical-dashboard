# Streamlit Cloud Deployment Checklist

## ✅ Completed Steps

### 1. Environment Configuration
- [x] Updated `environment.yml` with all dashboard dependencies (streamlit, reportlab, Pillow, plotly, qrcode)
- [x] Created `requirements.txt` for pip-based installation (fallback)
- [x] Streamlit dependencies are in both files

### 2. Streamlit Configuration
- [x] Created `.streamlit/config.toml` with UGent theme colors
- [x] Created `.streamlit/credentials.toml`
- [x] Created `.streamlit/secrets.toml.example` for API keys

### 3. Entry Point
- [x] Created root-level `app.py` that imports from `src/dashboard/app.py`
- [x] Properly configured Python path for imports

### 4. Dashboard Components
- [x] All dashboard modules exist:
  - `src/dashboard/app.py` - Main application
  - `src/dashboard/patient_creator.py` - Patient form
  - `src/dashboard/gene_panel_selector.py` - Gene selection
  - `src/dashboard/alert_classifier.py` - Alert classification
  - `src/dashboard/utils/styling.py` - UGent CSS

## ⚠️ Potential Issues & Solutions

### Issue: `streamlit: command not found`
**Cause:** Streamlit Cloud may not be installing pip dependencies from environment.yml correctly.

**Solution 1:** Use `requirements.txt` instead
- Update `requirements.txt` to include ALL dependencies
- Streamlit Cloud prefers this file for pip installations

**Solution 2:** Check environment activation
- Ensure the file says `environment.yml` (not `environment.yaml`)
- Verify Streamlit Cloud is using conda properly

### Issue: Import errors after deployment
**Cause:** Path issues with module imports.

**Solution:** The current `app.py` adds `src` to sys.path, which should work.

### Issue: Missing data files
**Cause:** The dashboard may try to access config.yaml or data files not in the repository.

**Solution:** 
- Ensure `config.yaml` exists in the repository root
- Add data files to `.gitignore` if they're large
- Use environment variables for API keys instead

## 📋 Deployment Steps

1. **Push to GitHub**
   ```bash
   git add src/pharmgx-clinical-dashboard/
   git commit -m "Add Streamlit dashboard deployment files"
   git push origin main
   ```

2. **Deploy on Streamlit Cloud**
   - Go to https://share.streamlit.io
   - Click "New app"
   - Connect your GitHub repository
   - Set:
     - **Main file path:** `app.py` or `src/dashboard/app.py`
     - **Python version:** 3.11
     - **Branch:** main

3. **Configure Secrets (optional)**
   - In Streamlit Cloud UI, go to "Secrets"
   - Add API keys from `config.yaml`:
     - `ncbi_email`
     - `ncbi_api_key`
     - `bioportal_api_key`

4. **Deploy & Test**
   - Click "Deploy"
   - Wait for build to complete
   - Test each page of the dashboard
   - Check logs for any errors

## 🔍 Troubleshooting

### Error: ModuleNotFoundError
- Check that all dependencies are in `requirements.txt`
- Verify Python path in `app.py`
- Check Streamlit Cloud logs for detailed errors

### Error: Streamlit command not found
- Use `requirements.txt` instead of `environment.yml`
- Or switch to pip-based deployment in Streamlit Cloud settings

### Error: API key errors
- Add API keys to Streamlit Cloud secrets
- Update code to read from `st.secrets` instead of `config.yaml`

## 📝 Files Summary

```
pharmgx-clinical-dashboard/
├── app.py                      # Entry point (deployment)
├── requirements.txt            # All dependencies (deployment)
├── environment.yml             # Conda environment
├── config.yaml                 # Configuration & API keys
├── .streamlit/                 # Streamlit configuration
│   ├── config.toml            # UI settings
│   ├── credentials.toml        # Credentials
│   └── secrets.toml.example   # API keys template
├── src/
│   ├── main.py                 # PGx pipeline
│   └── dashboard/
│       ├── app.py              # Main dashboard app
│       ├── patient_creator.py
│       ├── gene_panel_selector.py
│       ├── alert_classifier.py
│       └── utils/
│           └── styling.py
└── README_DEPLOYMENT.md       # This file
```

## 🚀 Expected Behavior

After deployment, you should see:
1. UGent-themed Streamlit dashboard
2. Navigation sidebar with 6 pages
3. Ability to create patient profiles
4. Gene panel selection interface
5. Test execution (requires full pipeline)
6. Results viewing and export

## 📞 Next Steps

1. Test locally: `streamlit run app.py` (from pharmgx-clinical-dashboard directory)
2. Push to GitHub
3. Deploy on Streamlit Cloud
4. Monitor logs for issues
5. Iterate based on feedback

