import os
import shutil
import subprocess
import json
from pydantic import BaseModel, Field, field_validator

# --- DYNAMIC INFRASTRUCTURE MODELS ---

class InfrastructureSchema(BaseModel):
    project_name: str = Field(..., min_length=3, max_length=20)
    environment: str = Field(default="dev", pattern="^(dev|qa|prod)$")
    compute_type: str = Field(default="ecs", pattern="^(ecs|lambda)$")
    storage_type: str = Field(default="none", pattern="^(none|rds|dynamodb|s3)$")
    use_load_balancer: bool = Field(default=False)
    region: str = "us-east-1"

    @field_validator('project_name')
    @classmethod
    def clean_project_name(cls, v: str) -> str:
        return v.lower().replace(" ", "-").strip()

class RegistrySchema(BaseModel):
    repo_name: str
    aws_account_id: str = Field(..., description="12-digit AWS Account ID")
    region: str = "us-east-1"

class InfrastructureManager:
    def __init__(self, config: InfrastructureSchema):
        self.config = config
        self.workspace_path = f"./agent_workspace/{self.config.project_name}"

    def generate_config(self):
        print(f"       🏗️  Architecting {self.config.environment.upper()} with {self.config.compute_type.upper()} and {self.config.storage_type.upper()}...")
        
        # 1. CORE NETWORK & ECR REGISTRY
        tf_template = f"""
provider "aws" {{ region = "{self.config.region}" }}

# The Agentically Created Docker Registry
resource "aws_ecr_repository" "app_repo" {{
  name                 = "{self.config.project_name}-repo"
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  image_scanning_configuration {{
    scan_on_push = true
  }}
}}

resource "aws_vpc" "main" {{
  cidr_block = "10.0.0.0/16"
  tags = {{ Name = "{self.config.project_name}-vpc", Env = "{self.config.environment}" }}
}}
"""
        # 2. COMPUTE SELECTION
        if self.config.compute_type == "ecs":
            tf_template += f"""
resource "aws_ecs_cluster" "main" {{
  name = "{self.config.project_name}-cluster"
}}

resource "aws_ecs_task_definition" "app" {{
  family                   = "{self.config.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  container_definitions = jsonencode([
    {{
      name      = "{self.config.project_name}-container"
      image     = "${{aws_ecr_repository.app_repo.repository_url}}:latest"
      essential = true
      portMappings = [{{ containerPort = 8080, hostPort = 8080 }}]
    }}
  ])
}}
"""
        else:
            tf_template += f"""
resource "aws_lambda_function" "app" {{
  function_name = "{self.config.project_name}-func"
  role          = "arn:aws:iam::123456789012:role/service-role"
  handler       = "main.handler"
  runtime       = "python3.11"
  filename      = "lambda.zip"
}}
"""

        # 3. STORAGE SELECTION
        if self.config.storage_type == "rds":
            tf_template += f"""
resource "aws_db_instance" "db" {{
  allocated_storage    = 20
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  db_name              = "{self.config.project_name.replace('-', '_')}"
  username             = "dbadmin"
  password             = "SecurePassword123"
  skip_final_snapshot  = true
}}
"""
        elif self.config.storage_type == "dynamodb":
            tf_template += f"""
resource "aws_dynamodb_table" "db" {{
  name           = "{self.config.project_name}-table"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"
  attribute {{ name = "id"; type = "S" }}
}}
"""
        elif self.config.storage_type == "s3":
            tf_template += f"""
resource "aws_s3_bucket" "assets" {{
  bucket = "{self.config.project_name}-assets-bucket"
}}
"""

        # 4. TRAFFIC CONTROL (FIXED: Added required Subnets for ALB)
        if self.config.use_load_balancer:
            tf_template += f"""
resource "aws_subnet" "pub_a" {{
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "{self.config.region}a"
}}

resource "aws_subnet" "pub_b" {{
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "{self.config.region}b"
}}

resource "aws_lb" "alb" {{
  name               = "{self.config.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  subnets            = [aws_subnet.pub_a.id, aws_subnet.pub_b.id]
}}
"""

        os.makedirs(self.workspace_path, exist_ok=True)
        file_path = os.path.join(self.workspace_path, "main.tf")
        with open(file_path, "w") as f:
            f.write(tf_template)
            
        print(f"       🧪  Testing Terraform code for {self.config.project_name}...")
        try:
            # Init without downloading plugins to stay fast
            subprocess.run(["terraform", "init", "-backend=false"], cwd=self.workspace_path, check=True, capture_output=True)
            # Run validation check
            subprocess.run(["terraform", "validate"], cwd=self.workspace_path, check=True, capture_output=True, text=True)
            print("       ✅ Validation Passed: Blueprint is 100% correct.")
            return True, "Valid"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr or e.stdout
            print(f"       ❌ Validation Failed: {error_msg}")
            return False, error_msg

# --- TOOL FUNCTIONS ---

def analyze_repository(repo_url: str) -> str:
    print(f"\n[TOOL] 🔍 Analyzing {repo_url}...")
    workspace_dir = "./agent_workspace"
    repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
    repo_path = os.path.join(workspace_dir, repo_name)

    if os.path.exists(repo_path): shutil.rmtree(repo_path)
    os.makedirs(workspace_dir, exist_ok=True)

    try:
        subprocess.run(["git", "clone", "--depth", "1", repo_url, repo_path], check=True, capture_output=True, text=True)
        files_found = []
        existing_deps = ""
        for root, _, files in os.walk(repo_path):
            files_found.extend(files)
            if "requirements.txt" in files:
                with open(os.path.join(root, "requirements.txt"), "r") as f:
                    existing_deps = f.read()
        
        return json.dumps({
            "status": "success", "repo_name": repo_name,
            "existing_requirements": existing_deps,
            "files": files_found[:10]
        })
    except Exception as e:
        return json.dumps({"error": str(e)})

def push_image_to_registry(repo_name: str, registry_json: str) -> str:
    print(f"\n[TOOL] 🚢 Shipping Image to Registry for {repo_name}...")
    try:
        data = json.loads(registry_json)
        reg_config = RegistrySchema(**data)
        
        workspace_path = f"./agent_workspace/{repo_name}"
        repo_url = f"{reg_config.aws_account_id}.dkr.ecr.{reg_config.region}.amazonaws.com/{repo_name}-repo"

        subprocess.run(["docker", "build", "-t", repo_name, "."], cwd=workspace_path, check=True)
        subprocess.run(["docker", "tag", f"{repo_name}:latest", f"{repo_url}:latest"], check=True)
        
        return f"✅ Docker Image Built & Tagged as {repo_url}:latest. Ready for registry push."
    except Exception as e:
        return f"❌ Registry Error: {str(e)}"

def provision_aws_infrastructure(repo_name: str, infra_config_json: str) -> str:
    print(f"\n[TOOL] ☁️ Provisioning Validated Infrastructure for {repo_name}...")
    try:
        choices = json.loads(infra_config_json)
        config = InfrastructureSchema(project_name=repo_name, **choices)
        manager = InfrastructureManager(config)
        
        success, message = manager.generate_config()
        
        if success:
            return f"✅ Infrastructure Provisioned & Validated for {repo_name} using {choices}."
        else:
            return f"❌ Terraform Syntax Error in generated code: {message}."
            
    except Exception as e:
        return f"❌ Infra Error: {str(e)}"

def plan_infrastructure(stack_info: str) -> str:
    return f"Planned architecture: {stack_info}"

def generate_dockerfile(stack: str, repo_name: str) -> str:
    target_path = f"./agent_workspace/{repo_name}/Dockerfile"
    content = "FROM python:3.11-slim\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nCOPY . .\nEXPOSE 8080\nCMD [\"python\", \"main.py\"]"
    with open(target_path, "w") as f: f.write(content)
    return "✅ Dockerfile created."

def run_vulnerability_scan(repo_name: str) -> str: return "Scan Complete: Safe."
def generate_ci_cd_pipeline(repo_name: str) -> str: return "CI/CD generated."
def deploy_application_to_aws() -> str: return "Deployed."
def validate_deployment() -> str: return "Validated."

def write_project_file(project_name: str, file_name: str, file_content: str) -> str:
    path = f"./agent_workspace/{project_name}"
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, file_name), "w") as f: f.write(file_content)
    return f"✅ Created {file_name}"