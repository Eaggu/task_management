from fastapi import Depends, APIRouter,HTTPException,File, UploadFile
from sqlalchemy import exists
from sqlalchemy.orm import Session
from model import PositionModel
from database import SessionLocal, engine
from schema import PositionSchema
import model
from typing import List
from datetime import datetime
import uuid
import csv
from sqlalchemy.exc import IntegrityError
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
@router.post("/api/v1/position/create", summary="Tạo vị trí",dependencies=[Depends(JWTBearer().has_role([1]))])
async def create_position(
    positionSchema: PositionSchema,
    db: Session = Depends(get_database_session),
):
    position_exists = db.query(exists().where(PositionModel.name == positionSchema.name)).scalar()
    if position_exists:
        raise HTTPException(status_code=400, detail="Vị trí đã tồn tại")

    # Create a new ProductSchema instance and add it to the database
    new_position = PositionModel(
        id=str(uuid.uuid4()).replace('-', '')[:8],
        name=positionSchema.name,
        role=positionSchema.role,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    db.add(new_position)
    db.commit()
    db.refresh(new_position)
    return {"message": "Tạo vị trí thành công"}

# Sủa loại sản phẩm
@router.put("/api/v1/position/update/{position_id}", summary="Cập nhật vị trí",dependencies=[Depends(JWTBearer().has_role([1,2]))])
async def update_postion(
    position_id: str,
    position_update: PositionSchema,
    db: Session = Depends(get_database_session),
):
    existing_position = db.query(PositionModel).filter(PositionModel.id == position_id).first()
    if not existing_position:
        raise HTTPException(status_code=404, detail="Vị trí không tồn tại!")

    existing_position.name = position_update.name
    existing_position.role = position_update.role
    existing_position.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    existing_position.deleted_at =None

  
    db.commit()
    db.refresh(existing_position)

    return {"message": "Chỉnh sửa vị trí thành công"}

#Hoàn tác xoá vị trí
@router.put("/api/v1/position/undo_delete/{position_id}", summary="Hoàn tác xóa vị trí",dependencies=[Depends(JWTBearer().has_role([1,2]))])
async def undo_delete_category(position_id: str, db: Session = Depends(get_database_session)):
    existing_position = db.query(PositionModel).filter(PositionModel.id == position_id).first()
    if not existing_position:
        raise HTTPException(status_code=404, detail=f"Vị trí không tồn tại!")
    existing_position.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    db.commit()

    return {"message": "Hoàn tác xoá vị trí thành công"}
#Lấy tất cả loại sản phẩm
@router.get("/api/v1/position/all", summary="Lấy tất cả vị trí",dependencies=[Depends(JWTBearer().has_role([1,2]))])
def get_category(
    db: Session = Depends(get_database_session),
):
    positions = (
    db.query(PositionModel).all()

    )
    return positions
@router.get("/api/v1/position/{position_id}", summary="Lấy một vị trí",dependencies=[Depends(JWTBearer().has_role([1,2]))])
def get_category(
    position_id: str,
    db: Session = Depends(get_database_session),
):
    positions = (
    db.query(PositionModel).filter(PositionModel.id==position_id).first()
    )
    return  positions
#Xóa loại sản phẩm
@router.delete("/api/v1/position/delete/{position_id}", summary="Xóa vị trí",dependencies=[Depends(JWTBearer().has_role([1,2]))])
async def delete_category(position_id: str, db: Session = Depends(get_database_session)):
    existing_position = db.query(PositionModel).filter(PositionModel.id == position_id).first()
    if not existing_position:
        raise HTTPException(status_code=404, detail=f"Vị trí không tồn tại!")
    existing_position.deleted_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    db.commit()

    return {"message": "Xoá vị trí thành công"}