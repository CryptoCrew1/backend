from bson import ObjectId
from fastapi import FastAPI, HTTPException, status, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.youthchain


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)


# Define the request model
class AddressRequest(BaseModel):
    ethereumAddress: str


# Define the user data model
class UserData(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    surname: str
    ethereumAddress: str
    projects: List[str]
    events: List[str]
    watchlist: List[str]


# Define the response model
class ApiResponse(BaseModel):
    success: bool
    status_code: int
    data: Optional[UserData] = None


@app.post("/check-user", response_model=ApiResponse)
async def check_user(address_request: AddressRequest):
    user = await db.users.find_one({"ethereumAddress": address_request.ethereumAddress})
    if user:
        user_data = UserData(
            name=user['name'],
            surname=user['surname'],
            ethereumAddress=user['ethereumAddress'],
            projects=user.get('projects', []),
            events=user.get('events', []),
            watchlist=user.get('watchlist', [])
        )
        return ApiResponse(success=True, status_code=status.HTTP_200_OK, data=user_data)
    else:
        return ApiResponse(success=False, status_code=status.HTTP_404_NOT_FOUND)


class Project(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    Category: str
    City: str
    Industry: str
    ImageUrl: str
    DaysLeft: int
    ProjectName: str
    Raised: int
    Investors: int
    Votes: int
    MinInvestment: int
    Slogan: str


# Helper function to parse MongoDB ObjectId
def serialize_data(data):
    data['id'] = str(data['_id'])
    del data['_id']
    return data


@app.get("/getProjects", response_model=List[Project])
async def get_projects(category: str = Query(..., description="The project category")):
    cursor = db.projects.find({"Category": category})
    projects = await cursor.to_list(length=100)  # Adjust the length as needed
    return [serialize_data(project) for project in projects]


@app.post("/postProjects", status_code=201)
async def add_project(project: Project):
    new_project = await db.projects.insert_one(project.dict())
    if new_project.inserted_id:
        project.id = str(new_project.inserted_id)
        return project
    raise HTTPException(status_code=400, detail="Error inserting project")


@app.get("/projects/by-user/{ethereum_address}", response_model=List[Project])
async def get_projects_by_user(ethereum_address: str):
    user = await db.users.find_one({"ethereumAddress": ethereum_address})
    if not user or "projects" not in user:
        raise HTTPException(status_code=404, detail="User or projects not found")

    if "projects" not in user or not user["projects"]:
        return []

    project_ids = [PyObjectId(id) for id in user["projects"]]
    projects_cursor = db.projects.find({"_id": {"$in": project_ids}})
    projects = await projects_cursor.to_list(None)
    return [Project(**project) for project in projects]


class Event(BaseModel):
    id: Optional[str]
    eventName: str
    eventDescription: str
    startDate: str
    endDate: str
    location: str
    img: str
    mainSpeaker: str
    rules: str
    votes: int
    neededVotes: int
    category: str


@app.get("/events", response_model=List[Event])
async def get_events_by_category(eventCategory: str = Query(..., description="The project category")):
    if eventCategory is None:
        raise HTTPException(status_code=400, detail="Event category header missing")

    events_cursor = db.events.find({"category": eventCategory})
    events = await events_cursor.to_list(None)
    return [Event(**serialize_data(event)) for event in events]
