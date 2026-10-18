"""
HSBLearn YouTube Lecture Recommendations Service.
Extracts core concepts from material and fetches real videos via YouTube Data API v3.
When credentials are not configured, returns clear setup guidance without fabricating data.
"""
import os
import requests
from typing import List, Dict, Any
from backend.services.ai_service import get_material_chunks

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "").strip()

def get_video_recommendations(material_ids: List[int]) -> Dict[str, Any]:
    """
    Retrieves real educational lecture recommendations from YouTube API.
    Does not invent fake URLs or channels.
    """
    chunks = get_material_chunks(material_ids)
    # Extract candidate keywords for search
    sample_text = " ".join([c["text"] for c in chunks[:4]])
    words = [w.strip(".,;:\"'()") for w in sample_text.split() if len(w) > 5]
    search_query = " ".join(words[:4]) if words else "computer science lecture"

    if not YOUTUBE_API_KEY:
        return {
            "configured": False,
            "message": "YouTube API key is not configured in backend/.env. To enable live lecture recommendations, add YOUTUBE_API_KEY to your environment variables. No simulated links are shown.",
            "recommendations": []
        }

    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": f"{search_query} lecture tutorial",
            "type": "video",
            "maxResults": 5,
            "key": YOUTUBE_API_KEY
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = []
            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                if vid_id:
                    items.append({
                        "title": snippet.get("title", "Video Lecture"),
                        "channel": snippet.get("channelTitle", "YouTube Creator"),
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "duration": "Available on YouTube",
                        "relevance_reason": f"Matches key topic query '{search_query}' derived from your study material.",
                        "source_topic": search_query
                    })
            return {
                "configured": True,
                "message": None,
                "recommendations": items
            }
        else:
            return {
                "configured": True,
                "message": f"YouTube API returned status {resp.status_code}: {resp.text}",
                "recommendations": []
            }
    except Exception as e:
        return {
            "configured": True,
            "message": f"Failed to connect to YouTube API: {str(e)}",
            "recommendations": []
        }
