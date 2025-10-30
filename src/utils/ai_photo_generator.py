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

    def __init__(self, api_key: str = None, service: str = "openai"):
        """
        Initialize photo generator

        Args:
            api_key: API key for the AI service
            service: Which service to use ("openai", "stability", "replicate")
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.service = service

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
        if self.service == "openai" and self.api_key:
            return self._generate_with_openai(prompt)
        elif self.service == "stability" and self.api_key:
            return self._generate_with_stability(prompt)
        else:
            print("⚠️ No API key configured, using fallback avatar")
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
                print(f"❌ OpenAI API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error generating with OpenAI: {e}")
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
                print(f"❌ Stability AI error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error generating with Stability AI: {e}")
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
