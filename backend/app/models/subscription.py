from sqlalchemy import Column, String, DateTime, Boolean, Integer, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Subscription(Base):
    """
    Stores user subscription details including Stripe integration,
    billing period, and subscription status.

    Note: Only one active subscription per user (enforced by UNIQUE constraint on user_id).
    """
    __tablename__ = "subscriptions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True  # Only one subscription per user
    )

    # Stripe details
    stripe_subscription_id = Column(String(255), nullable=False, unique=True)
    stripe_customer_id = Column(String(255), nullable=False)

    # Plan details
    tier = Column(String(20), nullable=False)  # 'basic', 'pro', 'ultimate'
    billing_interval = Column(String(10), nullable=False)  # 'month', 'year'
    monthly_credits = Column(Integer, nullable=False)  # Monthly credit allowance (100, 400, 1500)

    # Status
    status = Column(String(20), nullable=False)  # 'active', 'past_due', 'unpaid', 'cancelled', 'incomplete'
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)

    # Billing period
    current_period_start = Column(DateTime, nullable=False)
    current_period_end = Column(DateTime, nullable=False)

    # Pricing
    stripe_price_id = Column(String(255), nullable=False)  # e.g., price_xxx (CRITICAL for tracking)
    amount_cents = Column(Integer, nullable=False)  # e.g., 2999 for $29.99
    currency = Column(String(3), default='USD', nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription")
    credit_transactions = relationship("CreditTransaction", back_populates="subscription", cascade="all, delete-orphan")

    # Indexes and Constraints
    __table_args__ = (
        Index('idx_subscription_user', 'user_id'),
        Index('idx_subscription_stripe_id', 'stripe_subscription_id'),
        Index('idx_subscription_status', 'status'),
        Index('idx_subscription_period_end', 'current_period_end'),
        # Constraint: Ensure cancelled subscriptions have cancellation timestamp
        CheckConstraint(
            "(status = 'cancelled' AND cancelled_at IS NOT NULL) OR (status != 'cancelled')",
            name='check_cancelled_at'
        ),
    )

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, tier={self.tier}, status={self.status})>"

    @property
    def is_active(self) -> bool:
        """Check if subscription is active (user has platform access)"""
        return self.status in ['active', 'past_due']

    @property
    def is_renewable(self) -> bool:
        """Check if subscription can be renewed (not cancelled)"""
        return self.status not in ['cancelled', 'incomplete']
