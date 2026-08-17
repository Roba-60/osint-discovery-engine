import aiohttp
import asyncio
from typing import List, Dict, Any

HEADERS = {
    "User-Agent": "OSINT-Discovery-Engine/1.0 (Public Research Module)"
}

async def check_github(session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
    url = f"https://api.github.com/users/{username}"
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                return {
                    "platform": "GitHub",
                    "status": "exists",
                    "profile_url": f"https://github.com/{username}",
                    "details": {"public_repos": data.get("public_repos")}
                }
    except Exception:
        pass
    return None

async def check_gitlab(session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
    url = f"https://gitlab.com/api/v4/users?username={username}"
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return {
                        "platform": "GitLab",
                        "status": "exists",
                        "profile_url": f"https://gitlab.com/{username}",
                        "details": {"name": data[0].get("name")}
                    }
    except Exception:
        pass
    return None

async def check_reddit(session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
    url = f"https://www.reddit.com/user/{username}/about.json"
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                user_data = data.get("data", {})
                if user_data and not user_data.get("is_suspended"):
                    return {
                        "platform": "Reddit",
                        "status": "exists",
                        "profile_url": f"https://www.reddit.com/user/{username}",
                        "details": {"total_karma": user_data.get("total_karma")}
                    }
    except Exception:
        pass
    return None

async def check_hackernews(session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
    url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data is not None:
                    return {
                        "platform": "HackerNews",
                        "status": "exists",
                        "profile_url": f"https://news.ycombinator.com/user?id={username}",
                        "details": {"karma": data.get("karma")}
                    }
    except Exception:
        pass
    return None

async def check_devto(session: aiohttp.ClientSession, username: str) -> Dict[str, Any]:
    url = f"https://dev.to/api/users/by_username?url={username}"
    try:
        async with session.get(url, headers=HEADERS, timeout=5) as resp:
            if resp.status == 200:
                data = await resp.json()
                if data.get("username"):
                    return {
                        "platform": "Dev.to",
                        "status": "exists",
                        "profile_url": f"https://dev.to/{username}",
                        "details": {"summary": data.get("summary")}
                    }
    except Exception:
        pass
    return None

async def search_public_username(username: str) -> List[Dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        tasks = [
            check_github(session, username),
            check_gitlab(session, username),
            check_reddit(session, username),
            check_hackernews(session, username),
            check_devto(session, username),
        ]
        results = await asyncio.gather(*tasks)
        return [res for res in results if res is not None]
