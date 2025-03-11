import io
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

import openai
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Depends, BackgroundTasks, Form, Query
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy.orm import Session
from fastapi.staticfiles import StaticFiles

from core.markitdown import MarkItDown
from core.base import DocumentConverterResult
from core.model_manager import ModelConfigurator
from repository.db import get_db, Job

# 安全验证
security = HTTPBearer()

# 从环境变量获取API密钥
API_KEY = os.getenv("MARKIT_API_KEY", "secret-key")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)
port = int(os.getenv("PORT", 20926))

# 依赖项：API Key 验证
async def verify_api_key(
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    if credentials.scheme != "Bearer" or credentials.credentials != API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
    return credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动和关闭时的生命周期管理"""
    try:
        # 初始化模型
        configurator = ModelConfigurator(device=os.getenv("DEVICE", "cpu"))
        configurator.setup_environment()
        print("模型初始化完成")
    except Exception as e:
        print(f"模型初始化失败: {str(e)}")
        raise

    yield  # 应用运行期间

    # 清理逻辑（可选）
    print("服务关闭，清理资源...")


# FastAPI 应用
app = FastAPI(lifespan=lifespan)
if not os.path.exists("output/images"):
    os.mkdir("output/images")
app.mount("/images", StaticFiles(directory="output/images"), name="images")


# 数据模型
class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    filename: str
    params: dict
    error: Optional[str]


class JobResultResponse(BaseModel):
    job_id: str
    download_url: str
    format: str


oai_client = None
if os.getenv("MARKIFY_LLM_API_KEY", None) and os.getenv("MARKIFY_LLM_API_BASE", None):
    oai_client = openai.OpenAI(
        api_key=os.getenv("MARKIFY_LLM_API_KEY", None),
        base_url=os.getenv("MARKIFY_LLM_API_BASE", None)
    )


def process_file(db: Session, job_id: str, file_content: bytes, filename: str, mode: str = "simple"):
    """处理各种文件的后台任务"""
    try:
        # 更新任务状态为 processing
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = "processing"
        db.commit()

        # 创建处理器
        markitdown = MarkItDown(
            mode=mode,
            llm_client=oai_client,
            llm_model=os.getenv("MARKIFY_LLM_MODEL", None)
        )

        # 根据输入类型处理
        if filename.endswith('.md'):
            result = DocumentConverterResult(text_content=file_content.decode('utf-8'))
        else:
            # 将字节内容转为文件流
            file_stream = io.BytesIO(file_content)
            result = markitdown.convert_stream(file_stream, base_url="http://localhost:20926")

        # 保存结果到文件
        output_file = OUTPUT_DIR / f"{job_id}.md"
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result.text_content)

        # 更新任务状态为 completed
        job.status = "completed"
        job.result_file = str(output_file)
        db.commit()

    except Exception as e:
        # 更新任务状态为 failed
        job.status = "failed"
        job.error = f"{type(e).__name__}: {str(e)}"
        db.commit()


@app.post("/api/jobs", status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        mode: str = Form("simple"),
        db: Session = Depends(get_db)
):
    """上传文件并启动转换任务"""
    # 生成任务ID
    job_id = str(uuid.uuid4())

    try:
        # 读取文件内容
        content = await file.read()

        # 创建任务记录
        job = Job(
            id=job_id,
            filename=file.filename,
            params={"mode": mode},
            status="pending"
        )
        db.add(job)
        db.commit()

        # 启动后台任务
        background_tasks.add_task(
            process_file,
            db=db,
            job_id=job_id,
            file_content=content,
            filename=file.filename,
            mode=mode
        )

        return {"job_id": job_id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"File upload failed: {str(e)}"
        )


@app.get("/api/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
        db: Session = Depends(get_db),
        page: int = Query(0, ge=0, description=""),
        limit: int = Query(10, gt=0, le=100, description="default 10，max 100")
):
    """查询任务状态"""
    jobs = db.query(Job).order_by(Job.created_at.desc()).limit(limit).offset(page * limit).all()
    if not jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    response_list = []
    for job in jobs:
        response_list.append(JobStatusResponse(
            job_id=job.id,
            status=job.status,
            filename=job.filename,
            params=job.params,
            error=job.error
        ))
    return response_list


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
        job_id: str,
        db: Session = Depends(get_db)
):
    """查询任务状态"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return JobStatusResponse(
        job_id=job.id,
        status=job.status,
        filename=job.filename,
        params=job.params,
        error=job.error
    )


@app.get("/api/jobs/{job_id}/result")
async def download_result(
        job_id: str,
        db: Session = Depends(get_db)
):
    """下载任务结果文件"""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail="Job not completed"
        )

    result_file = job.result_file
    if not result_file or not os.path.exists(result_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result file not found"
        )

    # 返回文件内容
    return FileResponse(
        result_file,
        filename=f"{job.filename}.md",
        media_type="text/markdown"
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)