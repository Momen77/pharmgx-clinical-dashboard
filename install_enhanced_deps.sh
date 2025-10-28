#!/bin/bash
# Install dependencies for the enhanced Streamlit dashboard

echo "Installing enhanced dashboard dependencies..."

# Install streamlit-lottie for animations
pip install streamlit-lottie>=0.0.5

echo "✅ Dependencies installed successfully!"
echo ""
echo "To run the enhanced dashboard:"
echo "1. Navigate to: src/pharmgx-clinical-dashboard/"
echo "2. Run: streamlit run app.py"
echo ""
echo "New features:"
echo "- Scripted lab→NGS→report animation"
echo "- User-created profile as base with enrichment modes"
echo "- Demo mode for testing UI"
echo "- Cancel button for long-running pipelines"
echo "- Enhanced results display"
