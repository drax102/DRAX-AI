"""
open_website.py — Universal Siri-style website opener plugin.
Converts spoken paths like 'open lpu.in slash dashboard in chrome' -> 'https://lpu.in/dashboard'.
"""

import re
import webbrowser
from backend.core.logger import get_logger

logger = get_logger(__name__)

POPULAR_SITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "reddit": "https://www.reddit.com",
    "instagram": "https://www.instagram.com",
    "twitter": "https://x.com",
    "x": "https://x.com",
    "facebook": "https://www.facebook.com",
    "amazon": "https://www.amazon.in",
    "flipkart": "https://www.flipkart.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "stackoverflow": "https://stackoverflow.com",
    "linkedin": "https://www.linkedin.com",
    "whatsapp": "https://web.whatsapp.com",
    "discord": "https://discord.com/app",
    "wikipedia": "https://www.wikipedia.org",
    "twitch": "https://www.twitch.tv",
    "yahoo": "https://www.yahoo.com",
    "bing": "https://www.bing.com",
}


def clean_spoken_url(text: str) -> str:
    """Converts spoken URL words like 'slash', 'dot', 'dash' into actual URL symbols."""
    t = text.lower().strip()
    t = re.sub(r'\s*\bslash\b\s*', '/', t)
    t = re.sub(r'\s*\bdot\b\s*', '.', t)
    t = re.sub(r'\s*\bdash\b\s*', '-', t)
    t = re.sub(r'\s*\bhyphen\b\s*', '-', t)
    return t


def open_website(cmd: str) -> str:
    """
    Universal Siri-style website opener. Converts spoken URL paths like
    'open lpu.in slash dashboard' -> 'https://lpu.in/dashboard'.
    """
    c = clean_spoken_url(cmd)

    # Remove trigger verbs and trailing browser keywords
    clean = re.sub(r'^(open|launch|visit|go to)\s+', '', c)
    clean = re.sub(r'\s+(in|on)\s+(chrome|edge|browser|firefox)$', '', clean)
    clean = re.sub(r'\s+(website|site|online|page)$', '', clean).strip()

    # 1. Match domain names (e.g. lpu.in, lpg.in, google.com, lpu.in/dashboard)
    domain_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z]{2,10}(?:\.[a-zA-Z]{2,4})*(?:/[a-zA-Z0-9_.-]*)*)', clean)
    if domain_match:
        target_path = domain_match.group(1)
        url = f"https://{target_path}"
        logger.info(f"Opening URL: {url}")
        webbrowser.open(url)
        return f"Opening https://{target_path} in browser."

    # 2. Check popular sites dictionary
    if clean in POPULAR_SITES:
        webbrowser.open(POPULAR_SITES[clean])
        return f"Opening {clean.title()} in browser."

    # Substring check in popular sites
    for site_key, site_url in POPULAR_SITES.items():
        if site_key == clean or site_key in clean:
            webbrowser.open(site_url)
            return f"Opening {site_key.title()} in browser."

    # 3. Fallback: Treat single words as www.[clean].com
    if clean and len(clean) > 2 and " " not in clean:
        url = f"https://www.{clean}.com"
        webbrowser.open(url)
        return f"Opening https://www.{clean}.com in browser."

    # 4. Default Google search
    url = f"https://www.google.com/search?q={clean}"
    webbrowser.open(url)
    return f"Searching for '{clean}' online."
