import boto3
import json
import os
from dotenv import load_dotenv

# Load keys from .env
load_dotenv()

def test_connection():
    print("🔌 Connecting to AWS Bedrock...")
    
    try:
        client = boto3.client(
            'bedrock-runtime',
            region_name=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        )
        
        # Test Prompt
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Hello! Confirm you are online and ready for retail analytics."}
            ]
        }

        response = client.invoke_model(
            modelId='us.anthropic.claude-3-sonnet-20240229-v1:0',
            body=json.dumps(payload)
        )
        
        result = json.loads(response['body'].read())
        print("\n✅ SUCCESS! Response from Claude:")
        print("-" * 40)
        print(result['content'][0]['text'])
        print("-" * 40)

    except Exception as e:
        print("\n❌ CONNECTION FAILED")
        print(f"Error: {e}")
if __name__ == "__main__":
    test_connection()