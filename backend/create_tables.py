from app.database.session import engine
from app.database.base import Base

# Import all models so SQLAlchemy knows about them
from app.database.models import User
from app.database.models import ChatSession
from app.database.models import ChatMessage

Base.metadata.create_all(bind=engine)

print("Tables created successfully")