"""
Bedrock Service - Interface for AWS LLM
"""
import boto3
import json
import os
from typing import Dict, Any

class BedrockService:
    def __init__(self):
        # Initialize AWS Client (Requires .env credentials)
        self.client = boto3.client(
            'bedrock-runtime',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.model_id = 'us.anthropic.claude-3-sonnet-20240229-v1:0'

    def generate_insight(self, analytics_summary: str, user_query: str = None) -> str:
        """
        Sends store context to Claude and gets a manager-level insight.
        """
        
        # 1. System Prompt (The Persona)
        system_prompt = (
            "You are an AI Retail Manager Assistant for 'Minimart'. "
            "You have access to real-time computer vision data describing customer locations. "
            "Your job is to interpret this data into actionable business insights. "
            "Be concise, professional, and focus on store operations (staffing, queues, security)."
        )

        # 2. User Prompt (The Data + Question)
        prompt_content = f"""
        REAL-TIME STORE DATA:
        {analytics_summary}
        
        USER REQUEST:
        {user_query if user_query else "Analyze the current store status and identify any issues."}
        """

        # 3. Payload Construction (Claude 3 Structure)
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt_content}
            ]
        })

        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=body
            )
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            print(f"❌ Bedrock Error: {e}")
            return "Unable to access AI insights. Please check AWS configuration."