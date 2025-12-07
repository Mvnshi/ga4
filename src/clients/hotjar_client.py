"""
Hotjar API Client
==================
Hotjar integration for user behavior and feedback data.

Hotjar provides:
- Survey responses
- Feedback widget data
- NPS scores
- User sentiment

Note: Hotjar's API is primarily for feedback data.
Heatmaps and recordings require dashboard access.

API Documentation: https://help.hotjar.com/hc/en-us/articles/360033640653-Hotjar-API
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import requests

from config.settings import ClientConfig, get_settings
from src.utils.cache import cached


@dataclass
class SurveyResponse:
    """A single survey response."""
    response_id: str
    survey_id: str
    survey_name: str
    submitted_at: str
    answers: Dict[str, Any]
    page_url: str
    device: str
    country: str


@dataclass
class FeedbackItem:
    """A single feedback widget response."""
    feedback_id: str
    emotion: str  # happy, neutral, sad
    message: str
    page_url: str
    submitted_at: str
    device: str


class HotjarClient:
    """
    Hotjar API client for survey and feedback data.
    
    Requires:
    - Hotjar Site ID
    - Personal Access Token (from Hotjar dashboard)
    
    Rate limits are generous for survey data.
    """
    
    API_BASE = "https://api.hotjar.com/v1"
    
    def __init__(
        self,
        client_config: ClientConfig,
        site_id: str = None,
        api_token: str = None
    ):
        """
        Initialize Hotjar client.
        
        Args:
            client_config: Client configuration
            site_id: Hotjar Site ID (from Hotjar dashboard)
            api_token: Personal Access Token
        """
        self.config = client_config
        self.client_name = client_config.name
        self.site_id = site_id
        self.api_token = api_token
        self._settings = get_settings()
        
        # Check if Hotjar is configured
        self.is_configured = bool(site_id and api_token)
        
        if self.is_configured:
            self.headers = {
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
            }
    
    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Dict = None,
        data: Dict = None
    ) -> Optional[Dict[str, Any]]:
        """Make an API request to Hotjar."""
        if not self.is_configured:
            return None
        
        url = f"{self.API_BASE}/sites/{self.site_id}/{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                print("    ⚠️ Hotjar authentication failed - check API token")
                return None
            elif response.status_code == 404:
                print("    ⚠️ Hotjar resource not found - check Site ID")
                return None
            else:
                print(f"    ⚠️ Hotjar API error: {response.status_code}")
                return None
                
        except requests.RequestException as e:
            print(f"    ⚠️ Hotjar request failed: {e}")
            return None
    
    @cached(ttl_hours=24)
    def get_surveys(self) -> List[Dict[str, Any]]:
        """Get list of all surveys."""
        if not self.is_configured:
            return []
        
        data = self._make_request("surveys")
        if data:
            return data.get("data", [])
        return []
    
    @cached(ttl_hours=12)
    def get_survey_responses(
        self,
        survey_id: str,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[SurveyResponse]:
        """
        Get responses for a specific survey.
        
        Args:
            survey_id: Hotjar survey ID
            start_date: Filter from date (YYYY-MM-DD)
            end_date: Filter to date (YYYY-MM-DD)
            limit: Max responses to return
        
        Returns:
            List of SurveyResponse objects
        """
        if not self.is_configured:
            return []
        
        params = {"limit": limit}
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date
        
        data = self._make_request(f"surveys/{survey_id}/responses", params=params)
        
        if not data:
            return []
        
        responses = []
        for item in data.get("data", []):
            responses.append(SurveyResponse(
                response_id=str(item.get("id", "")),
                survey_id=survey_id,
                survey_name=item.get("survey_name", ""),
                submitted_at=item.get("created_at", ""),
                answers=item.get("answers", {}),
                page_url=item.get("page_url", ""),
                device=item.get("device", "unknown"),
                country=item.get("country", ""),
            ))
        
        return responses
    
    @cached(ttl_hours=12)
    def get_feedback(
        self,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[FeedbackItem]:
        """
        Get feedback widget responses.
        
        Args:
            start_date: Filter from date (YYYY-MM-DD)
            end_date: Filter to date (YYYY-MM-DD)
            limit: Max items to return
        
        Returns:
            List of FeedbackItem objects
        """
        if not self.is_configured:
            return []
        
        params = {"limit": limit}
        if start_date:
            params["from"] = start_date
        if end_date:
            params["to"] = end_date
        
        data = self._make_request("feedback", params=params)
        
        if not data:
            return []
        
        feedback = []
        for item in data.get("data", []):
            feedback.append(FeedbackItem(
                feedback_id=str(item.get("id", "")),
                emotion=item.get("emotion", "neutral"),
                message=item.get("message", ""),
                page_url=item.get("page_url", ""),
                submitted_at=item.get("created_at", ""),
                device=item.get("device", "unknown"),
            ))
        
        return feedback
    
    def get_feedback_summary(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get summarized feedback data for a period.
        
        Returns sentiment breakdown and common themes.
        """
        if not self.is_configured:
            return {"available": False, "reason": "Hotjar not configured"}
        
        feedback = self.get_feedback(start_date, end_date, limit=500)
        
        if not feedback:
            return {
                "available": True,
                "total_responses": 0,
                "sentiment": {},
            }
        
        # Sentiment breakdown
        sentiment_counts = {"happy": 0, "neutral": 0, "sad": 0}
        for item in feedback:
            emotion = item.emotion.lower()
            if emotion in sentiment_counts:
                sentiment_counts[emotion] += 1
        
        total = len(feedback)
        sentiment_pct = {
            k: round(v / total * 100, 1) if total > 0 else 0
            for k, v in sentiment_counts.items()
        }
        
        # Calculate NPS-like score
        # happy = promoters, sad = detractors
        nps = sentiment_pct.get("happy", 0) - sentiment_pct.get("sad", 0)
        
        # Recent feedback messages (for qualitative insights)
        recent_messages = [
            {"emotion": f.emotion, "message": f.message[:200], "page": f.page_url}
            for f in feedback[:20]
            if f.message
        ]
        
        return {
            "available": True,
            "total_responses": total,
            "sentiment": sentiment_counts,
            "sentiment_pct": sentiment_pct,
            "nps_estimate": round(nps, 1),
            "recent_feedback": recent_messages,
        }
    
    def get_survey_summary(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get summarized survey data for a period.
        """
        if not self.is_configured:
            return {"available": False, "reason": "Hotjar not configured"}
        
        surveys = self.get_surveys()
        
        if not surveys:
            return {
                "available": True,
                "total_surveys": 0,
                "total_responses": 0,
            }
        
        total_responses = 0
        survey_data = []
        
        for survey in surveys[:5]:  # Limit to 5 most recent surveys
            survey_id = str(survey.get("id", ""))
            survey_name = survey.get("name", "Unnamed Survey")
            
            responses = self.get_survey_responses(survey_id, start_date, end_date)
            
            survey_data.append({
                "name": survey_name,
                "responses": len(responses),
            })
            total_responses += len(responses)
        
        return {
            "available": True,
            "total_surveys": len(surveys),
            "total_responses": total_responses,
            "surveys": survey_data,
        }
    
    def get_all_insights(
        self,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """
        Get all available Hotjar insights for a period.
        
        This is the main method to call for quarterly reports.
        """
        if not self.is_configured:
            return {
                "available": False,
                "reason": "Hotjar not configured - add site_id and api_token to client config"
            }
        
        print("    📊 Fetching Hotjar feedback...")
        feedback = self.get_feedback_summary(start_date, end_date)
        
        print("    📋 Fetching Hotjar surveys...")
        surveys = self.get_survey_summary(start_date, end_date)
        
        return {
            "available": True,
            "feedback": feedback,
            "surveys": surveys,
            "summary": {
                "total_feedback": feedback.get("total_responses", 0),
                "total_survey_responses": surveys.get("total_responses", 0),
                "sentiment_score": feedback.get("nps_estimate", 0),
                "happy_pct": feedback.get("sentiment_pct", {}).get("happy", 0),
            }
        }


class HotjarClientDisabled:
    """
    Placeholder client when Hotjar is not configured.
    
    Returns empty/safe values for all methods to prevent errors.
    """
    
    def __init__(self, *args, **kwargs):
        self.is_configured = False
    
    def get_surveys(self) -> List:
        return []
    
    def get_survey_responses(self, *args, **kwargs) -> List:
        return []
    
    def get_feedback(self, *args, **kwargs) -> List:
        return []
    
    def get_feedback_summary(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Hotjar not configured"}
    
    def get_survey_summary(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Hotjar not configured"}
    
    def get_all_insights(self, *args, **kwargs) -> Dict:
        return {"available": False, "reason": "Hotjar not configured"}


def create_hotjar_client(
    client_config: ClientConfig,
    site_id: str = None,
    api_token: str = None
) -> HotjarClient:
    """
    Factory function to create appropriate Hotjar client.
    
    Returns disabled client if credentials not provided.
    """
    if site_id and api_token:
        return HotjarClient(client_config, site_id, api_token)
    return HotjarClientDisabled()

