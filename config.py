import os
from typing import List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Default prompt used by the data-quality (DQ) pipeline. The model is shown all
# of a datastream's quicklook plots for a single day and asked to assess data
# quality holistically, returning a strict JSON object the pipeline can parse.
_DEFAULT_DQ_PROMPT = (
    "You are a data quality analyst reviewing ARM (Atmospheric Radiation "
    "Measurement) quicklook plots. The {count} image(s) shown are all of the "
    "quicklook plots for datastream '{datastream}' on {day}.\n\n"
    "Inspect the plots holistically for data quality issues such as: missing "
    "or sparse data, flat-lined or stuck values, unphysical outliers, "
    "noise, suspicious discontinuities, values pinned at instrument limits, "
    "calibration shifts, or anything that looks anomalous for this kind of "
    "measurement.\n\n"
    "Respond with ONLY a single JSON object and nothing else (no markdown code "
    "fences, no commentary). Use exactly this schema:\n"
    "{{\n"
    '  "issues_found": true or false,\n'
    '  "severity": "Good" | "Indeterminate" | "Bad",\n'
    '  "summary": "one or two sentence overall assessment",\n'
    '  "issues": ["short description of each specific issue, empty list if none"]\n'
    "}}"
)

class Config:
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL: Optional[str] = os.getenv("OPENAI_BASE_URL") 
    # Ollama Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Default models
    DEFAULT_GPT_MODEL: str = os.getenv("DEFAULT_GPT_MODEL", "gpt-4-vision-preview")
    DEFAULT_OLLAMA_MODEL: str = os.getenv("DEFAULT_OLLAMA_MODEL", "llava")
    
    # Image processing settings
    MAX_IMAGE_SIZE_MB: int = int(os.getenv("MAX_IMAGE_SIZE_MB", "10"))
    SUPPORTED_IMAGE_FORMATS: List[str] = os.getenv(
        "SUPPORTED_IMAGE_FORMATS", "jpg,jpeg,png,gif,bmp,webp"
    ).split(",")
    
    # Parallel processing settings
    MAX_CONCURRENT_MODELS: int = int(os.getenv("MAX_CONCURRENT_MODELS", "3"))
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))

    # Data quality (DQ) quicklook pipeline settings.
    # ARM's plot server has no usable directory listing, so the per-day quicklook
    # PNG URL is constructed directly as DQ_PATH_TEMPLATE (the directory) +
    # DQ_FILENAME_TEMPLATE (the file):
    #   DQ_PATH_TEMPLATE.format(base=DQ_BASE_URL, fac=..., facinstrument=...,
    #       yyyymmdd=...)
    #   DQ_FILENAME_TEMPLATE.format(datastream=..., yyyymmdd=...)
    # These are configurable so the URL scheme can be corrected without code
    # changes. The filename default is specific to the `met` instrument's
    # meteogram quicklook; override DQ_FILENAME_TEMPLATE for other instruments.
    DQ_BASE_URL: str = os.getenv("DQ_BASE_URL", "https://plot.adc.arm.gov/PLOTS")
    DQ_PATH_TEMPLATE: str = os.getenv(
        "DQ_PATH_TEMPLATE", "{base}/{fac}/{facinstrument}/{yyyymmdd}/"
    )
    DQ_FILENAME_TEMPLATE: str = os.getenv(
        "DQ_FILENAME_TEMPLATE", "{datastream}.meteogram.{yyyymmdd}.png"
    )
    DQ_MAX_IMAGES_PER_DAY: int = int(os.getenv("DQ_MAX_IMAGES_PER_DAY", "12"))
    DQ_TEMP_DIR: Optional[str] = os.getenv("DQ_TEMP_DIR")  # None => system temp
    DQ_DEFAULT_PROMPT: str = os.getenv("DQ_DEFAULT_PROMPT", _DEFAULT_DQ_PROMPT)

    # Default location for the opt-in per-day quicklook picture cache. This is
    # only the path; caching stays off unless enabled via the CLI (--cache /
    # --cache-dir). Cached images live under
    # <DQ_CACHE_DIR>/<datastream>/<YYYYMMDD>/.
    DQ_CACHE_DIR: str = os.getenv("DQ_CACHE_DIR", ".nepho_cache/quicklooks")

config = Config()
