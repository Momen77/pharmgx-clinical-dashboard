# AI Patient Photo Generation Setup Guide

## Overview

The system can generate realistic AI-powered patient photos based on their complete profile including:
- **Demographics:** Age, gender, ethnicity, birthplace
- **Medical Conditions:** Multiple diseases show subtle tiredness
- **Emotional State:** Happy/sad/depressed based on health status
- **Character:** Subtle expressions that add realism and humanity

---

## 🎨 How It Works

### Prompt Generation
The system analyzes patient data and creates a detailed prompt:

**Example for a 55-year-old Asian female with 3 chronic conditions:**
```
Professional medical portrait photograph of a 55-year-old female patient
of Asian descent with East Asian features, neutral background, soft lighting,
facing camera, realistic photographic style, high quality, subtle tired
expression, showing signs of chronic illness, slight weariness in eyes but
maintaining dignity, gray hair, age lines, mature features, wearing casual
comfortable clothing, natural skin texture, realistic human features, NOT
illustration, NOT cartoon, NOT artwork, photorealistic medical record photo
```

### Emotional Mapping
| Condition Count | Expression | Details |
|----------------|------------|---------|
| 0 conditions | Healthy, slight smile | Positive demeanor |
| 1-2 conditions | Calm with hint of concern | Thoughtful expression |
| 3+ conditions | Subtle tiredness | Shows chronic illness impact |

---

## 🔑 API Setup

### Option 1: OpenAI DALL-E (Recommended)

**Pros:**
- High quality, photorealistic images
- Fast generation (20-40 seconds)
- Consistent results

**Cost:** ~$0.04 per image (1024x1024)

**Setup:**
1. Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set environment variable:
   ```bash
   export OPENAI_API_KEY="sk-..."
   ```
3. Or add to config.yaml:
   ```yaml
   ai_services:
     openai_api_key: "sk-..."
     photo_service: "openai"
   ```

### Option 2: Stability AI

**Pros:**
- Good quality
- Lower cost ($0.002 per image)
- Open source model

**Setup:**
1. Get API key from [Stability AI](https://platform.stability.ai/)
2. Set environment variable:
   ```bash
   export STABILITY_API_KEY="sk-..."
   ```
3. Or configure in code:
   ```python
   generator = AIPhotoGenerator(
       api_key="sk-...",
       service="stability"
   )
   ```

### Option 3: No API Key (Fallback)

If no API key is configured:
- **Automatic fallback to avatar generation**
- Shows colored circle with patient initials
- No additional cost
- Instant generation

---

## 📁 File Structure

```
src/
├── utils/
│   └── ai_photo_generator.py    # Core AI photo generation
└── dashboard/
    ├── patient_creator.py        # Integrates AI photo gen
    └── app.py                    # Displays generated photos
```

---

## 💻 Usage

### Manual Profile Creation
```python
# In Create Patient page form
# Select photo option at top:
# ⚪ Generate Avatar
# ⚪ Upload Photo
# ⚪ AI Generated  ← Fully functional with API key
```

When you select "AI Generated" and submit the form:
1. The system collects all patient data from the form
2. Builds a detailed AI prompt based on demographics and medical conditions
3. Generates a photorealistic portrait using OpenAI DALL-E or Stability AI
4. Displays the generated photo with success message
5. Automatically falls back to avatar if no API key is configured

### Auto-Generate Profile
```python
# Click "Generate Random Patient Profile"
# Automatically generates:
# 1. Random demographics
# 2. Medical conditions
# 3. AI-generated photo based on all above
```

### Programmatic Usage
```python
from utils.ai_photo_generator import AIPhotoGenerator

patient_data = {
    'demographics': {
        'age': 45,
        'gender': 'Female',
        'ethnicity': ['Hispanic/Latino'],
        'birth_country': 'Mexico'
    },
    'clinical_information': {
        'demographics': {
            'current_conditions': [
                {'name': 'Diabetes'},
                {'name': 'Hypertension'}
            ]
        }
    }
}

generator = AIPhotoGenerator(api_key="your-key", service="openai")
photo_bytes = generator.generate_patient_photo(patient_data)

# Save to file
with open('patient_photo.png', 'wb') as f:
    f.write(photo_bytes)
```

---

## 🎯 Prompt Customization

### Ethnicity Descriptions
The system maps ethnicities to visual descriptions:
```python
ethnicity_map = {
    'African': 'African descent with dark skin',
    'Asian': 'Asian descent with East Asian features',
    'Caucasian/European': 'European descent with fair skin',
    'Hispanic/Latino': 'Hispanic/Latino descent with olive skin',
    'Middle Eastern': 'Middle Eastern descent with tan skin',
    'Native American': 'Native American descent',
    'Pacific Islander': 'Pacific Islander descent',
    'Mixed': 'mixed ethnicity'
}
```

### Age-Based Details
```python
if age >= 60:
    prompt += "gray hair, age lines, mature features"
elif age >= 40:
    prompt += "middle-aged appearance, slight aging signs"
else:
    prompt += "youthful appearance"
```

### Condition-Based Expressions
```python
if condition_count >= 3:
    prompt += "subtle tired expression, showing signs of chronic illness"
    prompt += "slight weariness in eyes but maintaining dignity"
elif condition_count >= 1:
    prompt += "calm expression with hint of concern"
else:
    prompt += "healthy appearance, slight smile"
```

---

## 🧪 Testing

### Test Without API Key
```bash
# Will fallback to avatar
python src/utils/ai_photo_generator.py
# Output: ⚠️ No API key configured, using fallback avatar
```

### Test With OpenAI
```bash
export OPENAI_API_KEY="sk-..."
python src/utils/ai_photo_generator.py
# Output: ✅ Photo generated successfully with OpenAI DALL-E
```

### Test In Dashboard
1. Start Streamlit: `streamlit run src/dashboard/app.py`
2. Go to **Create Patient** page
3. Select **Auto-generate** mode
4. Click **Generate Random Patient Profile**
5. Watch for status:
   - ✅ With API: "✅ AI photo generated successfully!"
   - ⚠️ Without API: "⚠️ Using avatar fallback"

---

## 🔒 Security Notes

1. **Never commit API keys** to git
2. Use environment variables or secure config
3. Add to `.gitignore`:
   ```
   config.yaml
   .env
   *.key
   ```
4. For production, use secrets management:
   - AWS Secrets Manager
   - Azure Key Vault
   - HashiCorp Vault

---

## 💰 Cost Estimation

### OpenAI DALL-E
- **Price:** $0.04 per image (1024x1024)
- **100 patients:** $4.00
- **1,000 patients:** $40.00

### Stability AI
- **Price:** $0.002 per image (1024x1024)
- **100 patients:** $0.20
- **1,000 patients:** $2.00

### Recommendation
- **Development/Testing:** Use fallback avatar (free)
- **Production (high volume):** Use Stability AI
- **Production (best quality):** Use OpenAI DALL-E

---

## 🐛 Troubleshooting

### "No API key configured"
```bash
# Set environment variable
export OPENAI_API_KEY="your-key-here"

# Or check config.yaml exists
cat config.yaml | grep openai_api_key
```

### "API error: 401 Unauthorized"
- Check API key is correct
- Verify key has credits/quota
- Check key permissions

### "Generation timeout"
- Image generation can take 20-40 seconds
- Check network connection
- Try again (may be API rate limiting)

### Photo not displaying
```python
# Check photo format
profile = st.session_state.get('patient_profile', {})
print(f"Photo format: {profile.get('photo_format')}")
print(f"Photo size: {len(profile.get('photo', b''))} bytes")
```

---

## 🚀 Future Enhancements

1. **Multiple photo styles:** Medical ID, casual, professional
2. **Expression customization:** User can choose emotion
3. **Batch generation:** Generate photos for multiple patients
4. **Photo editing:** Adjust age, expression after generation
5. **Historical photos:** Generate younger/older versions
6. **Video avatars:** Animated talking patient avatars

---

## 📞 Questions?

For questions about AI photo generation:
- Check the code: `src/utils/ai_photo_generator.py`
- Review examples in this guide
- Test with the example patient data provided

**Remember:** Always respect patient privacy and use AI-generated photos ethically for testing/development purposes only.
