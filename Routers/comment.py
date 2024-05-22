from fastapi import Depends, APIRouter,HTTPException
from sqlalchemy import exists
from sqlalchemy.orm import Session
from model import CommentModel,UserModel,TaskModel
from database import SessionLocal, engine
from schema import CommentSchema
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

#Thêm loại sản phẩm
@router.post("/api/v1/comment/create", summary="Tạo Comment",dependencies=[Depends(JWTBearer().has_role([1,2,3]))])
async def create_comment(
    commmentSchema: CommentSchema,
    db: Session = Depends(get_database_session),
):
    new_comment = CommentModel(
        id=str(uuid.uuid4()).replace('-', '')[:8],  
        message=commmentSchema.message,
        task_id=commmentSchema.task_id,
        user_id=commmentSchema.user_id,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    return {"message": "Tạo comment thành công"}

# Sủa loại sản phẩm
@router.put("/api/v1/comment/update/{comment_id}", summary="Cập nhật Comment",dependencies=[Depends(JWTBearer().has_role([1,2,3]))])
async def update_tag(
    comment_id: str,
    comment_update: CommentSchema,
    db: Session = Depends(get_database_session),
):
    existing_comment = db.query(CommentModel).filter(CommentModel.id == comment_id).first()
    if not existing_comment:
        raise HTTPException(status_code=404, detail="Comment không tồn tại!")

    existing_comment.message = comment_update.message
    existing_comment.task_id = comment_update.task_id
    existing_comment.user_id = comment_update.user_id
    existing_comment.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    existing_comment.deleted_at =None

  
    db.commit()
    db.refresh(existing_comment)

    return {"message": "Chỉnh sửa Comment thành công"}

#Lấy tất cả loại sản phẩm
@router.get("/api/v1/comments_in_task/{task_id}", summary="Lấy tất cả comment theo task", dependencies=[Depends(JWTBearer().has_role([1, 2, 3]))])
def get_comments_in_task(
    task_id: str,
    db: Session = Depends(get_database_session),
):
    comments = (
        db.query(CommentModel)
        .join(UserModel, CommentModel.user_id == UserModel.id)
        .join(TaskModel, CommentModel.task_id == TaskModel.id)
        .filter(CommentModel.task_id == task_id)
        .all()
    )
    
    if not comments:
        raise HTTPException(status_code=404, detail="No comments found")
    
    all_comments = []
    for comment in comments:
        user = db.query(UserModel).filter(UserModel.id == comment.user_id).first()
        task = db.query(TaskModel).filter(TaskModel.id == comment.task_id).first()
        
        all_comments.append({
            "id": comment.id,
            "message": comment.message,
            "task_id": comment.task_id,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "avatar": user.avatar,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "deleted_at": user.deleted_at,
            },
            "created_at": comment.created_at,
            "updated_at": comment.updated_at,
        })
    
    return all_comments
@router.get("/api/v1/comment/{task_id}/{comment_id}", summary="Lấy một comment",dependencies=[Depends(JWTBearer().has_role([1]))])
def get_comment_by_id(
    comment_id: str,
    db: Session = Depends(get_database_session),
):
    comment = (
    db.query(CommentModel).filter(CommentModel.id==comment_id).first()
    )
    return comment
#Xóa loại sản phẩm
@router.delete("/api/v1/comment/delete/{comment_id}", summary="Xóa Comment",dependencies=[Depends(JWTBearer().has_role([1]))])
async def delete_comment(comment_id:str, db: Session = Depends(get_database_session)):
    existing_comment= db.query(CommentModel).filter(CommentModel.id == comment_id).first()

    if not existing_comment:
        raise HTTPException(status_code=404, detail=f"Comment không tồn tại!")
    existing_comment.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    db.commit()

    return {"message": "Xoá Comment thành công"}