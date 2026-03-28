# --- SET AWS CREDENTIALS BEFORE ANY IMPORTS ---
import os

import json
import boto3
from dotenv import load_dotenv
from pydantic_ai import Agent
from fastapi import FastAPI, File, UploadFile, Form
import uvicorn

# Import the specialized tools
import tools 

load_dotenv()

# --- CREATE BOTO3 CLIENT WITH EXPLICIT CREDENTIALS ---
_bedrock_client = None

def get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name='us-west-2',
            aws_access_key_id='ASIAXWDKBRAVU62VY27K',
            aws_secret_access_key='CC58xXajGdIbIpph9pXm84yJGcJUJQxgUd3+YNMTd',
            aws_session_token='IQoJb3JpZ2luX2VjEPz//////////wEaCXVzLXdlc3QtMiJGMEQCIGvLzGFYIxg65/QjHb+u+KL6JddfgWXe+UstlTi8IRl1AiALAUoVTUgvst3PRuKussFUTVy0wEBZtKVrGAYzkKCQoSqtAwjF//////////8BEAEaDDUyODUwMzM3NTkxNSIMsCtnC2IUjosHD8pZKoEDuP9qxSjuFXOtkShVERM5T4uaepS5VgdUnY2umQrfW+ODZPtiJSGYSABKl0FQ8Z1PHEU2xQPwsU5CQOoOd7Yt0chkel+JT0h1GcdRoZi98+P+r6DN9dUVg9QyTwnOJUh+HhtAHehAXgHeLdbm6ToG7fFeLFACD5PqVQ2R59ATlCua9/4HY2XhH5r/4py3TESJkmrkuM0ZIUekaKhFcCTC6Bv/jV7kttJpz+7lJsGbLEKNPyEfK3HqGGi2SFErYpQYs1bp4CcFjIjXMjIWz1tFG6kaJLxuEMZlozHlBBY6S9+7GTGawdM1PebytIMGYVb0VwRlSqHnxzy3IKPySmRwEAVmSl3BjbNMMaR8ST5Rdgu2P4RhDa5uR8m1sAfm/XGWppyrq7Y4wQ9ED4DAVjYKVuG+tFGHskWlF6plqv8aya8papoiXp5mr7eyC+aSHII4YzVNvTLwnQGJewgaI2VFYge3lxngXW8cmt1NfGs3LXKBHZn0xYtA+HaYQk6beEvC7TCksJTOBjqlAY9EicKn43w6avwuYKw2MddnW8ZXpKxWRoerPvDaFW3dcgSoU4gHhIOdGt7dZD/r5J0I4F8wgsycczre7QLqpCrI9/l0mD8l57P31Or1FTLszOZbcodkaoLEQOPnMMDT59ZIc0vVE2+57kBn8w63c86gvEsmSWLJiPu4tXemHg3m7kCFr7AzuVmDB3O1NQobsFnRjJ8YBo9WD0ENvzxWUi58VZDwgg=='
        )
    return _bedrock_client

# --- THE MASTER DEVOPS ARCHITECT LOGIC ---
devops_agent = Agent(
    'bedrock:anthropic.claude-3-5-sonnet-20241022-v2:0',
    system_prompt=(
        "You are an elite autonomous Senior DevOps Architect. Follow this strict protocol:\n"
        "1. AUDIT: Use 'analyze_repository' on the Git URL. Check 'existing_requirements_content'.\n"
        "2. DESIGN: Analyze the BRD, FRD, and existing code to decide the infrastructure:\n"
        "   - compute_type: Choose 'ecs' (for web apps/APIs) or 'lambda' (for scripts/triggers).\n"
        "   - storage_type: Choose 'rds' (SQL), 'dynamodb' (NoSQL), or 's3' (Files).\n"
        "   - use_load_balancer: Set to true if it's a public API or high-traffic app.\n"
        "3. MERGE: Keep Git versions from the audit. Add missing dependencies from BRD/FRD.\n"
        "4. EXECUTE:\n"
        "   - Use 'write_project_file' for the final 'requirements.txt'.\n"
        "   - Use 'generate_dockerfile' for the container logic.\n"
        "   - Use 'provision_aws_infrastructure' by passing your architectural choices as a JSON string.\n"
        "5. SHIP (NEW AGENTIC STEP): Once infrastructure is validated, use 'push_image_to_registry'.\n"
        "   - You must provide the project_name as 'repo_name'.\n"
        "   - Pass a JSON string matching 'RegistrySchema' (aws_account_id, repo_name, region).\n"
        "   - Use '123456789012' as the placeholder AWS Account ID if none is found in docs.\n"
        "6. REPORT: Explain WHY you chose the specific storage and compute types and confirm the image push."
    )
)

# Register tools from tools.py
devops_agent.tool_plain(tools.analyze_repository)
devops_agent.tool_plain(tools.plan_infrastructure)
devops_agent.tool_plain(tools.generate_dockerfile)
devops_agent.tool_plain(tools.run_vulnerability_scan)
devops_agent.tool_plain(tools.generate_ci_cd_pipeline)
devops_agent.tool_plain(tools.provision_aws_infrastructure)
devops_agent.tool_plain(tools.push_image_to_registry) # NEW: Registered Registry Tool
devops_agent.tool_plain(tools.deploy_application_to_aws)
devops_agent.tool_plain(tools.validate_deployment)
devops_agent.tool_plain(tools.write_project_file)

app = FastAPI(
    title="DevOps Architect API v2.5", 
    description="Unified Agentic API for Infra Design, Validation, and Docker Registry Management.",
    version="2.5.0"
)

@app.get("/")
def health_check():
    return {"status": "online", "message": "Architect is ready for full-cycle deployment!"}

@app.post("/architect-project")
async def architect_and_deploy(
    project_name: str = Form(...),
    repo_url: str = Form(...),
    brd_file: UploadFile = File(...),
    frd_file: UploadFile = File(...)
):
    """Master Endpoint: Audits Git, Merges Docs, Dynamically Designs AWS, and Pushes Docker Image."""
    print(f"\n🚀 STARTING FULL AGENTIC PIPELINE: {project_name}")
    print("-" * 50)
    
    try:
        # Read the uploaded business and technical documents
        brd_text = (await brd_file.read()).decode('utf-8')
        frd_text = (await frd_file.read()).decode('utf-8')
        
        # Give the Agent the full context to make its decisions
        user_prompt = (
            f"Project Name: {project_name}\n"
            f"GitHub Repo: {repo_url}\n\n"
            f"--- BRD (Business Requirements) ---\n{brd_text}\n\n"
            f"--- FRD (Technical Requirements) ---\n{frd_text}\n\n"
            "Analyze the code and docs. Determine the best compute and storage types. "
            "Generate the requirements, design the AWS infra, and push the Docker image to the registry."
        )
        
        # Execute the Agentic Loop
        result = await devops_agent.run(user_prompt)
        print("🏁 Pipeline Execution Complete.")
        
        return {
            "status": "success", 
            "project": project_name, 
            "agent_report": result.output
        }
        
    except Exception as e:
        print(f"\n❌ Pipeline failed: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    print("="*50)
    print("🤖 DEVOPS ARCHITECT API v2.5 STARTING...")
    print("Endpoint: http://localhost:8000/docs")
    print("="*50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
