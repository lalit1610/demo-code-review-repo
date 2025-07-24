import os
import boto3
import json
import requests

# Initialize Bedrock client with your AWS region
bedrock = boto3.client('bedrock', region_name=os.getenv('BEDROCK_REGION'))

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
PR_NUMBER = os.getenv('PR_NUMBER')

def get_pr_changed_files():
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    url = f'https://api.github.com/repos/{GITHUB_REPO}/pulls/{PR_NUMBER}/files'
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()

def call_bedrock_model(code_snippet):
    prompt = f"""
You are an expert software engineer giving a code review for the below code snippet:

{code_snippet}

List:
1. Code quality issues
2. Potential bugs or security vulnerabilities
3. Recommendations to improve performance and readability.
"""

    response = bedrock.invoke_model(
        ModelId='anthropic.claude-instant-v1',  # choose appropriate model ID
        ContentType='application/json',
        Accept='application/json',
        Body=json.dumps({
            'prompt': prompt,
            'max_tokens_to_sample': 500
        })
    )
    result = json.loads(response['Body'].read().decode())
    return result['completion']

def post_comment(path, line, body):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{PR_NUMBER}/comments"
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github+json'
    }
    commit_sha = get_latest_commit_sha()
    payload = {
        "body": body,
        "commit_id": commit_sha,
        "path": path,
        "line": line,
        "side": "RIGHT"
    }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()

def get_latest_commit_sha():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/pulls/{PR_NUMBER}"
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    return resp.json()['head']['sha']

def main():
    files = get_pr_changed_files()

    for file in files:
        path = file['filename']
        patch = file.get('patch')
        if not patch:
            # Skip non-text or binary files
            continue

        # Call Bedrock model to get review feedback
        feedback = call_bedrock_model(patch)

        # Post comment on line 1 of the file for demo purposes
        post_comment(path, 1, feedback)
        print(f"Posted review comment on file: {path}")

if __name__ == "__main__":
    main()
