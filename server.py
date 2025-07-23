from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import fal_client
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class VideoRequest(BaseModel):
    prompt: str
    duration: Optional[int] = 5  # duration in seconds, default 5
    
class VideoResponse(BaseModel):
    id: str
    prompt: str
    status: str
    video_url: Optional[str] = None
    created_at: datetime
    
class VideoGeneration(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prompt: str
    duration: int = 5
    status: str = "processing"  # processing, completed, failed
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

# Video generation endpoint
@api_router.post("/generate-video", response_model=VideoResponse)
async def generate_video(request: VideoRequest):
    # Create video generation record
    video_gen = VideoGeneration(
        prompt=request.prompt,
        duration=request.duration
    )
    
    # Save to database
    await db.video_generations.insert_one(video_gen.dict())
    
    try:
        # Check if FAL_KEY is available
        fal_key = os.environ.get('FAL_KEY')
        if not fal_key:
            # For demo purposes, simulate video generation
            import time
            await asyncio.sleep(2)  # Simulate processing time
            
            # Update record with demo video
            demo_video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            await db.video_generations.update_one(
                {"id": video_gen.id},
                {
                    "$set": {
                        "status": "completed",
                        "video_url": demo_video_url,
                        "completed_at": datetime.utcnow(),
                        "error_message": "Demo mode - using sample video (FAL_KEY not provided)"
                    }
                }
            )
            
            return VideoResponse(
                id=video_gen.id,
                prompt=request.prompt,
                status="completed",
                video_url=demo_video_url,
                created_at=video_gen.created_at
            )
        
        # Try to generate video using fal.ai
        try:
            # Use text-to-video model (Hunyuan Video is available on fal.ai)
            handler = await fal_client.submit_async(
                "fal-ai/hunyuan-video",
                arguments={
                    "prompt": request.prompt,
                    "duration": request.duration
                }
            )
            
            result = await handler.get()
            
            video_url = result.get("video", {}).get("url") if result.get("video") else None
            
            if video_url:
                # Update database with success
                await db.video_generations.update_one(
                    {"id": video_gen.id},
                    {
                        "$set": {
                            "status": "completed",
                            "video_url": video_url,
                            "completed_at": datetime.utcnow()
                        }
                    }
                )
                
                return VideoResponse(
                    id=video_gen.id,
                    prompt=request.prompt,
                    status="completed",
                    video_url=video_url,
                    created_at=video_gen.created_at
                )
            else:
                raise Exception("No video URL returned from fal.ai")
                
        except Exception as fal_error:
            logger.error(f"FAL.AI error: {str(fal_error)}")
            # Fall back to demo mode
            demo_video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
            await db.video_generations.update_one(
                {"id": video_gen.id},
                {
                    "$set": {
                        "status": "completed",
                        "video_url": demo_video_url,
                        "completed_at": datetime.utcnow(),
                        "error_message": f"FAL.AI error, using demo: {str(fal_error)}"
                    }
                }
            )
            
            return VideoResponse(
                id=video_gen.id,
                prompt=request.prompt,
                status="completed",
                video_url=demo_video_url,
                created_at=video_gen.created_at
            )
            
    except Exception as e:
        logger.error(f"Video generation error: {str(e)}")
        # Update database with error
        await db.video_generations.update_one(
            {"id": video_gen.id},
            {
                "$set": {
                    "status": "failed",
                    "error_message": str(e),
                    "completed_at": datetime.utcnow()
                }
            }
        )
        raise HTTPException(status_code=500, detail=str(e))

# Get video status
@api_router.get("/video/{video_id}", response_model=VideoResponse)
async def get_video_status(video_id: str):
    video = await db.video_generations.find_one({"id": video_id})
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return VideoResponse(
        id=video["id"],
        prompt=video["prompt"],
        status=video["status"],
        video_url=video.get("video_url"),
        created_at=video["created_at"]
    )

# Get all videos
@api_router.get("/videos", response_model=List[VideoResponse])
async def get_all_videos(limit: int = 10):
    videos = await db.video_generations.find().sort("created_at", -1).limit(limit).to_list(limit)
    return [
        VideoResponse(
            id=video["id"],
            prompt=video["prompt"],
            status=video["status"],
            video_url=video.get("video_url"),
            created_at=video["created_at"]
        ) for video in videos
    ]

# Original status check endpoints
@api_router.get("/")
async def root():
    return {"message": "AI Video Generator API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()