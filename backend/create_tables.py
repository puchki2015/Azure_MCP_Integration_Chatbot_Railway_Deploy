from app.database.session import engine
from app.database.base import Base

# Import all models so SQLAlchemy knows about them
from app.database.models import User
from app.database.models import ChatSession
from app.database.models import ChatMessage
from app.database.models import SessionMemory
from app.database.models import ApprovalRequest
from app.database.models import ApprovalActionLog
from app.database.models import AuditLog
from app.database.models import PricingLookupKey
from app.database.models import PricingSnapshot
from app.database.models import PriceRefreshRun
from app.database.models import CostEstimate
from app.database.models import CostEstimateLine

Base.metadata.create_all(bind=engine)

print("Tables created successfully")
