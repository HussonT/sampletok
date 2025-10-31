from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class StripeCustomer(Base):
    """
    Links Sampletok users to Stripe customer IDs.
    One user = one Stripe customer (1:1 relationship).
    """
    __tablename__ = "stripe_customers"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # One Stripe customer per user
    )

    # Stripe details
    stripe_customer_id = Column(String(255), nullable=False, unique=True)
    email = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="stripe_customer")

    # Indexes
    __table_args__ = (
        Index('idx_stripe_customer_user', 'user_id'),
        Index('idx_stripe_customer_stripe_id', 'stripe_customer_id'),
    )

    def __repr__(self):
        return f"<StripeCustomer(id={self.id}, user_id={self.user_id}, stripe_customer_id={self.stripe_customer_id})>"
