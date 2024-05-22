from fastapi import Depends, APIRouter,HTTPException
from sqlalchemy import exists
from sqlalchemy.orm import Session,aliased
from model import TaskModel,StatusModel,TagModel,UserModel,TaskHasTagModel
from database import SessionLocal, engine
from schema import TaskSchema,TaskUpdateSchema
import model
from datetime import datetime
import uuid
from auth.auth_handler import JWTBearer

router = APIRouter()  
model.Base.metadata.create_all(bind=engine)


def get_database_session():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
custome_uuid=str(uuid.uuid4()).replace('-', '')[:8]

#Thêm loại sản phẩm
@router.post("/api/v1/task/create", summary="Tạo công việc", dependencies=[Depends(JWTBearer().has_role([1, 2, 3]))])
async def create_task(
    taskSchema: TaskSchema,
    db: Session = Depends(get_database_session),
):
    # Retrieve the default status id
    status_default = db.query(StatusModel).filter(StatusModel.name == "Cần làm").first().id

    # Create a new task instance
    new_task = TaskModel(
        id=str(uuid.uuid4()).replace('-', '')[:8],
        name=taskSchema.name,
        start_time=taskSchema.start_time,
        end_time=taskSchema.end_time,
        status_id=status_default,
        assigner=taskSchema.assigner,
        carrier=taskSchema.carrier,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    # Process the tags
    if taskSchema.tag:
        for tag in taskSchema.tag:
            task_has_tag = TaskHasTagModel(
                task_id=new_task.id,
                tag_id=tag.tag_id,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            db.add(task_has_tag)

    db.commit()

    return {"message": "Tạo công việc thành công", "task_id": new_task.id}

# Sủa loại sản phẩm
@router.put("/api/v1/task/update/{task_id}", summary="Cập nhật công việc", dependencies=[Depends(JWTBearer().has_role([1, 2, 3]))])
async def update_task(
    task_id: str,
    taskUpdateSchema: TaskUpdateSchema,
    db: Session = Depends(get_database_session),
):
    # Retrieve the existing task
    task = db.query(TaskModel).filter(TaskModel.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Update task fields if provided
    if taskUpdateSchema.name:
        task.name = taskUpdateSchema.name
    if taskUpdateSchema.start_time:
        task.start_time = taskUpdateSchema.start_time
    if taskUpdateSchema.end_time:
        task.end_time = taskUpdateSchema.end_time
    if taskUpdateSchema.assigner:
        task.assigner = taskUpdateSchema.assigner
    if taskUpdateSchema.carrier:
        task.carrier = taskUpdateSchema.carrier
    task.updated_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    # Process the tags
    if taskUpdateSchema.tag is not None:
        # Delete existing task tags
        db.query(TaskHasTagModel).filter(TaskHasTagModel.task_id == task_id).delete()
        # Add new tags
        for tag in taskUpdateSchema.tag:
            task_has_tag = TaskHasTagModel(
                task_id=task_id,
                tag_id=tag.tag_id,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            db.add(task_has_tag)

    db.commit()
    db.refresh(task)

    return {"message": "Cập nhật công việc thành công", "task_id": task.id}


@router.put("/api/v1/task/undo_delete/{task_id}", summary="Hoàn tác xoá công việc",dependencies=[Depends(JWTBearer().has_role([1,2,3]))])
async def delete_task(status_id: str, db: Session = Depends(get_database_session)):
    existing_task= db.query(TaskModel).filter(TaskModel.id == status_id).first()
    if not existing_task:
        raise HTTPException(status_code=404, detail=f"Công việc không tồn tại!")
    existing_task.deleted_at = None

    db.commit()

    return {"message": "Hoàn tác xoá công việc thành công"}
#Lấy tất cả loại sản phẩm

@router.get("/api/v1/task/all", summary="Lấy tất cả công việc", dependencies=[Depends(JWTBearer().has_role([1,2,3]))])
def get_all_tasks(
    db: Session = Depends(get_database_session),
):
    # Alias the UserModel to distinguish between assigner and carrier
    Assigner = aliased(UserModel)
    Carrier = aliased(UserModel)

    # Query the database to fetch all tasks along with their status, assigner, and carrier information
    tasks = (
        db.query(TaskModel, StatusModel, Assigner, Carrier)
        .join(StatusModel, TaskModel.status_id == StatusModel.id)
        .join(Assigner, TaskModel.assigner == Assigner.id)
        .join(Carrier, TaskModel.carrier == Carrier.id)
        .all()
    )

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")

    all_tasks = []

    for task in tasks:
        task_model, status_model, assigner, carrier = task

        # Query to get all tags associated with the task
        tags = (
            db.query(TagModel)
            .join(TaskHasTagModel, TagModel.id == TaskHasTagModel.tag_id)
            .filter(TaskHasTagModel.task_id == task_model.id, TaskHasTagModel.deleted_at == None)
            .all()
        )

        all_tasks.append({
            "id": task_model.id,
            "start_time": task_model.start_time,
            "end_time": task_model.end_time,
            "name": task_model.name,
            "description":task_model.description,
            "assigner": {
                "id": assigner.id,
                "name": assigner.name,
            },
            "carrier": {
                "id": carrier.id,
                "name": carrier.name,
            },
            "status": {
                "id": status_model.id,
                "name": status_model.name,
            },
            "tags": [{"id": tag.id, "name": tag.name} for tag in tags],
            "created_at": task_model.created_at,
            "deleted_at": task_model.deleted_at,
            "updated_at": task_model.updated_at
        })

    # Construct and return the response dictionary
    return  all_tasks
@router.get("/api/v1/task/{task_id}", summary="Lấy một công việc", dependencies=[Depends(JWTBearer().has_role([1]))])
def get_task_by_id(
    task_id: str,
    db: Session = Depends(get_database_session),
):
    # Alias the UserModel to distinguish between assigner and carrier
    Assigner = aliased(UserModel)
    Carrier = aliased(UserModel)

    # Query the database to fetch the task along with its status, assigner, and carrier information
    task = (
        db.query(TaskModel, StatusModel, Assigner, Carrier)
        .join(StatusModel, TaskModel.status_id == StatusModel.id)
        .join(Assigner, TaskModel.assigner == Assigner.id)
        .join(Carrier, TaskModel.carrier == Carrier.id)
        .filter(TaskModel.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_model, status_model, assigner, carrier = task

    # Query to get all tags associated with the task
    tags = (
        db.query(TagModel)
        .join(TaskHasTagModel, TagModel.id == TaskHasTagModel.tag_id)
        .filter(TaskHasTagModel.task_id == task_id)
        .all()
    )

    # Construct and return the response dictionary
    return {
        "id": task_model.id,
        "start_time": task_model.start_time,
        "end_time": task_model.end_time,
        "name": task_model.name,
        "assigner": {
            "id": assigner.id,
            "name": assigner.name,
        },
        "carrier": {
            "id": carrier.id,
            "name": carrier.name,
        },
        "status": {
            "id": status_model.id,
            "name": status_model.name,
        },
        "tags": [{"id": tag.id, "name": tag.name} for tag in tags],
        "created_at": task_model.created_at,
        "deleted_at": task_model.deleted_at,
        "updated_at": task_model.updated_at,
    }

#Xóa loại sản phẩm
@router.delete("/api/v1/task/delete/{task_id}", summary="Xóa công việc",dependencies=[Depends(JWTBearer().has_role([1]))])
async def delete_task(status_id: str, db: Session = Depends(get_database_session)):
    existing_task= db.query(TaskModel).filter(TaskModel.id == status_id).first()
    if not existing_task:
        raise HTTPException(status_code=404, detail=f"Công việc không tồn tại!")
    existing_task.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    db.commit()

    return {"message": "Xoá công việc thành công"}