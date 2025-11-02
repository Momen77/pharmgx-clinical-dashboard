"""
Regional Name Database for Culturally Accurate Profile Generation

CRITICAL: This module ensures first names from a region are ONLY paired with
last names from the SAME region to prevent unrealistic combinations.

Example: Nigerian Igbo first name (Chike) will only get Nigerian Igbo surname (Okafor),
never a Kenyan surname (Mwangi) or Ghanaian surname (Mensah).

Structure:
- Each ethnicity contains multiple regions
- Each region has matched first/last name pools for Male/Female
- Selection logic picks a region first, then gets both names from that region
"""

# COMPREHENSIVE REGIONAL NAME DATABASE
REGIONAL_NAMES = {
    "African": {
        "regions": {
            "Nigerian_Igbo": {
                "countries": ["Nigeria"],
                "Male": {
                    "first": ["Chike", "Chidi", "Chinonso", "Chibueze", "Emeka", "Ikenna", "Obinna", "Nnamdi", "Okechukwu", "Uchenna",
                              "Chinedu", "Chijioke", "Obafemi", "Enyinnaya", "Ifeanyi", "Kelechi", "Nkem", "Obi", "Oge", "Ugo",
                              "Chukwudi", "Chukwuemeka", "Ebuka", "Echezona", "Izuchukwu", "Kenechukwu", "Nnamani", "Obichukwu", "Okolie", "Onyeka",
                              "Azubuike", "Chekwube", "Chinaza", "Chukwuma", "Ekezie", "Emejuru", "Ikem", "Kachukwu", "Kosisochukwu", "Ndubuisi"],
                    "last": ["Okafor", "Okeke", "Okonkwo", "Udoka", "Nwosu", "Eze", "Nnamdi", "Nwankwo", "Obinna", "Obi",
                             "Onyekwere", "Ugochukwu", "Uzodinma", "Ezekiel", "Chukwu", "Onwuachu", "Nwachukwu", "Emezie",
                             "Anyanwu", "Chikezie", "Ezeonu", "Ikpeazu", "Nweke", "Ogu", "Onuoha", "Uchegbu", "Uche"]
                },
                "Female": {
                    "first": ["Amara", "Chioma", "Ngozi", "Adaeze", "Ifeoma", "Chiamaka", "Nneka", "Obiageli", "Uchenna", "Nkechi",
                              "Chidinma", "Chinwe", "Ebere", "Ego", "Ifunanya", "Njideka", "Nkiruka", "Nneoma", "Nwamaka", "Obioma",
                              "Adanna", "Amarachi", "Chinenye", "Chinyere", "Echezona", "Ezinne", "Ijeoma", "Kamsiyochi", "Nkemdilim", "Onyinye",
                              "Amaka", "Chidiebere", "Chinaza", "Chukwuemeka", "Ebele", "Ifeyinwa", "Kelechi", "Nkemdiri", "Nkoli", "Nma"],
                    "last": ["Okafor", "Okeke", "Okonkwo", "Udoka", "Nwosu", "Eze", "Nnamdi", "Nwankwo", "Obinna", "Obi",
                             "Onyekwere", "Ugochukwu", "Uzodinma", "Ezekiel", "Chukwu", "Onwuachu", "Nwachukwu", "Emezie",
                             "Anyanwu", "Chikezie", "Ezeonu", "Ikpeazu", "Nweke", "Ogu", "Onuoha", "Uchegbu", "Uche"]
                }
            },
            "Nigerian_Yoruba": {
                "countries": ["Nigeria"],
                "Male": {
                    "first": ["Ade", "Adebayo", "Adewale", "Ademola", "Oluwaseun", "Olumide", "Babatunde", "Ayodele", "Akinwale", "Olusegun",
                              "Adeyemi", "Adekunle", "Adeniyi", "Akintunde", "Bolaji", "Damilola", "Kayode", "Olalekan", "Olaniyan", "Oluwatobi",
                              "Adeyinka", "Akinola", "Ayotunde", "Babajide", "Femi", "Olamide", "Olaseni", "Oluseyi", "Omowale", "Taiwo",
                              "Adeleke", "Adeola", "Adeyanju", "Afolabi", "Akinyemi", "Ayodeji", "Gbenga", "Kolawole", "Ola", "Toyin"],
                    "last": ["Adeyemi", "Adeleke", "Akinyemi", "Oluwole", "Babatunde", "Ogundele", "Adekunle", "Adebayo", "Olawale", "Ogunleye",
                             "Akinde", "Akinola", "Ayodele", "Famuyiwa", "Ogunbiyi", "Ogunsola", "Oladele", "Olatunji", "Oyewole",
                             "Afolabi", "Ajayi", "Akinwale", "Awolowo", "Balogun", "Fal​ola", "Obasanjo", "Odunsi", "Oseni"]
                },
                "Female": {
                    "first": ["Adunni", "Ayomide", "Bisola", "Folake", "Ife", "Jumoke", "Kehinde", "Modupe", "Omolara", "Titilayo",
                              "Abosede", "Adetoun", "Boluwatife", "Damilola", "Folashade", "Funmilayo", "Iyabo", "Mojisola", "Olabisi",
                              "Adebimpe", "Adedoyin", "Adeola", "Bolanle", "Morayo", "Omowunmi", "Ronke", "Seun", "Yetunde",
                              "Adesuwa", "Akinyi", "Ayobami", "Bola", "Bunmi", "Nike", "Olufunke", "Sade", "Temilola", "Yewande"],
                    "last": ["Adeyemi", "Adeleke", "Akinyemi", "Oluwole", "Babatunde", "Ogundele", "Adekunle", "Adebayo", "Olawale", "Ogunleye",
                             "Akinde", "Akinola", "Ayodele", "Famuyiwa", "Ogunbiyi", "Ogunsola", "Oladele", "Olatunji", "Oyewole",
                             "Afolabi", "Ajayi", "Akinwale", "Awolowo", "Balogun", "Falola", "Obasanjo", "Odunsi", "Oseni"]
                }
            },
            "Ghanaian_Akan": {
                "countries": ["Ghana"],
                "Male": {
                    "first": ["Kwame", "Kofi", "Kwesi", "Kwaku", "Yaw", "Kojo", "Kobina", "Kwadwo", "Kwabena", "Koffi",
                              "Agyeman", "Akwasi", "Ato", "Kwamena", "Nana", "Opoku", "Yeboah", "Boateng", "Osei",
                              "Adom", "Agyei", "Anane", "Atta", "Boadi", "Darkwa", "Frimpong", "Mensah", "Nyantakyi", "Owusu",
                              "Amoah", "Antwi", "Asare", "Boakye", "Donkor", "Gyasi", "Konadu", "Ofosu", "Sarkodie", "Yiadom"],
                    "last": ["Mensah", "Asante", "Boateng", "Owusu", "Osei", "Nkrumah", "Agyeman", "Agyei", "Amoah", "Antwi",
                             "Appiah", "Asare", "Attah", "Darkwa", "Frimpong", "Konadu", "Nyantakyi", "Opoku", "Yeboah",
                             "Acheampong", "Adjei", "Boakye", "Danquah", "Gyasi", "Kufuor", "Ofori", "Sarkodie", "Yiadom"]
                },
                "Female": {
                    "first": ["Ama", "Afua", "Akua", "Abena", "Afia", "Akosua", "Adwoa", "Yaa", "Adjoa", "Esi",
                              "Efua", "Abenaa", "Akosua", "Akosuah", "Amma", "Ekua", "Enyonam", "Maame", "Nana", "Oboshie",
                              "Araba", "Efua", "Ekua", "Esi", "Kukua", "Mansa", "Serwa", "Serwaa", "Yaayaa"],
                    "last": ["Mensah", "Asante", "Boateng", "Owusu", "Osei", "Nkrumah", "Agyeman", "Agyei", "Amoah", "Antwi",
                             "Appiah", "Asare", "Attah", "Darkwa", "Frimpong", "Konadu", "Nyantakyi", "Opoku", "Yeboah",
                             "Acheampong", "Adjei", "Boakye", "Danquah", "Gyasi", "Kufuor", "Ofori", "Sarkodie", "Yiadom"]
                }
            },
            # Continue with more African regions...
        }
    },
    # Will add more ethnicities below
}


def get_random_name(ethnicity, gender, random_module):
    """
    Get a culturally matched first and last name from the same region.

    Args:
        ethnicity: Ethnicity key (e.g., "African", "South Asian")
        gender: "Male" or "Female"
        random_module: Python random module instance

    Returns:
        tuple: (first_name, last_name) from the same region
    """
    if ethnicity not in REGIONAL_NAMES:
        # Fallback for ethnicities not yet regionalized
        return None, None

    ethnicity_data = REGIONAL_NAMES[ethnicity]

    # Pick a random region within the ethnicity
    regions = ethnicity_data["regions"]
    region_key = random_module.choice(list(regions.keys()))
    region_data = regions[region_key]

    # Get matched first and last name from the SAME region
    first_name = random_module.choice(region_data[gender]["first"])
    last_name = random_module.choice(region_data[gender]["last"])

    return first_name, last_name
