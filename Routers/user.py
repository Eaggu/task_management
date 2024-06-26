from fastapi import Depends, Header,APIRouter
from sqlalchemy.orm import Session
from auth.auth_handler import decodeJWT
from model import UserModel,PositionModel
from database import SessionLocal, engine
import model
from auth.auth_handler import JWTBearer

router = APIRouter()  
model.Base.metadata.create_all(bind=engine)


def get_database_session():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

@router.get("/user", dependencies=[Depends(JWTBearer().has_role([1, 2, 3]))])
async def get_user(
    authorization: str = Header(...),
    db: Session = Depends(get_database_session),
):
    # Decode JWT to get user information
    user = decodeJWT(authorization.split()[1])
    email = user.get("email")

    # Query the database to get the user along with the position name
    user_data = db.query(UserModel, PositionModel).join(PositionModel, UserModel.position_id == PositionModel.id).filter(UserModel.email == email).first()

    if user_data:
        user, position = user_data
        return {
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "address": user.address,
                "gender": user.gender,
                "dob": user.dob,
                "avatar": user.avatar,
                "position": position
            }
        }
    else:
        return {"error": "User not found"}, 404