from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, DECIMAL, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base
from app.utils import utcnow_naive


class CreditTransaction(Base):
    """
    Tracks all credit movements in the system including subscription grants,
    monthly renewals, top-up purchases, deductions, refunds, and resets.

    Provides full audit trail for credit accounting and reconciliation.
    """
    __tablename__ = "credit_transactions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    # Transaction details
    transaction_type = Column(String(30), nullable=False)
    # Types: 'subscription_grant', 'monthly_renewal', 'top_up_purchase',
    #        'deduction', 'refund', 'cancellation_reset'
    credits_amount = Column(Integer, nullable=False)  # Positive for grants, negative for deductions
    previous_balance = Column(Integer, nullable=False)
    new_balance = Column(Integer, nullable=False)

    # Subscription reference (if applicable)
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True
    )

    # Payment details (for purchases)
    stripe_session_id = Column(String(255), nullable=True)
    stripe_payment_intent_id = Column(String(255), nullable=True)
    stripe_invoice_id = Column(String(255), nullable=True)  # CRITICAL for idempotency
    amount_cents = Column(Integer, nullable=True)
    currency = Column(String(3), default='USD', nullable=True)

    # Top-up details
    top_up_package = Column(String(20), nullable=True)  # 'small', 'medium', 'large'
    discount_applied = Column(DECIMAL(5, 2), nullable=True)  # e.g., 0.10 for 10% off

    # Status
    status = Column(String(20), nullable=False, default='pending')
    # Status: 'pending', 'completed', 'failed', 'refunded'

    # Metadata
    description = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)  # Renamed from 'metadata' (reserved by SQLAlchemy)

    # Related entities
    collection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("collections.id", ondelete="SET NULL"),
        nullable=True
    )
    sample_id = Column(
        UUID(as_uuid=True),
        ForeignKey("samples.id", ondelete="SET NULL"),
        nullable=True
    )
    stem_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stems.id", ondelete="SET NULL"),
        nullable=True
    )

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=utcnow_naive, nullable=False)
    updated_at = Column(DateTime, default=utcnow_naive, onupdate=utcnow_naive, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="credit_transactions")
    subscription = relationship("Subscription", back_populates="credit_transactions")
    collection = relationship("Collection", foreign_keys=[collection_id])
    sample = relationship("Sample", foreign_keys=[sample_id])
    stem = relationship("Stem", foreign_keys=[stem_id])

    # Indexes
    __table_args__ = (
        Index('idx_credit_tx_user', 'user_id'),
        Index('idx_credit_tx_subscription', 'subscription_id'),
        Index('idx_credit_tx_type', 'transaction_type'),
        Index('idx_credit_tx_status', 'status'),
        Index('idx_credit_tx_created', 'created_at'),
        # CRITICAL: Composite indexes for common queries
        Index('idx_credit_tx_user_created', 'user_id', 'created_at'),
        Index('idx_credit_tx_user_type', 'user_id', 'transaction_type'),
        # Partial index for idempotency checks
        Index('idx_credit_tx_stripe_invoice', 'stripe_invoice_id', postgresql_where=Column('stripe_invoice_id').isnot(None)),
    )

    def __repr__(self):
        return (
            f"<CreditTransaction(id={self.id}, user_id={self.user_id}, "
            f"type={self.transaction_type}, amount={self.credits_amount}, status={self.status})>"
        )

    @property
    def is_credit(self) -> bool:
        """Check if transaction adds credits"""
        return self.credits_amount > 0

    @property
    def is_debit(self) -> bool:
        """Check if transaction deducts credits"""
        return self.credits_amount < 0
