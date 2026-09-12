"""Constants and endpoints for Renpho Cloud API."""

API_BASE_URL = "https://cloud.renpho.com"
ENCRYPTION_KEY = "ed*wijdi$h6fe3ew"  # 16-byte AES-128 key
APP_VERSION = "6.6.0"
PLATFORM = "android"
SYSTEM_VERSION = "11"

ENDPOINTS = {
    "login": "renpho-aggregation/user/login",
    "device_info": "renpho-aggregation/device/count",
    "family": "RenphoHealth/centerUser/queryFamilyMemberList",
    "measurements": "RenphoHealth/scale/queryAllMeasureDataList",
    "body_composition": "RenphoHealth/scale/queryBodyCompositionMeasureData",
}

BODY_WEIGHT_SCALES = [
    "01", "02", "03", "04", "05", "06", "07", "08", "09", "0A",
    "0B", "0C", "0D", "0E", "0F", "10", "11", "12", "13", "14",
]

MEASUREMENT_TABLE_SHARDS = 24
MEASUREMENT_TABLE_NAMES = [
    f"measurements_info_{i}" for i in range(MEASUREMENT_TABLE_SHARDS)
]

METRICS_DISPLAY = [
    ("weight", "Weight", "kg"),
    ("bmi", "BMI", ""),
    ("bodyfat", "Body Fat", "%"),
    ("subfat", "Subcutaneous Fat", "%"),
    ("visfat", "Visceral Fat", "level"),
    ("sinew", "Fat-Free Weight", "kg"),
    ("muscle", "Muscle Mass", "%"),
    ("smmMass", "Skeletal Muscle", "kg"),
    ("bone", "Bone Mass", "kg"),
    ("water", "Body Water", "%"),
    ("protein", "Protein", "%"),
    ("bmr", "BMR", "kcal"),
    ("bodyage", "Metabolic Age", "years"),
]
