"""
AI-Powered Patient Photo Generator
Generates realistic patient photos based on demographics and medical conditions
"""
import os
import base64
import requests
from typing import Dict, Optional
from pathlib import Path


class AIPhotoGenerator:
    """Generates realistic patient photos using AI"""

    def __init__(self, api_key: str = None, service: str = "gemini"):
        """
        Initialize photo generator

        Args:
            api_key: API key for the AI service
            service: Which service to use ("gemini", "openai", "stability")
        """
        # Choose API key based on selected service; allow explicit api_key to override
        if api_key:
            self.api_key = api_key
        else:
            if service == "gemini":
                self.api_key = os.getenv("GOOGLE_API_KEY")
            elif service == "openai":
                self.api_key = os.getenv("OPENAI_API_KEY")
            elif service == "stability":
                self.api_key = os.getenv("STABILITY_API_KEY")
            else:
                self.api_key = None
        self.service = service
        self.last_error: Optional[str] = None

    def generate_patient_photo(self, patient_data: Dict) -> Optional[bytes]:
        """
        Generate a patient photo based on their profile

        Args:
            patient_data: Dictionary with demographics and medical conditions

        Returns:
            Image bytes or None if generation fails
        """
        # Validate demographics readiness before building prompt
        demo = patient_data.get('demographics') if isinstance(patient_data, dict) else None
        if not isinstance(demo, dict) or not demo:
            self.last_error = "Invalid or missing demographics; aborted photo generation."
            print(f"⚠️ {self.last_error}")
            return None

        # Build detailed prompt from patient data
        prompt = self._build_prompt(patient_data)

        print(f"🎨 Generating patient photo...")
        print(f"📝 Prompt: {prompt[:200]}...")

        # Generate image using selected service
        if self.service == "gemini" and self.api_key:
            return self._generate_with_gemini(prompt)
        elif self.service == "openai" and self.api_key:
            return self._generate_with_openai(prompt)
        elif self.service == "stability" and self.api_key:
            return self._generate_with_stability(prompt)
        else:
            msg = "No API key configured, using fallback avatar"
            print(f"⚠️ {msg}")
            self.last_error = msg
            return None

    def _build_prompt(self, patient_data: Dict) -> str:
        """Build detailed prompt from patient data"""
        # Defensive fallback: always create prompt_parts as a last resort
        prompt_parts = ["Generic person, neutral facial features"]
        demo = patient_data.get('demographics', {})
        clinical = patient_data.get('clinical_information', {})
        try:
            # Extract key demographics with defensive type handling
            age = demo.get('age') or 45
            # Use biological_sex for photo generation (physical appearance), fall back to gender
            gender = demo.get('biological_sex') or demo.get('gender') or 'Male'
            ethnicity_raw = demo.get('ethnicity')
            if isinstance(ethnicity_raw, list) and len(ethnicity_raw) > 0:
                ethnicity = ethnicity_raw[0]
            elif isinstance(ethnicity_raw, str):
                ethnicity = ethnicity_raw
            else:
                ethnicity = 'Caucasian/European'
            birth_country = demo.get('birth_country') or ''
            # Normalize strings
            gender = str(gender) if gender else 'Male'
            ethnicity = str(ethnicity) if ethnicity else 'Caucasian/European'
            birth_country = str(birth_country) if birth_country else ''
            # Map ethnicity to description
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
            ethnicity_desc = ethnicity_map.get(ethnicity, 'mixed ethnicity')

            # Ethnicity/gender explicit facial feature descriptors (clinical defaults)
            ethn = ethnicity.lower()
            gender_str = gender.lower()
            face_block = None
            if 'middle eastern' in ethn or 'arab' in ethn:
                face_block = f"Middle Eastern {'woman' if gender_str == 'female' else 'man' if gender_str == 'male' else 'person'}, olive or tan skin, brown eyes, thick dark eyebrows, Middle Eastern facial features"
            elif 'asian' in ethn and ('east' in ethn or 'china' in birth_country.lower() or 'japan' in birth_country.lower() or 'korea' in birth_country.lower()):
                face_block = f"East Asian {'woman' if gender_str == 'female' else 'man' if gender_str == 'male' else 'person'}, pale or yellowish skin tone, almond-shaped eyes, straight black hair, East Asian facial features"
            elif 'asian' in ethn:
                face_block = f"South Asian {'woman' if gender_str == 'female' else 'man ' if gender_str == 'male' else 'person'}, light brown skin, dark eyes, dark straight or wavy hair, South Asian facial features"
            elif 'african' in ethn or 'black' in ethn:
                face_block = f"Black/African {'woman' if gender_str == 'female' else 'man' if gender_str == 'male' else 'person'}, dark brown or black skin, curly/coily hair, strong jawline, fuller lips, African facial features"
            elif 'hispanic' in ethn or 'latino' in ethn:
                face_block = f"Latino/Latina {('woman' if gender_str == 'female' else 'man' if gender_str == 'male' else 'person')}, light brown or olive skin, dark eyes, straight or wavy dark hair, Latino facial features"
            elif 'caucasian' in ethn or 'european' in ethn or 'white' in ethn:
                face_block = f"White/European {('woman' if gender_str == 'female' else 'man' if gender_str == 'male' else 'person')}, fair skin, brown, blonde or black straight/wavy hair, blue, green, or brown eyes, European facial features"
            elif 'mixed' in ethn:
                face_block = "person of mixed heritage, neutral facial features"
            else:
                face_block = "person of undetermined heritage, neutral facial features"
            # Overwrite prompt_parts with more specific face_block
            prompt_parts = [face_block]

            # Base description with strong gender anchoring
            gender_l = gender.lower().strip()
            gender_anchor = "adult person"
            gender_positive = None
            gender_negative = None
            if gender_l == "male":
                gender_anchor = "adult man, male"
                # Strong positive/negative anchors to avoid gender flips in some models
                gender_positive = "clearly male facial features, masculine jawline, no makeup"
                gender_negative = "not female, not woman, no feminine makeup"
            elif gender_l == "female":
                gender_anchor = "adult woman, female"
                gender_positive = "clearly female facial features, soft feminine traits"
                gender_negative = "not male, not man, no facial hair"

            base_desc = [
                f"Professional medical portrait photograph of a {age}-year-old {gender_anchor}",
                f"of {ethnicity_desc}",
                "neutral background, soft lighting, facing camera",
                "realistic photographic style, high quality"
            ]
            if gender_positive:
                base_desc.append(gender_positive)
            if gender_negative:
                base_desc.append(gender_negative)

            prompt_parts += base_desc
        except Exception as e:
            # Log details for debugging
            self.last_error = (
                f"prompt_parts error: {type(e).__name__}: {e}\n"
                f"age={demo.get('age')!r} gender={demo.get('gender')!r} ethnicity={demo.get('ethnicity')!r} birth_country={demo.get('birth_country')!r}"
            )
            # Return emergency fallback prompt
            return ", ".join(prompt_parts)

        # Add emotional state based on medical conditions
        # current_conditions lives under clinical_information, not inside demographics
        conditions = clinical.get('current_conditions', [])
        if isinstance(conditions, list):
            condition_count = len(conditions)
        else:
            condition_count = 0

        # Determine emotional state (base)
        if condition_count >= 3:
            prompt_parts.append("subtle tired expression, showing signs of chronic illness")
            prompt_parts.append("slight weariness in eyes but maintaining dignity")
        elif condition_count >= 1:
            prompt_parts.append("calm expression with hint of concern")
            prompt_parts.append("thoughtful demeanor")
        else:
            prompt_parts.append("healthy appearance, slight smile")
            prompt_parts.append("positive demeanor")

        # Add age-appropriate details
        if age >= 60:
            prompt_parts.append("gray hair, age lines, mature features")
        elif age >= 40:
            prompt_parts.append("middle-aged appearance, slight aging signs")
        else:
            prompt_parts.append("youthful appearance")

        # Extract weight/height/BMI when available to influence body habitus
        height_cm = None
        weight_kg = None
        bmi_value = None
        try:
            demo_clin = clinical.get('demographics', {})
            if isinstance(demo_clin, dict):
                height = demo_clin.get('schema:height', {})
                if isinstance(height, dict):
                    height_cm = height.get('schema:value')
                weight = demo_clin.get('schema:weight', {})
                if isinstance(weight, dict):
                    weight_kg = weight.get('schema:value')
                bmi_value = demo_clin.get('bmi')
        except Exception:
            pass

        # Compute BMI if not present and possible
        if bmi_value is None and height_cm and weight_kg:
            try:
                h_m = float(height_cm) / 100.0
                if h_m > 0:
                    bmi_value = float(weight_kg) / (h_m * h_m)
            except Exception:
                bmi_value = None

        # Map BMI/weight to body habitus description
        body_desc = None
        try:
            if bmi_value is not None:
                if bmi_value < 18.5:
                    body_desc = "underweight body type, slight thinness"
                elif bmi_value < 25:
                    body_desc = "average body type"
                elif bmi_value < 30:
                    body_desc = "overweight body type, fuller face"
                elif bmi_value < 35:
                    body_desc = "obese body type, visibly heavy set"
                elif bmi_value < 40:
                    body_desc = "severely obese body type, very full features"
                else:
                    body_desc = "morbidly obese body type, pronounced fullness in face and body"
            elif weight_kg is not None and float(weight_kg) >= 120:
                body_desc = "obese body type, visibly heavy set"
        except Exception:
            body_desc = None

        if body_desc:
            prompt_parts.append(body_desc)

        # Stronger visual anchors for higher BMI (exaggerated)
        try:
            if bmi_value is not None and bmi_value >= 30:
                prompt_parts.append("extremely full rounded cheeks, highly prominent double chin, extremely wide face, dramatically broad neck and shoulders, very full/rounded upper torso, visible arm fullness, deep neck skin folds")
            if bmi_value is not None and bmi_value >= 40:
                prompt_parts.append("face and neck appear profoundly large, excess fullness under chin, arms full and thick with body-wide fullness")
            if bmi_value is not None and bmi_value < 18.5:
                prompt_parts.append("very slender, pronounced gaunt cheeks, sharply visible cheekbones, extremely thin neck and shoulders, collarbones sharply protruding, bony hands visible if in frame")
        except Exception:
            pass

        # Include height/weight hints to anchor proportions (without forcing exact numbers)
        if height_cm:
            prompt_parts.append("proportions consistent with reported height")
        if weight_kg:
            prompt_parts.append("proportions consistent with reported weight")

        # Add clothing
        prompt_parts.append("wearing casual comfortable clothing appropriate for a clinic visit")

        # Gender-aware regional/cultural attire (patients only; no clinical/medical/scientific cues)
        try:
            country = str(birth_country or "").lower()
            gender_l = str(gender).lower().strip()
            region_hint = None
            # Gulf/Saudi
            if any(k in country for k in ["saudi", "uae", "emirates", "qatar", "oman", "kuwait", "bahrain"]):
                if gender_l == "female":
                    region_hint = "modest black abaya covering body, black hijab fully covering hair—no scarf on face, not medical attire"
                else:
                    region_hint = "long white thobe (ankle-length garment), no head covering, cropped hair, not medical attire"
            elif any(k in country for k in ["egypt", "morocco", "algeria", "tunisia"]):
                if gender_l == "female":
                    region_hint = "long modest dress or abaya, light scarf or hijab covering hair, not medical attire"
                else:
                    region_hint = "collared shirt and pants or galabeya, no headscarf, casual clothes"
            elif any(k in country for k in ["pakistan", "india", "bangladesh", "sri lanka"]):
                if gender_l == "female":
                    region_hint = "kurta tunic and pants, dupatta or hijab covering hair, not medical attire"
                else:
                    region_hint = "kurta or shirt and pants, no headscarf, not medical attire"
            elif any(k in country for k in ["china", "japan", "korea", "taiwan", "singapore", "vietnam", "thailand", "malaysia", "indonesia"]):
                region_hint = "simple, modern, minimalist daywear/casual clothes, no head covering"
            elif any(k in country for k in ["nigeria", "ghana", "kenya", "south africa", "ethiopia", "uganda", "tanzania"]):
                if gender_l == "female":
                    region_hint = "patterned long dress or skirt/top, bright head tie or scarf, casual patient clothing"
                else:
                    region_hint = "colorful shirt and trousers, no head covering, casual wear"
            elif any(k in country for k in ["mexico", "brazil", "argentina", "chile", "colombia", "peru"]):
                region_hint = "latin american casual attire, warm earth tones, not medical clothes, no head covering"
            elif any(k in country for k in ["turkey", "iran", "iraq", "jordan", "lebanon", "syria", "yemen"]):
                if gender_l == "female":
                    region_hint = "long modest coat, dress or abaya, well-fitted headscarf (hijab) covering hair"
                else:
                    region_hint = "button-down shirt and long trousers, short/trimmed hair, no head covering"
            elif any(k in country for k in ["france", "germany", "netherlands", "belgium", "spain", "italy", "sweden", "norway", "denmark", "uk", "ireland", "poland"]):
                region_hint = "european casual layered clothing, no head covering, not medical"
            elif any(k in country for k in ["usa", "united states", "canada", "australia", "new zealand"]):
                region_hint = "plain T-shirt, shirt, casual cardigan, blouse or dress, no head covering, not medical"
            # fallback by ethnicity if needed
            if not region_hint:
                eth_l = str(ethnicity).lower()
                if "asian" in eth_l:
                    region_hint = "east/south asian patient attire (long tunic, blouse, or casual shirt)"
                elif any(x in eth_l for x in ["african", "black"]):
                    region_hint = "african-inspired patient attire; modest patterned dress for female, colorful shirt for male"
                elif any(x in eth_l for x in ["middle eastern", "arab"]):
                    region_hint = "middle eastern modest attire (scarf for female, uncovered hair for male)"
                elif any(x in eth_l for x in ["hispanic", "latino"]):
                    region_hint = "latin american casual clothing (warm colors)"
                elif any(x in eth_l for x in ["european", "caucasian"]):
                    region_hint = "european/western casual clothing"
            if region_hint:
                prompt_parts.append(region_hint)
        except Exception:
            pass
        # No medical or clinical attire cues anywhere in prompt.

        # Subtle attributes based on lifestyle factors (if available)
        lifestyle_factors = clinical.get('lifestyle_factors', [])
        if isinstance(lifestyle_factors, list) and lifestyle_factors:
            # Normalize to simple flags
            is_smoker = any((f.get('factor_type') == 'smoking' and f.get('status') == 'current') for f in lifestyle_factors if isinstance(f, dict))
            drinks_alcohol = any((f.get('factor_type') == 'alcohol') for f in lifestyle_factors if isinstance(f, dict))
            exercise_regular = any((f.get('factor_type') == 'exercise' and 'Regular' in str(f.get('rdfs:label', ''))) for f in lifestyle_factors if isinstance(f, dict))

            if is_smoker:
                prompt_parts.append("subtle signs consistent with current smoker (slight skin dullness)")
            if drinks_alcohol and (bmi_value or weight_kg):
                prompt_parts.append("very mild facial redness acceptable in clinical portrait")
            if exercise_regular and (bmi_value and bmi_value < 30):
                prompt_parts.append("healthy posture")

        # Age/gender style refinements
        try:
            if gender.lower() == 'male':
                if age >= 50:
                    prompt_parts.append("short neatly kept hair, optional subtle gray, light facial hair acceptable")
                else:
                    prompt_parts.append("short neatly kept hair")
            elif gender.lower() == 'female':
                if age >= 50:
                    prompt_parts.append("neatly styled hair, optional subtle gray streaks")
                else:
                    prompt_parts.append("neatly styled hair")
        except Exception:
            pass

        # Accessories common in clinics; avoid text artifacts
        prompt_parts.append("no text, no watermark, no logos")

        # Important: make it look natural and human
        prompt_parts.append("natural skin texture, realistic human features, accurate body proportions")
        prompt_parts.append("NOT illustration, NOT cartoon, NOT artwork")
        prompt_parts.append("photorealistic medical record photo")

        # Specific affect based on mental health conditions
        try:
            labels = []
            for c in conditions if isinstance(conditions, list) else []:
                if isinstance(c, dict):
                    lbl = (c.get('rdfs:label') or c.get('name') or '')
                    if isinstance(lbl, str):
                        labels.append(lbl.lower())
            has_anxiety = any('anxiety' in l for l in labels)
            has_depression = any('depress' in l for l in labels)
            if has_anxiety:
                prompt_parts.append("subtle anxious affect, gentle furrowed brow, attentive gaze")
            if has_depression:
                prompt_parts.append("subdued affect, low energy gaze, gentle neutral mouth")
        except Exception:
            pass

        return ", ".join(prompt_parts)

    def _generate_with_openai(self, prompt: str) -> Optional[bytes]:
        """Generate image using OpenAI DALL-E"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024",
                "quality": "standard",
                "style": "natural"
            }

            response = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                image_url = result['data'][0]['url']

                # Download the image
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code == 200:
                    print("✅ Photo generated successfully with OpenAI DALL-E")
                    return image_response.content
            else:
                err = f"OpenAI API error: {response.status_code} - {response.text}"
                print(f"❌ {err}")
                self.last_error = err
                return None

        except Exception as e:
            err = f"Error generating with OpenAI: {e}"
            print(f"❌ {err}")
            self.last_error = err
            return None

    def _generate_with_gemini(self, prompt: str) -> Optional[bytes]:
        """Generate image using Google Gemini/Imagen via Google AI Studio.

        Supports multiple client import paths and response shapes.
        """
        client = None
        genai_mod = None
        # Prefer modern import path
        try:
            from google import genai as _genai  # type: ignore
            genai_mod = _genai
            client = _genai.Client(api_key=self.api_key)
        except Exception:
            self.last_error = "google-genai not installed or import failed. Install with: pip install google-genai"
            print(f"❌ {self.last_error}")
            return None

        try:
            # Use modern API only. If unavailable, surface a clear error with capability introspection.
            has_models = hasattr(client, "models")
            has_models_generate = has_models and hasattr(client.models, "generate_images")
            has_images_attr = hasattr(client, "images")
            version = getattr(genai_mod, "__version__", "unknown")
            if not has_models_generate:
                self.last_error = (
                    f"Gemini SDK lacks models.generate_images. genai version={version}; "
                    f"has client.models={has_models}; has models.generate_images={has_models_generate}; "
                    f"has client.images={has_images_attr}"
                )
                print(f"❌ {self.last_error}")
                return None

            cfg = None
            types_mod = getattr(genai_mod, "types", None)
            if types_mod and hasattr(types_mod, "GenerateImagesConfig"):
                GenerateImagesConfig = getattr(types_mod, "GenerateImagesConfig")
                cfg = GenerateImagesConfig(
                    number_of_images=1,
                    safety_filter_level="BLOCK_LOW_AND_ABOVE",
                    person_generation="ALLOW_ADULT",
                    aspect_ratio="1:1",
                )

            # Try supported models in order, stop on first that works
            # Prefer latest public model codes; fall back to older ones if enabled
            candidate_models = [
                # Imagen 4 family (2025) - Generally Available
                "imagen-4.0-generate-001",
                "imagen-4.0-ultra-generate-001",
                "imagen-4.0-fast-generate-001",
                # Imagen 3 updated code (2025)
                "imagen-3.0-generate-002",
                "imagen-3.0-generate-001",
                "imagen-3.0-fast-generate-001",
                "imagen-3.0-capability-001"
                # NOTE: imagen-3.0-fast and imagen-3.0-nano are DEPRECATED as of Feb 2025
                # They are removed from the list to avoid 404 errors
            ]

            response = None
            last_exc: Optional[Exception] = None
            for model_id in candidate_models:
                try:
                    if cfg is not None:
                        response = client.models.generate_images(
                            model=model_id,
                            prompt=prompt,
                            config=cfg
                        )
                    else:
                        response = client.models.generate_images(
                            model=model_id,
                            prompt=prompt
                        )
                    print(f"✅ Successfully using model: {model_id}")
                    break
                except Exception as e:
                    last_exc = e
                    # Try next model on NOT_FOUND or unsupported errors
                    error_str = str(e)
                    if "404" in error_str or "NOT_FOUND" in error_str:
                        print(f"⚠️  Model {model_id} not found, trying next...")
                    continue

            if response is None:
                # As a last resort, discover available models dynamically
                print("🔍 No pre-configured models worked. Discovering available models...")
                try:
                    models = client.models.list()
                    # Prefer imagen-4, then imagen-3 families that support generate_images
                    def supports_image_gen(m):
                        caps = getattr(m, "supported_generation_methods", []) or getattr(m, "supportedMethods", [])
                        return any("generate_images" in str(c).lower() for c in caps)

                    image_models = [m for m in models if supports_image_gen(m)]
                    # Sort preference: imagen-4 first, then imagen-3, else anything with generate_images
                    def score(m):
                        name = getattr(m, "name", "") or ""
                        if "imagen-4" in name:
                            return 0
                        if "imagen-3" in name:
                            return 1
                        return 2
                    image_models.sort(key=score)

                    if image_models:
                        chosen = image_models[0].name
                        print(f"📸 Auto-discovered working model: {chosen}")
                        if cfg is not None:
                            response = client.models.generate_images(model=chosen, prompt=prompt, config=cfg)
                        else:
                            response = client.models.generate_images(model=chosen, prompt=prompt)
                    else:
                        all_model_names = [getattr(m, "name", "unknown") for m in models]
                        self.last_error = f"No image-capable models available for this API key/project. Available models: {all_model_names}. Last error: {last_exc}"
                        print(f"❌ {self.last_error}")
                        return None
                except Exception as e:
                    self.last_error = f"Model discovery failed and candidates unavailable. Last error: {last_exc}; discovery error: {e}"
                    print(f"❌ {self.last_error}")
                    return None

            # Extract bytes across possible response shapes
            image_bytes: Optional[bytes] = None

            # Case 1: response.images[0].image_bytes
            images_attr = getattr(response, "images", None)
            if images_attr and len(images_attr) > 0:
                img0 = images_attr[0]
                image_bytes = getattr(img0, "image_bytes", None)

            # Case 2: response.generated_images[0].image_bytes / .bytes / .data
            if image_bytes is None:
                gi = getattr(response, "generated_images", None)
                if gi and len(gi) > 0:
                    img0 = gi[0]
                    for attr in ("image_bytes", "bytes", "data"):
                        maybe = getattr(img0, attr, None)
                        if maybe is not None:
                            image_bytes = maybe if isinstance(maybe, (bytes, bytearray)) else None
                            break

            # Case 3: base64 data under response fields
            if image_bytes is None:
                for candidate in ("data", "image", "image_base64"):
                    maybe = getattr(response, candidate, None)
                    if isinstance(maybe, str):
                        try:
                            image_bytes = base64.b64decode(maybe)
                            break
                        except Exception:
                            pass

            if image_bytes:
                print("✅ Photo generated successfully with Gemini (Imagen 3)")
                return bytes(image_bytes)

            # Log shape for debugging
            self.last_error = f"Gemini API returned no images. Response type: {type(response)}"
            print(f"❌ {self.last_error}")
            return None

        except Exception as e:
            self.last_error = f"Error generating with Gemini: {e}"
            print(f"❌ {self.last_error}")
            return None

    def _generate_with_stability(self, prompt: str) -> Optional[bytes]:
        """Generate image using Stability AI"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }

            data = {
                "text_prompts": [
                    {
                        "text": prompt,
                        "weight": 1
                    },
                    {
                        "text": "cartoon, illustration, anime, drawing, sketch, unrealistic",
                        "weight": -1
                    }
                ],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            }

            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                image_data = result['artifacts'][0]['base64']
                print("✅ Photo generated successfully with Stability AI")
                return base64.b64decode(image_data)
            else:
                err = f"Stability AI error: {response.status_code} - {response.text}"
                print(f"❌ {err}")
                self.last_error = err
                return None

        except Exception as e:
            err = f"Error generating with Stability AI: {e}"
            print(f"❌ {err}")
            self.last_error = err
            return None


# Example usage
if __name__ == "__main__":
    # Example patient data
    patient = {
        'demographics': {
            'age': 55,
            'gender': 'Female',
            'ethnicity': ['Asian'],
            'birth_country': 'China'
        },
        'clinical_information': {
            'demographics': {
                'current_conditions': [
                    {'name': 'Hypertension'},
                    {'name': 'Diabetes'},
                    {'name': 'Arthritis'}
                ]
            }
        }
    }

    generator = AIPhotoGenerator()
    photo = generator.generate_patient_photo(patient)

    if photo:
        # Save to file
        with open('generated_patient.png', 'wb') as f:
            f.write(photo)
        print("Photo saved to generated_patient.png")
