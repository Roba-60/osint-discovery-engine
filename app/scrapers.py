import aiohttp
from typing import List, Dict

PUBLIC_PLATFORMS = {
    "GitHub": "https://api.github.com/users/{}",
    "Reddit": "https://www.reddit.com/user/{}/about.json",
    "GitLab": "https://gitlab.com/api/v4/users?username={}"
}

async def search_public_username(username: str) -> List[Dict]:
    results = []
    headers = {"User-Agent": "OSINT-Discovery-Engine/1.0"}
    async with aiohttp.ClientSession(headers=headers) as session:
        for platform, url_template in PUBLIC_PLATFORMS.items():
            target_url = url_template.format(username)
            try:
                async with session.get(target_url, timeout=5) as response:
                    if response.status == 200:
                        results.append({
                            "platform": platform,
                            "status": "exists",
                            "profile_url": f"https://{platform.lower()}.com/{username}"
                        })
            except Exception:
                continue
    return results
