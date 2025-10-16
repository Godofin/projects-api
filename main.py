from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
import uuid
import os

# Importações para Supabase e .env
from supabase import create_client, Client
from dotenv import load_dotenv

# Importa o CORSMiddleware
from fastapi.middleware.cors import CORSMiddleware

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Cria a instância da aplicação FastAPI
app = FastAPI(
    title="API de Controle de Projetos com Supabase",
    description="Uma API para gerenciar o tempo e o faturamento de projetos, integrada ao Supabase.",
    version="1.1.0"
)

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- Conexão com Supabase ---
try:
    url: str = "https://ghnqlsnjbeckzxidfesh.supabase.co"
    key: str = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImdobnFsc25qYmVja3p4aWRmZXNoIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjAxMDAyMjgsImV4cCI6MjA3NTY3NjIyOH0.ey9UD0CNm4vByVhZ6oSfgmZxXV9Ma6GVC_8aYbh1N7g"

    if not url or not key:
        raise ValueError("As variáveis de ambiente SUPABASE_URL e SUPABASE_KEY são necessárias.")
    supabase: Client = create_client(url, key)
    print("Conexão com Supabase bem-sucedida!")
except Exception as e:
    print(f"Erro ao conectar com Supabase: {e}")
    supabase = None

# --- Modelos de Dados (Pydantic) ---
class ProjectCreate(BaseModel):
    project_name: str = Field(..., example="Dashboard de Vendas")
    task_owner: str = Field(..., example="Maria Souza")
    project_type: str = Field(..., example="Engenharia de Dados")
    start_time: datetime
    end_time: datetime
    hourly_rate: float = Field(..., gt=0)

class Project(ProjectCreate):
    id: uuid.UUID
    created_at: datetime
    duration_minutes: Optional[float] = None
    total_value: Optional[float] = None


# --- Endpoints da API ---

@app.post("/projects/", response_model=Project, status_code=201, summary="Cria um novo projeto no Supabase")
async def create_project(project_data: ProjectCreate):
    """
    Cria um novo registro de projeto e o salva no banco de dados Supabase.
    Calcula automaticamente a duração e o valor total.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Conexão com o banco de dados não configurada.")
    
    if project_data.end_time <= project_data.start_time:
        raise HTTPException(status_code=400, detail="A hora de fim deve ser posterior à hora de início.")

    duration_delta = project_data.end_time - project_data.start_time
    duration_minutes = duration_delta.total_seconds() / 60
    total_value = (duration_minutes / 60) * project_data.hourly_rate

    project_to_insert = project_data.model_dump()
    project_to_insert.update({
        "duration_minutes": duration_minutes,
        "total_value": total_value
    })
    
    # Converte datetimes para string no formato ISO para compatibilidade
    project_to_insert['start_time'] = project_to_insert['start_time'].isoformat()
    project_to_insert['end_time'] = project_to_insert['end_time'].isoformat()

    try:
        response = supabase.table("projects").insert(project_to_insert).execute()
        
        if len(response.data) == 0:
            raise HTTPException(status_code=500, detail="Falha ao criar o projeto no banco de dados.")
            
        return response.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Supabase: {str(e)}")


@app.get("/projects/", response_model=List[Project], summary="Lista todos os projetos do Supabase")
async def get_all_projects():
    """
    Retorna uma lista com todos os projetos registrados no Supabase, ordenados pelo mais recente.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Conexão com o banco de dados não configurada.")
        
    try:
        response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no Supabase: {str(e)}")

@app.get("/projects/{project_id}", response_model=Project, summary="Busca um projeto por ID")
async def get_project_by_id(project_id: uuid.UUID):
    """
    Obtém os detalhes de um projeto específico pelo seu ID.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Conexão com o banco de dados não configurada.")

    try:
        response = supabase.table("projects").select("*").eq("id", str(project_id)).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Projeto não encontrado.")
        return response.data[0]
    except Exception as e:
        # Evita expor detalhes do erro, mas diferencia 404 de outros erros.
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Erro no Supabase: {str(e)}")


@app.delete("/projects/{project_id}", status_code=204, summary="Deleta um projeto do Supabase")
async def delete_project(project_id: uuid.UUID):
    """
    Remove um projeto do banco de dados com base no seu ID.
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Conexão com o banco de dados não configurada.")

    try:
        response = supabase.table("projects").delete().eq("id", str(project_id)).execute()
        
        # Se a lista de dados estiver vazia, significa que o ID não foi encontrado para deletar
        if not response.data:
            raise HTTPException(status_code=404, detail="Projeto não encontrado para deletar.")
            
        return {} # Retorna uma resposta vazia com status 204
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Erro no Supabase: {str(e)}")


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Bem-vindo à API de Controle de Projetos. Acesse /docs para ver a documentação."}

