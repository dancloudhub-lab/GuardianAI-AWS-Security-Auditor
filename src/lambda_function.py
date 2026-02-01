import boto3
import json
import os
import logging

# Set up logging for production visibility
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    GuardianAI: Analyzes AWS CloudTrail events using Amazon Bedrock 
    and sends security recommendations via SNS.
    """
    
    # Initialize AWS Clients
    bedrock = boto3.client('bedrock-runtime')
    sns = boto3.client('sns')
    
    # Retrieve environment variables (Production Best Practice)
    sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
    
    try:
        # 1. Extract Event Data
        # We capture the specific IP permissions changed in the Security Group
        detail = event.get('detail', {})
        request_params = detail.get('requestParameters', {})
        ip_permissions = request_params.get('ipPermissions', 'No specific rule found')
        
        logger.info(f"Analyzing security change: {ip_permissions}")

        # 2. Construct the Engineering Prompt
        # We define a "System Role" to ensure the AI behaves like a Security Expert
        prompt = (
            f"Human: You are a Senior AWS Security Architect. "
            f"Analyze this Security Group rule change: {ip_permissions}. "
            f"Identify potential risks, reference the SAA-C03 Security Pillar "
            f"(specifically Infrastructure Protection), and provide the "
            f"exact AWS CLI command to revoke this rule if it's unsafe. "
            f"Assistant:"
        )

        # 3. Invoke Amazon Bedrock (Claude 3 Haiku)
        # Using Haiku for high-speed, low-cost security triage
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        })

        response = bedrock.invoke_model(
            body=body,
            modelId='anthropic.claude-3-haiku-20240307-v1:0'
        )
        
        # Parse AI Response
        response_body = json.loads(response.get('body').read())
        ai_advice = response_body['content'][0]['text']

        # 4. Publish to SNS
        sns.publish(
            TopicArn=sns_topic_arn,
            Subject="🚨 GuardianAI: Risky Security Group Change Detected",
            Message=(
                f"GuardianAI Security Analysis\n"
                f"{'='*30}\n\n"
                f"Event Source: {detail.get('eventSource')}\n"
                f"User Identity: {detail.get('userIdentity', {}).get('arn')}\n\n"
                f"AI Security Recommendation:\n{ai_advice}"
            )
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Analysis successfully delivered."})
        }

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        # Optional: Send a failure notification to SNS so the admin knows the auditor failed
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal Processing Error"})
        }
