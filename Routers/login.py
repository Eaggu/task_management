from fastapi import Depends, Form,status,APIRouter,UploadFile,File
from fastapi.responses import JSONResponse
from sqlalchemy import exists
import base64
from sqlalchemy.orm import Session
from auth.auth_handler import signJWT,JWTBearer
from model import UserModel,PositionModel
from datetime import datetime
import uuid
from schema import UserSchema
import shutil
import os
# import schema
from database import SessionLocal, engine
import model
from passlib.context import CryptContext
from pydantic import BaseModel

router = APIRouter()  
model.Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_database_session():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()
        
class UserLogin(BaseModel):
    email: str
    password: str

@router.post("/api/v1/signup", summary="Đăng ký")
async def create_account(
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    position_id: str = Form(),
    phone: str = Form(),
    address: str = Form(),
    gender: int = Form(),
    dob: str = Form(),
    avatar: UploadFile = File(None),
    db: Session = Depends(get_database_session)
):
    user_exists = db.query(exists().where(UserModel.email == email)).scalar()
    if user_exists:
        return JSONResponse(status_code=400, content={"message": "Tài khoản bị trùng"})
    elif len(password) < 6:
        return JSONResponse(status_code=400, content={"message": "Mật khẩu tối thiểu là 6 ký tự"})
    hashed_password = pwd_context.hash(password)

    # Ensure the directory exists
    os.makedirs("images", exist_ok=True)

    avatar_filepath = None
    if avatar:
        # Save the uploaded avatar file
        avatar_filename = f"{str(uuid.uuid4()).replace('-', '')[:10]}.png"
        avatar_filepath = f"images/{avatar_filename}"
        with open(avatar_filepath, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

    new_user = UserModel(
        id=str(uuid.uuid4()).replace('-', '')[:8],
        name=name,
        email=email,
        password=hashed_password,
        phone=phone,
        address=address,
        gender=gender,
        avatar=avatar_filepath,
        position_id=position_id,
        dob=dob,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "data": "Tài khoản đã được tạo thành công!"
    }

@router.post("/api/v1/login", status_code=status.HTTP_200_OK, summary="Đăng nhập")
async def login(user_login: UserLogin, db: Session = Depends(get_database_session)):
    email = user_login.email
    password = user_login.password

    if password == '1':
        return JSONResponse(status_code=400, content={"message": "Sai mật khẩu"})
    user_exists = db.query(exists().where(UserModel.email == email)).scalar()
    user = db.query(UserModel).filter(UserModel.email == email).first()
    if not user_exists:
        return JSONResponse(status_code=400, content={"message": "Không có tài khoản"})
    elif not pwd_context.verify(password, user.password):
        return JSONResponse(status_code=400, content={"message": "Sai mật khẩu"})
    else:
        role = db.query(PositionModel).filter(PositionModel.id == user.position_id).first().role
        return signJWT(email, user.id, role)  

@router.get("/admin",dependencies=[Depends(JWTBearer().has_role([2]))])
async def read_admin_data():
    return {"msg": "This is admin data"}

@router.get("/user1", dependencies=[Depends(JWTBearer().has_role([2, 1]))])
async def read_user_data():
    return {"msg": "This is user data"}


# @router.post("/api/v1/refresh")
# async def refresh_token(refresh_token: str):
#     return refresh_access_token(refresh_token)

#Đổi mật khẩu
@router.put("/api/v1/change_password", dependencies=[Depends(JWTBearer().has_role([2, 1]))], summary="Đổi mật khẩu")
async def change_password(
    db: Session = Depends(get_database_session),
    email: str = Form(...),
    old_password: str = Form(...),
    new_password: str = Form(...),
    new_confirm_password: str = Form(...)
):
    Duser = db.query(UserModel).filter(UserModel.email == email).first()

    if Duser is None:
        return JSONResponse(status_code=404, content={"message": "Người dùng không tồn tại!"})
    if not pwd_context.verify(old_password, Duser.password):
        return JSONResponse(status_code=400, content={"message": "Sai mật khẩu!"})
    if new_password != new_confirm_password:
        return JSONResponse(status_code=400, content={"message": "Mật khẩu xác nhận không khớp!"})
    if len(new_password) < 6:
        return JSONResponse(status_code=400, content={"message": "Mật khẩu quá ngắn!"})
    hashed_new_password = pwd_context.hash(new_password)
    Duser.password = hashed_new_password
    db.commit()
    db.refresh(Duser)
    return JSONResponse(status_code=200, content={"message": "Đổi mật khẩu thành công!"})