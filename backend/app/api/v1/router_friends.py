from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select, and_, or_
from app.core.deps import CurrentUser, DbSession
from app.models.social import Friendship, PetProfile
from app.models.user import User
from app.schemas.social import FriendRequestCreate

router = APIRouter(prefix="/friends", tags=["friends"])

@router.post("/requests", status_code=status.HTTP_201_CREATED)
def send_friend_request(data: FriendRequestCreate, user: CurrentUser, db: DbSession):
    addressee_id = data.user_id
    if addressee_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot befriend yourself.")
    
    addressee = db.get(User, addressee_id)
    if not addressee:
         raise HTTPException(status_code=404, detail="User not found.")

    existing_request = db.scalar(
        select(Friendship).where(
            or_(
                and_(Friendship.requester_id == user.id, Friendship.addressee_id == addressee_id),
                and_(Friendship.requester_id == addressee_id, Friendship.addressee_id == user.id)
            )
        )
    )

    if existing_request:
        raise HTTPException(status_code=409, detail="Friend request already exists or you are already friends.")

    new_friendship = Friendship(requester_id=user.id, addressee_id=addressee_id, status="pending")
    db.add(new_friendship)
    db.commit()
    db.refresh(new_friendship)
    return new_friendship

@router.get("/requests")
def get_requests(user: CurrentUser, db: DbSession):
    incoming = db.scalars(
        select(Friendship).where(and_(Friendship.addressee_id == user.id, Friendship.status == "pending"))
    ).all()
    outgoing = db.scalars(
        select(Friendship).where(and_(Friendship.requester_id == user.id, Friendship.status == "pending"))
    ).all()
    
    return {"incoming": incoming, "outgoing": outgoing}

@router.post("/requests/{friendship_id}/accept")
def accept_request(friendship_id: int, user: CurrentUser, db: DbSession):
    friendship = db.get(Friendship, friendship_id)
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found.")
    
    if friendship.addressee_id != user.id:
         raise HTTPException(status_code=403, detail="You can only accept requests sent to you.")

    friendship.status = "accepted"
    db.commit()
    return {"status": "accepted"}

@router.post("/requests/{friendship_id}/reject")
def reject_request(friendship_id: int, user: CurrentUser, db: DbSession):
    friendship = db.get(Friendship, friendship_id)
    
    if not friendship:
        raise HTTPException(status_code=404, detail="Friend request not found.")
        
    if friendship.addressee_id != user.id:
         raise HTTPException(status_code=403, detail="Permission denied.")

    db.delete(friendship)
    db.commit()
    return {"status": "rejected"}

@router.get("/")
def get_friends(user: CurrentUser, db: DbSession):
    friendships = db.scalars(
        select(Friendship).where(
            and_(
                or_(Friendship.requester_id == user.id, Friendship.addressee_id == user.id),
                Friendship.status == "accepted"
            )
        )
    ).all()
    
    friends_ids = []
    for f in friendships:
        friend_id = f.addressee_id if f.requester_id == user.id else f.requester_id
        friends_ids.append(friend_id)
        
    friends = db.scalars(select(User).where(User.id.in_(friends_ids))).all()
    
    return [{"id": f.id, "name": f.name} for f in friends]

@router.get("/{friend_id}/pet")
def get_friend_pet(friend_id: int, user: CurrentUser, db: DbSession):
    friendship = db.scalar(
         select(Friendship).where(
            and_(
                or_(
                    and_(Friendship.requester_id == user.id, Friendship.addressee_id == friend_id),
                    and_(Friendship.requester_id == friend_id, Friendship.addressee_id == user.id)
                ),
                Friendship.status == "accepted"
            )
        )
    )
    
    if not friendship:
        raise HTTPException(status_code=403, detail="You are not friends.")
        
    friend = db.get(User, friend_id)
    if not friend:
        raise HTTPException(status_code=404, detail="Friend not found.")

    if not friend.share_pet:
         return {}
         
    pet = db.scalar(select(PetProfile).where(PetProfile.user_id == friend_id))
    
    if not pet:
         raise HTTPException(status_code=404, detail="Friend does not have a pet profile.")
         
    return pet

@router.delete("/{friend_id}")
def remove_friend(friend_id: int, user: CurrentUser, db: DbSession):
    friendship = db.scalar(
        select(Friendship).where(
            and_(
                or_(
                    and_(Friendship.requester_id == user.id, Friendship.addressee_id == friend_id),
                    and_(Friendship.requester_id == friend_id, Friendship.addressee_id == user.id)
                ),
                Friendship.status == "accepted"
            )
        )
    )
    
    if not friendship:
        raise HTTPException(status_code=404, detail="You're not a friends.")
        
    db.delete(friendship)
    db.commit()
    return {"status": "deleted"}