INDIA_CITIES = [
    "Bengaluru",
    "Hyderabad",
    "Pune",
    "Chennai",
    "Mumbai",
    "Gurugram",
    "Noida",
    "Ahmedabad",
    "Kolkata",
    "remote",
]

CITY_ALIASES = {
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "gurgaon": "Gurugram",
    "gurugram": "Gurugram",
    "delhi ncr": "Gurugram",
    "ncr": "Noida",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "chennai": "Chennai",
    "mumbai": "Mumbai",
    "noida": "Noida",
    "ahmedabad": "Ahmedabad",
    "kolkata": "Kolkata",
    "remote": "remote",
    "india remote": "remote",
}

ROLE_ALIASES = {
    "ai engineer": {"ai engineer", "genai engineer", "llm engineer", "machine learning engineer"},
    "genai engineer": {"genai engineer", "ai engineer", "llm engineer", "generative ai engineer"},
    "llm engineer": {"llm engineer", "genai engineer", "ai engineer"},
    "ml engineer": {"ml engineer", "machine learning engineer", "applied scientist"},
    "mlops engineer": {"mlops engineer", "ml platform engineer", "platform engineer"},
    "data scientist": {"data scientist", "applied scientist", "ml engineer"},
    "applied scientist": {"applied scientist", "data scientist", "ml engineer"},
    "backend engineer": {"backend engineer", "software engineer", "platform engineer"},
    "platform engineer": {"platform engineer", "backend engineer", "mlops engineer"},
    "solutions architect": {"solutions architect", "solution architect", "architect"},
}

EMPLOYMENT_TYPES = ("full-time", "contract", "internship")
WORK_MODES = ("remote", "hybrid", "onsite")
COMPANY_PREFERENCES = ("startup", "enterprise", "either")


def canonicalize_city(value: str | None) -> str | None:
    if not value:
        return None
    return CITY_ALIASES.get(value.strip().lower(), value.strip())
