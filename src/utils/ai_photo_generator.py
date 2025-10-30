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
        demo = patient_data.get('demographics', {})
        clinical = patient_data.get('clinical_information', {})

        # Extract key demographics
        age = demo.get('age', 45)
        gender = demo.get('gender', 'Male')
        ethnicity = demo.get('ethnicity', [])[0] if demo.get('ethnicity') else 'Caucasian/European'
        birth_country = demo.get('birth_country', '')

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

        # Base description
        prompt_parts = [
            f"Professional medical portrait photograph of a {age}-year-old {gender.lower()} patient",
            f"of {ethnicity_desc}",
            "neutral background, soft lighting, facing camera",
            "realistic photographic style, high quality"
        ]

        # Add emotional state based on medical conditions
        conditions = clinical.get('demographics', {}).get('current_conditions', [])
        if isinstance(conditions, list):
            condition_count = len(conditions)
        else:
            condition_count = 0

        # Determine emotional state
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

        # Add clothing
        prompt_parts.append("wearing casual comfortable clothing")

        # Important: make it look natural and human
        prompt_parts.append("natural skin texture, realistic human features")
        prompt_parts.append("NOT illustration, NOT cartoon, NOT artwork")
        prompt_parts.append("photorealistic medical record photo")

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
        # Try both import paths used by google-genai across versions
        try:
            from google import genai as _genai  # type: ignore
            genai_mod = _genai
            client = _genai.Client(api_key=self.api_key)
        except Exception:
            try:
                from google.genai import Client  # type: ignore
                client = Client(api_key=self.api_key)
            except Exception:
                self.last_error = "google-genai not installed or import failed. Install with: pip install google-genai"
                print(f"❌ {self.last_error}")
                return None

        try:
            response = None
            # Preferred modern API: client.models.generate_images
            try:
                if genai_mod is not None and hasattr(client, "models") and hasattr(client.models, "generate_images"):
                    cfg_cls = getattr(genai_mod, "types", None)
                    cfg = None
                    if cfg_cls and hasattr(cfg_cls, "GenerateImagesConfig"):
                        GenerateImagesConfig = getattr(cfg_cls, "GenerateImagesConfig")
                        cfg = GenerateImagesConfig(
                            number_of_images=1,
                            safety_filter_level="BLOCK_LOW_AND_ABOVE",
                            person_generation="ALLOW_ADULT",
                            aspect_ratio="1:1",
                        )
                    response = client.models.generate_images(
                        model="imagen-3.0-generate-001",
                        prompt=prompt,
                        config=cfg
                    )
            except Exception as e:
                # Fall back to older API shapes below
                pass

            # Legacy API: client.images.generate
            if response is None and hasattr(client, "images") and hasattr(client.images, "generate"):
                response = client.images.generate(
                    model="imagen-3.0-generate-001",
                    prompt=prompt,
                    size="1024x1024",
                    num_images=1,
                    safety_filter_level="block_some",
                    negative_prompt="blurry, low-res, watermark, text, cartoon, illustration"
                )

            if response is None:
                self.last_error = "Gemini client has neither models.generate_images nor images.generate"
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
