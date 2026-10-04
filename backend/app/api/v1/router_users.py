from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.user import UserOut, UserUpdate
from app.services import user_service
from pydantic import BaseModel
from sqlalchemy import select
from app.models.user import User
from app.models.social import PetProfile
from app.schemas.social import PrivacyUpdate, PetUpdate, UserSearchOut

router = APIRouter(prefix="/users", tags=["users"])
me_router = APIRouter(prefix="/me", tags=["users"])


@router.get("/me", response_model=UserOut)
def read_me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, user: CurrentUser, db: DbSession):
    return user_service.update_user(db, user, data)

@router.get("/search", response_model=list[UserSearchOut])
def search_users(email: str, db: DbSession, user: CurrentUser):
    users = db.scalars(
        select(User).where(User.email.ilike(f"%{email}%"), User.id != user.id)
    ).all()
    return [{"id": u.id, "name": u.name or u.email.split("@")[0]} for u in users]

@me_router.patch("/privacy")
def update_privacy(data: PrivacyUpdate, user: CurrentUser, db: DbSession):
    user.share_pet = data.share_pet
    db.commit()
    return {"share_pet": user.share_pet}

@me_router.put("/pet")
def update_pet(data: PetUpdate, user: CurrentUser, db: DbSession):
    pet = db.scalar(select(PetProfile).where(PetProfile.user_id == user.id))
    
    if not pet:
        pet = PetProfile(user_id=user.id, name=data.name or "My Pet")
        db.add(pet)
    
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(pet, key, value)
        
    db.commit()
    db.refresh(pet)
    return pet
