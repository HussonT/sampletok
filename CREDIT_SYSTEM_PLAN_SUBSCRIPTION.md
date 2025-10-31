# Subscription-Based Credit System - Comprehensive Implementation Plan

## Executive Summary

This document outlines a **subscription-based credit system** for Sampletok with Stripe integration, following a Splice-style model where:
- Users **must subscribe** to access the platform (no free tier)
- Subscriptions grant **monthly credit allowances** (100-1500 credits/month based on tier)
- Credits **accumulate unlimited** while subscription is active
- Users can **purchase top-up credits** for extra capacity
- On cancellation, users have a **grace period** until billing period ends
- **All credits reset to 0** when subscription ends (enforces re-subscription)

**Business Model Benefits:**
- 💰 Predictable monthly recurring revenue (MRR)
- 📈 Higher customer lifetime value (LTV)
- 🔒 Better retention (credits lost on churn)
- 📊 Cleaner metrics (subscription-based SaaS)

**Implementation Decisions:**
- ✅ Keep all V2 features (annual billing, top-ups, tier changes)
- ✅ Use soft delete for users with active subscriptions
- ❌ No free trials - paid subscriptions only (simpler onboarding)

**Critical Risk Mitigations Implemented:**
- 🔒 **Webhook Race Conditions**: Database locks + idempotency checks prevent duplicate credit grants
- 🔐 **Security**: Strict webhook signature verification + async processing via Inngest
- ⚠️ **Immediate Deletion**: Grace period for active processing before credit reset
- 📊 **Credit Drift**: Weekly reconciliation job detects and corrects accounting errors
- 🗑️ **Soft Delete**: Users with active subscriptions cannot be hard deleted
- 🔑 **Key Changes from Original Plan**:
  - Removed redundant `users.subscription_status` field (use relationship instead)
  - Added `stripe_price_id` to subscriptions table for tracking
  - Added composite indexes for performance (user_id + created_at, user_id + transaction_type)
  - Removed all trial-related code (no trials in MVP)
  - Enhanced credit service with proper locking and idempotency

---

## Table of Contents

1. [Business Model Design](#1-business-model-design)
2. [Subscription Architecture](#2-subscription-architecture)
3. [Credit System Rules](#3-credit-system-rules)
4. [Stripe Integration](#4-stripe-integration)
5. [Database Schema](#5-database-schema)
6. [Backend Implementation](#6-backend-implementation)
7. [Frontend Implementation](#7-frontend-implementation)
8. [User Flows & Edge Cases](#8-user-flows--edge-cases)
9. [Security & Compliance](#9-security--compliance)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment Plan](#11-deployment-plan)
12. [Key Differences from One-Time Purchase Model](#12-key-differences-from-one-time-purchase-model)

---

## 1. Business Model Design

### 1.1 Subscription Tiers

```
┌─────────────────────────────────────────────────────────────┐
│ SUBSCRIPTION PLANS                                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 🥉 BASIC PLAN                                               │
│    $9.99/month or $99/year (save 17%)                       │
│    ├─ 100 credits/month                                     │
│    ├─ Process ~100 TikTok videos/month                      │
│    ├─ Email support                                         │
│    └─ Best for: Individual creators, hobbyists             │
│                                                              │
│ 🥈 PRO PLAN ⭐ MOST POPULAR                                 │
│    $16.99/month or $169/year (save 17%)                     │
│    ├─ 400 credits/month                                     │
│    ├─ Process ~400 TikTok videos/month                      │
│    ├─ Priority email support                                │
│    ├─ 10% discount on top-up credits                        │
│    └─ Best for: Content agencies, power users              │
│                                                              │
│ 🥇 ULTIMATE PLAN                                            │
│    $49.99/month or $498/year (save 17%)                     │
│    ├─ 1500 credits/month                                    │
│    ├─ Process ~1500 TikTok videos/month                     │
│    ├─ Priority support (24h response)                       │
│    ├─ 20% discount on top-up credits                        │
│    ├─ Early access to new features                          │
│    └─ Best for: Businesses, large-scale operations         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Pricing Rationale:**
- $9.99 entry point (~price of 2 coffees) for individual users
- Pro plan at 1.7x price but 4x credits (better value, anchor pricing)
- Ultimate at 5x price but 15x credits (enterprise-level)
- Annual billing saves 17% (2 months free) to encourage longer commitments

### 1.2 Top-Up Credit Packs (For Subscribers Only)

```
┌─────────────────────────────────────────────────────────────┐
│ ONE-TIME TOP-UP CREDITS (Active Subscription Required)     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ Small Pack:     50 credits  → $6.99   ($0.14/credit)       │
│ Medium Pack:   150 credits  → $17.99  ($0.12/credit)       │
│ Large Pack:    500 credits  → $49.99  ($0.10/credit)       │
│                                                              │
│ Note: Pro plan gets 10% discount, Ultimate gets 20%        │
│       Top-up credits lost if subscription cancelled         │
└─────────────────────────────────────────────────────────────┘
```

**Top-Up Strategy:**
- Priced higher than monthly subscription credits (incentivize upgrading tier)
- Discounts for higher-tier subscribers (reward loyalty)
- All top-up credits lost on cancellation (tied to subscription)

### 1.3 Credit Accumulation Model

```
┌─────────────────────────────────────────────────────────────┐
│ CREDIT ACCUMULATION RULES                                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ ✅ WHILE SUBSCRIBED:                                        │
│    • Monthly credits added at start of each billing period  │
│    • Unused credits roll over unlimited                     │
│    • Example: Pro user (400/mo) uses 200 in Month 1        │
│      → Month 2 starts with 200 + 400 = 600 credits         │
│    • Top-up credits also accumulate                         │
│                                                              │
│ ⚠️  ON CANCELLATION:                                        │
│    • Grace period: Keep access until end of billing period  │
│    • At period end: ALL credits reset to 0                  │
│    • Includes: subscription credits + top-up credits        │
│    • Re-subscribing starts fresh with monthly allowance     │
│                                                              │
│ 🔒 ENFORCEMENT:                                             │
│    • No subscription = No platform access                   │
│    • No free tier, no trials - paid subscriptions only      │
│    • Credits shown but locked if subscription inactive      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Subscription Architecture

### 2.1 Subscription Lifecycle

```
┌──────────────────────────────────────────────────────────────┐
│ SUBSCRIPTION STATE MACHINE                                   │
└──────────────────────────────────────────────────────────────┘

[New User]
    ↓
    │ User clicks "Subscribe"
    │ Stripe Checkout processes payment
    ↓
[active]
    │ • Credits granted monthly
    │ • Full platform access
    │ • Process collections/videos
    │
    ├─→ invoice.paid (recurring) → Stay [active], grant credits
    │
    ├─→ User cancels → [active] (cancel_at_period_end = true)
    │                     │
    │                     └─→ period_end → [cancelled] → Credits = 0
    │
    ├─→ invoice.payment_failed → [past_due]
    │                               │
    │                               ├─→ Retry succeeds → [active]
    │                               └─→ Retry fails (after 7 days) → [unpaid] → [cancelled]
    │
    └─→ User upgrades/downgrades → [active] (new tier)

[cancelled]
    │ • No platform access
    │ • Credits = 0
    │ • Can re-subscribe anytime
    │
    └─→ Re-subscribe → [active] (fresh monthly credits)
```

### 2.2 Subscription Status Definitions

| Status | Description | Platform Access | Credits Behavior |
|--------|-------------|-----------------|------------------|
| `active` | Subscription paid and current | ✅ Full access | Monthly credits granted |
| `past_due` | Payment failed, retrying | ✅ Grace period | Keep existing credits |
| `unpaid` | All retry attempts failed | ❌ Locked | Keep credits (visible but locked) |
| `cancelled` | Subscription ended | ❌ Locked | Credits = 0 |
| `incomplete` | Initial payment failed | ❌ No access | No credits |

**Grace Period Logic:**
- `past_due`: Payment failed but still in grace period (7 days of retries)
- During `past_due`: User keeps full access and credits
- If payment succeeds during retries: Back to `active`
- If all retries fail: Moves to `unpaid` → `cancelled`, credits zeroed

---

## 3. Credit System Rules

### 3.1 Credit Sources

```
┌─────────────────────────────────────────────────────────────┐
│ CREDIT ADDITION (How credits are added)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. NEW SUBSCRIPTION                                         │
│    Event: customer.subscription.created                     │
│    Action: Grant initial monthly allowance                  │
│    Example: Subscribe to Pro → +400 credits immediately     │
│                                                              │
│ 2. MONTHLY RENEWAL                                          │
│    Event: invoice.paid (for subscription)                   │
│    Action: Grant monthly allowance                          │
│    Example: Pro renewal → +400 credits (added to existing)  │
│    Note: Accumulates with unused credits                    │
│                                                              │
│ 3. TOP-UP PURCHASE                                          │
│    Event: checkout.session.completed (one-time payment)     │
│    Action: Grant top-up credits immediately                 │
│    Example: Buy 150 credit pack → +150 credits             │
│    Requirement: Must have active subscription               │
│                                                              │
│ 4. REFUND (Rare)                                            │
│    Event: Inngest worker refunds failed video processing    │
│    Action: +1 credit per failed video                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CREDIT DEDUCTION (How credits are used)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. COLLECTION PROCESSING                                    │
│    Cost: 1 credit per video                                 │
│    Charged: Upfront for entire collection                   │
│    Refund: Automatic for failed videos                      │
│                                                              │
│ 2. SINGLE VIDEO PROCESSING (Future)                         │
│    Cost: 1 credit per video                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CREDIT RESET (When credits are zeroed)                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ 1. SUBSCRIPTION CANCELLED                                   │
│    Event: Billing period ends (period_end timestamp)        │
│    Action: Set credits = 0                                  │
│    Scope: ALL credits (subscription + top-ups)              │
│                                                              │
│ 2. SUBSCRIPTION EXPIRED (Non-payment)                       │
│    Event: customer.subscription.deleted                     │
│    Action: Set credits = 0                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Credit Calculation Logic

```python
# Pseudocode for credit balance calculation

def calculate_user_credits(user, subscription):
    """
    Calculate user's credit balance based on subscription status.
    """
    # Check subscription status
    if not subscription or subscription.status in ['cancelled', 'unpaid', 'incomplete']:
        return 0  # No subscription = no credits

    # Active or grace period (past_due)
    if subscription.status in ['active', 'past_due']:
        # Credits accumulate while subscribed
        return user.credits  # Current balance (can be > monthly allowance)

    return 0

def can_process_collection(user, video_count):
    """
    Check if user can process a collection.
    """
    subscription = get_active_subscription(user)

    # Must have active subscription
    if not subscription or subscription.status not in ['active', 'past_due']:
        return False, "Active subscription required"

    # Must have enough credits
    if user.credits < video_count:
        return False, f"Insufficient credits. Need {video_count}, have {user.credits}"

    return True, None
```

---

## 4. Stripe Integration

### 4.1 Stripe Products Configuration

#### In Stripe Dashboard, create:

**1. Subscription Products**

```
Product: "Sampletok Basic Monthly"
├─ Type: Recurring
├─ Price: $9.99/month (recurring)
├─ Billing Period: Monthly
├─ Metadata:
│   ├─ tier: "basic"
│   ├─ monthly_credits: "100"
│   └─ billing_interval: "month"

Product: "Sampletok Basic Annual"
├─ Type: Recurring
├─ Price: $99/year (recurring)
├─ Billing Period: Yearly
├─ Metadata:
│   ├─ tier: "basic"
│   ├─ monthly_credits: "100"
│   └─ billing_interval: "year"

Product: "Sampletok Pro Monthly"
├─ Type: Recurring
├─ Price: $16.99/month (recurring)
├─ Metadata:
│   ├─ tier: "pro"
│   ├─ monthly_credits: "400"
│   ├─ top_up_discount: "0.10"
│   └─ billing_interval: "month"

Product: "Sampletok Pro Annual"
├─ Type: Recurring
├─ Price: $299/year (recurring)
├─ Metadata:
│   ├─ tier: "pro"
│   ├─ monthly_credits: "400"
│   ├─ top_up_discount: "0.10"
│   └─ billing_interval: "year"

Product: "Sampletok Ultimate Monthly"
├─ Type: Recurring
├─ Price: $49.99/month (recurring)
├─ Metadata:
│   ├─ tier: "ultimate"
│   ├─ monthly_credits: "1500"
│   ├─ top_up_discount: "0.20"
│   └─ billing_interval: "month"

Product: "Sampletok Ultimate Annual"
├─ Type: Recurring
├─ Price: $799/year (recurring)
├─ Metadata:
│   ├─ tier: "ultimate"
│   ├─ monthly_credits: "1500"
│   ├─ top_up_discount: "0.20"
│   └─ billing_interval: "year"
```

**2. Top-Up Products (One-Time)**

```
Product: "50 Credit Top-Up"
├─ Type: One-time
├─ Price: $6.99
├─ Metadata:
│   ├─ type: "top_up"
│   ├─ credits: "50"
│   └─ requires_subscription: "true"

Product: "150 Credit Top-Up"
├─ Type: One-time
├─ Price: $17.99
├─ Metadata:
│   ├─ type: "top_up"
│   ├─ credits: "150"
│   └─ requires_subscription: "true"

Product: "500 Credit Top-Up"
├─ Type: One-time
├─ Price: $49.99
├─ Metadata:
│   ├─ type: "top_up"
│   ├─ credits: "500"
│   └─ requires_subscription: "true"
```

### 4.2 Critical Webhook Events

```
┌─────────────────────────────────────────────────────────────┐
│ SUBSCRIPTION WEBHOOKS (Must Handle)                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ customer.subscription.created                               │
│ ├─ User just subscribed                                     │
│ ├─ Create subscription record in database                   │
│ ├─ Grant initial monthly credits                            │
│ └─ Send welcome email                                       │
│                                                              │
│ customer.subscription.updated                               │
│ ├─ Subscription modified (upgrade/downgrade/cancel)         │
│ ├─ Update subscription record                               │
│ ├─ Handle tier change (adjust monthly_credits)              │
│ └─ If cancel_at_period_end = true, mark for cancellation   │
│                                                              │
│ customer.subscription.deleted                               │
│ ├─ Subscription ended (cancelled or expired)                │
│ ├─ Zero out all credits                                     │
│ ├─ Update status to 'cancelled'                             │
│ └─ Send cancellation email                                  │
│                                                              │
│ invoice.paid                                                │
│ ├─ Successful payment (initial or renewal)                  │
│ ├─ Grant monthly credits (if recurring invoice)             │
│ ├─ Update subscription.current_period_start/end             │
│ └─ Send receipt                                             │
│                                                              │
│ invoice.payment_failed                                      │
│ ├─ Payment failed (card declined, insufficient funds)       │
│ ├─ Update subscription status to 'past_due'                 │
│ ├─ Send payment failed email                                │
│ └─ Stripe auto-retries for 7 days                           │
│                                                              │
│ invoice.payment_action_required                             │
│ ├─ Requires 3D Secure authentication                        │
│ ├─ Send email with payment link                             │
│ └─ User must complete authentication                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ TOP-UP WEBHOOKS                                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ checkout.session.completed                                  │
│ ├─ One-time top-up purchase completed                       │
│ ├─ Verify user has active subscription                      │
│ ├─ Grant top-up credits                                     │
│ ├─ Apply tier discount if applicable                        │
│ └─ Create transaction record                                │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ DISPUTE/REFUND WEBHOOKS                                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│ charge.refunded                                             │
│ ├─ Payment refunded (manual or dispute)                     │
│ ├─ Deduct refunded credits (if possible)                    │
│ └─ Log transaction                                          │
│                                                              │
│ charge.dispute.created                                      │
│ ├─ Customer disputed charge                                 │
│ ├─ Freeze account                                           │
│ └─ Flag for manual review                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Subscription Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                  SUBSCRIPTION CHECKOUT FLOW                  │
└──────────────────────────────────────────────────────────────┘

[Frontend: Pricing Page]
    │
    │ User selects "Pro Monthly - $16.99/mo"
    ↓
POST /api/v1/subscriptions/create-checkout
    │ Body: { price_id: "price_xxx", tier: "pro" }
    │
    ▼
[Backend: Create Stripe Checkout Session]
    │ - Verify user authenticated
    │ - Check no active subscription exists
    │ - Get or create Stripe customer
    │ - Call Stripe: checkout.Session.create({
    │     mode: "subscription",
    │     line_items: [{ price: price_id, quantity: 1 }]
    │   })
    │
    ▼
Return: { checkout_url: "https://checkout.stripe.com/..." }
    │
    ▼
[Frontend: Redirect to Stripe]
    │ Stripe handles:
    │ - Payment method collection
    │ - 3D Secure if needed
    │ - Trial period setup (if enabled)
    │
    ▼
[Stripe: Process Subscription Creation]
    │
    ├─→ Success:
    │   │ - Redirects to success_url
    │   │ - Sends webhook: customer.subscription.created
    │   │ - Sends webhook: invoice.paid (first payment)
    │   └─→ [Backend Webhook Handler]
    │          │
    │          ├─ Create subscription record
    │          ├─ Grant initial monthly credits
    │          └─ Update user status
    │
    └─→ Failure:
        │ - Redirects to cancel_url
        └─ No subscription created

[Frontend: Success Page]
    │ Shows: "Subscription activated! +400 credits added"
    │ Displays: Current credit balance, next billing date
```

---

## 5. Database Schema

### 5.1 New Tables

#### Subscriptions Table

```sql
CREATE TABLE subscriptions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    -- Only one active subscription per user

    -- Stripe details
    stripe_subscription_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_customer_id VARCHAR(255) NOT NULL,

    -- Plan details
    tier VARCHAR(20) NOT NULL,  -- 'basic', 'pro', 'ultimate'
    billing_interval VARCHAR(10) NOT NULL,  -- 'month', 'year'
    monthly_credits INTEGER NOT NULL,  -- Monthly credit allowance (100, 400, 1500)

    -- Status
    status VARCHAR(20) NOT NULL,  -- 'active', 'past_due', 'unpaid', 'cancelled', 'incomplete'
    cancel_at_period_end BOOLEAN DEFAULT FALSE,

    -- Billing period
    current_period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Pricing
    stripe_price_id VARCHAR(255) NOT NULL,  -- e.g., price_xxx (CRITICAL for tracking)
    amount_cents INTEGER NOT NULL,  -- e.g., 1699 for $16.99
    currency VARCHAR(3) DEFAULT 'USD',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    cancelled_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_subscription_user (user_id),
    INDEX idx_subscription_stripe_id (stripe_subscription_id),
    INDEX idx_subscription_status (status),
    INDEX idx_subscription_period_end (current_period_end)
);

-- Constraint: Ensure cancelled subscriptions have cancellation timestamp
ALTER TABLE subscriptions
ADD CONSTRAINT check_cancelled_at
CHECK (
    (status = 'cancelled' AND cancelled_at IS NOT NULL) OR
    (status != 'cancelled')
);
```

#### Credit Transactions Table (Enhanced)

```sql
CREATE TABLE credit_transactions (
    -- Primary identification
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Transaction details
    transaction_type VARCHAR(30) NOT NULL,
    -- Types: 'subscription_grant', 'monthly_renewal', 'top_up_purchase',
    --        'deduction', 'refund', 'cancellation_reset'
    credits_amount INTEGER NOT NULL,  -- Positive for grants, negative for deductions
    previous_balance INTEGER NOT NULL,
    new_balance INTEGER NOT NULL,

    -- Subscription reference (if applicable)
    subscription_id UUID REFERENCES subscriptions(id) ON DELETE SET NULL,

    -- Payment details (for purchases)
    stripe_session_id VARCHAR(255),
    stripe_payment_intent_id VARCHAR(255),
    stripe_invoice_id VARCHAR(255),
    amount_cents INTEGER,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Top-up details
    top_up_package VARCHAR(20),  -- 'small', 'medium', 'large'
    discount_applied DECIMAL(5,2),  -- e.g., 0.10 for 10% off

    -- Status
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- Metadata
    description TEXT,
    metadata JSONB,

    -- Related entities
    collection_id UUID REFERENCES collections(id) ON DELETE SET NULL,
    sample_id UUID REFERENCES samples(id) ON DELETE SET NULL,

    -- Error tracking
    error_message TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_credit_tx_user (user_id),
    INDEX idx_credit_tx_subscription (subscription_id),
    INDEX idx_credit_tx_type (transaction_type),
    INDEX idx_credit_tx_status (status),
    INDEX idx_credit_tx_created (created_at DESC),
    -- CRITICAL: Composite indexes for common queries
    INDEX idx_credit_tx_user_created (user_id, created_at DESC),
    INDEX idx_credit_tx_user_type (user_id, transaction_type),
    INDEX idx_credit_tx_stripe_invoice (stripe_invoice_id) WHERE stripe_invoice_id IS NOT NULL
);
```

#### Stripe Customers Table (Same as before)

```sql
CREATE TABLE stripe_customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    stripe_customer_id VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255),
    name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    INDEX idx_stripe_customer_user (user_id),
    INDEX idx_stripe_customer_stripe_id (stripe_customer_id)
);
```

### 5.2 Modified Tables

#### Users Table (Add soft delete)

```sql
-- Add to existing users table
ALTER TABLE users
ADD COLUMN is_deleted BOOLEAN DEFAULT FALSE NOT NULL,
ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- Constraint: deleted_at must be set if is_deleted is true
ALTER TABLE users
ADD CONSTRAINT check_deleted_at
CHECK (
    (is_deleted = false) OR (is_deleted = true AND deleted_at IS NOT NULL)
);

-- Index for filtering out deleted users
CREATE INDEX idx_users_is_deleted ON users(is_deleted);

-- NOTE: subscription_status is accessed via relationship, not stored in users table
-- Use: user.subscription.status (avoids data sync issues)
```

### 5.3 Database Relationships

```
users (1) ←──────── (0..1) subscriptions
  │                         │
  │                         ├─→ stripe_subscription_id
  │                         ├─→ current_period_start/end
  │                         └─→ monthly_credits
  │
  ├──────── (1) stripe_customers
  │                └─→ stripe_customer_id
  │
  └──────── (many) credit_transactions
                      │
                      ├─→ subscription_id (if subscription-related)
                      ├─→ stripe_invoice_id (if monthly renewal)
                      └─→ collection_id / sample_id (if deduction)
```

---

## 6. Backend Implementation

### 6.1 Project Structure

```
backend/
├── app/
│   ├── models/
│   │   ├── user.py                        [📝 Enhance - add subscription_status]
│   │   ├── subscription.py                [➕ NEW]
│   │   ├── credit_transaction.py          [➕ NEW]
│   │   └── stripe_customer.py             [➕ NEW]
│   │
│   ├── schemas/
│   │   ├── subscription.py                [➕ NEW]
│   │   ├── credit_transaction.py          [➕ NEW]
│   │   └── payment.py                     [➕ NEW]
│   │
│   ├── services/
│   │   ├── credit_service.py              [📝 Enhance - subscription logic]
│   │   ├── subscription_service.py        [➕ NEW]
│   │   ├── payment_service.py             [➕ NEW]
│   │   └── transaction_service.py         [➕ NEW]
│   │
│   ├── api/v1/endpoints/
│   │   ├── subscriptions.py               [➕ NEW]
│   │   ├── payments.py                    [➕ NEW - top-ups]
│   │   ├── credits.py                     [➕ NEW]
│   │   ├── users.py                       [📝 Enhance]
│   │   └── webhooks.py                    [➕ NEW - Stripe webhooks]
│   │
│   ├── api/deps.py                        [📝 Enhance - subscription check]
│   │
│   ├── core/
│   │   └── config.py                      [📝 Enhance - Stripe config]
│   │
│   └── utils/
│       └── subscription_helpers.py        [➕ NEW]
│
└── alembic/versions/
    ├── xxx_add_subscriptions.py           [➕ NEW]
    └── xxx_add_credit_transactions.py     [➕ NEW]
```

### 6.2 Models

#### `backend/app/models/subscription.py`

```python
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.db.base_class import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)

    # Stripe details
    stripe_subscription_id = Column(String(255), unique=True, nullable=False)
    stripe_customer_id = Column(String(255), nullable=False)

    # Plan details
    tier = Column(String(20), nullable=False)  # basic, pro, ultimate
    billing_interval = Column(String(10), nullable=False)  # month, year
    monthly_credits = Column(Integer, nullable=False)

    # Status
    status = Column(String(20), nullable=False)  # active, past_due, unpaid, cancelled, incomplete
    cancel_at_period_end = Column(Boolean, default=False)

    # Billing period
    current_period_start = Column(TIMESTAMP(timezone=True), nullable=False)
    current_period_end = Column(TIMESTAMP(timezone=True), nullable=False)

    # Pricing
    stripe_price_id = Column(String(255), nullable=False)  # CRITICAL: Track which price user is on
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="USD")

    # Timestamps
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    updated_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="subscription")
    credit_transactions = relationship("CreditTransaction", back_populates="subscription")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(status = 'cancelled' AND cancelled_at IS NOT NULL) OR (status != 'cancelled')",
            name="check_cancelled_at"
        ),
    )

    @property
    def is_active(self) -> bool:
        """Check if subscription allows platform access."""
        return self.status in ['active', 'past_due']

    @property
    def top_up_discount(self) -> float:
        """Get discount percentage for top-up purchases."""
        discounts = {
            'basic': 0.0,
            'pro': 0.10,
            'ultimate': 0.20
        }
        return discounts.get(self.tier, 0.0)
```

#### Enhanced `backend/app/models/user.py`

```python
# Add to existing User model:

from sqlalchemy import Column, Boolean, CheckConstraint
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    # ... existing fields ...

    # Soft delete (CRITICAL: prevents data loss with active subscriptions)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    credit_transactions = relationship("CreditTransaction", back_populates="user")
    stripe_customer = relationship("StripeCustomer", back_populates="user", uselist=False)

    # Constraint
    __table_args__ = (
        CheckConstraint(
            "(is_deleted = false) OR (is_deleted = true AND deleted_at IS NOT NULL)",
            name="check_deleted_at"
        ),
    )

    @property
    def subscription_status(self) -> str:
        """Get subscription status from relationship (not stored in DB)."""
        if not self.subscription:
            return 'none'
        return self.subscription.status

    @property
    def has_active_subscription(self) -> bool:
        """Check if user has active subscription for platform access."""
        return self.subscription and self.subscription.is_active

    @property
    def monthly_credit_allowance(self) -> int:
        """Get monthly credit allowance from subscription."""
        if self.subscription and self.subscription.is_active:
            return self.subscription.monthly_credits
        return 0

    def soft_delete(self):
        """Mark user as deleted without removing data."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()
```

### 6.3 Services

#### `backend/app/services/subscription_service.py`

```python
import stripe
from typing import Optional, Dict
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.user import User
from app.models.subscription import Subscription
from app.models.stripe_customer import StripeCustomer
from app.services.credit_service import CreditService
from app.services.transaction_service import TransactionService

stripe.api_key = settings.STRIPE_SECRET_KEY

class SubscriptionService:
    """
    Manages subscription lifecycle and Stripe subscription operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.credit_service = CreditService(db)
        self.transaction_service = TransactionService(db)

    async def create_checkout_session(
        self,
        user: User,
        price_id: str,
        tier: str,
        billing_interval: str,
        success_url: str,
        cancel_url: str
    ) -> Dict:
        """
        Create Stripe Checkout session for subscription.

        Args:
            user: User subscribing
            price_id: Stripe price ID
            tier: Subscription tier (basic, pro, ultimate)
            billing_interval: month or year
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancellation

        Returns:
            {
                "session_id": "cs_xxx",
                "checkout_url": "https://checkout.stripe.com/..."
            }
        """
        # Check if user already has subscription
        existing_sub = await self.get_user_subscription(user.id)
        if existing_sub and existing_sub.is_active:
            raise ValueError("User already has an active subscription")

        # Get or create Stripe customer
        stripe_customer = await self._get_or_create_stripe_customer(user)

        # Create checkout session
        session_params = {
            "customer": stripe_customer.stripe_customer_id,
            "payment_method_types": ["card"],
            "line_items": [
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            "mode": "subscription",
            "success_url": f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": cancel_url,
            "metadata": {
                "user_id": str(user.id),
                "tier": tier,
                "billing_interval": billing_interval
            },
            "subscription_data": {
                "metadata": {
                    "user_id": str(user.id),
                    "tier": tier
                }
            }
        }

        session = stripe.checkout.Session.create(**session_params)

        return {
            "session_id": session.id,
            "checkout_url": session.url
        }

    async def handle_subscription_created(
        self,
        stripe_subscription: stripe.Subscription
    ) -> Subscription:
        """
        Handle customer.subscription.created webhook.
        Creates subscription record and grants initial credits.
        """
        # Get user
        user_id = stripe_subscription.metadata.get("user_id")
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one()

        # Extract subscription details
        price = stripe_subscription["items"]["data"][0]["price"]
        tier = stripe_subscription.metadata.get("tier")
        monthly_credits = self._get_monthly_credits_for_tier(tier)

        # Create subscription record
        subscription = Subscription(
            user_id=user.id,
            stripe_subscription_id=stripe_subscription.id,
            stripe_customer_id=stripe_subscription.customer,
            stripe_price_id=price.id,  # CRITICAL: Track which price
            tier=tier,
            billing_interval=price.recurring.interval,
            monthly_credits=monthly_credits,
            status=stripe_subscription.status,
            current_period_start=datetime.fromtimestamp(stripe_subscription.current_period_start),
            current_period_end=datetime.fromtimestamp(stripe_subscription.current_period_end),
            amount_cents=price.unit_amount,
            currency=price.currency.upper()
        )

        self.db.add(subscription)

        # Grant initial monthly credits
        await self.credit_service.add_credits_atomic(
            user_id=user.id,
            credits=monthly_credits,
            transaction_type="subscription_grant",
            description=f"Initial credits for {tier} subscription",
            subscription_id=subscription.id
        )

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    async def handle_invoice_paid(
        self,
        stripe_invoice: stripe.Invoice
    ) -> None:
        """
        Handle invoice.paid webhook.
        Grants monthly credits on renewal.
        """
        # Skip if not a subscription invoice
        if not stripe_invoice.subscription:
            return

        # Find subscription
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_invoice.subscription
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        # Check if this is a renewal (not initial payment)
        # Initial payment is handled by subscription.created
        is_renewal = subscription.created_at < datetime.utcnow()

        if is_renewal:
            # Grant monthly credits
            await self.credit_service.add_credits_atomic(
                user_id=subscription.user_id,
                credits=subscription.monthly_credits,
                transaction_type="monthly_renewal",
                description=f"Monthly renewal: {subscription.tier} plan",
                subscription_id=subscription.id,
                stripe_invoice_id=stripe_invoice.id
            )

        # Update period dates
        stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
        subscription.current_period_start = datetime.fromtimestamp(stripe_sub.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
        subscription.status = stripe_sub.status

        await self.db.commit()

    async def handle_subscription_updated(
        self,
        stripe_subscription: stripe.Subscription
    ) -> None:
        """
        Handle customer.subscription.updated webhook.
        Updates subscription status, handles cancellations, tier changes.
        """
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription.id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            return

        # Update status
        old_status = subscription.status
        subscription.status = stripe_subscription.status
        subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end

        # Handle tier change (upgrade/downgrade)
        new_tier = stripe_subscription.metadata.get("tier")
        if new_tier and new_tier != subscription.tier:
            old_tier = subscription.tier
            subscription.tier = new_tier
            subscription.monthly_credits = self._get_monthly_credits_for_tier(new_tier)

            # Log tier change
            await self.transaction_service.create_transaction(
                user_id=subscription.user_id,
                transaction_type="tier_change",
                credits_amount=0,
                description=f"Subscription changed: {old_tier} → {new_tier}",
                subscription_id=subscription.id,
                metadata={"old_tier": old_tier, "new_tier": new_tier}
            )

        # Update period
        subscription.current_period_start = datetime.fromtimestamp(stripe_subscription.current_period_start)
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)

        await self.db.commit()

    async def handle_subscription_deleted(
        self,
        stripe_subscription: stripe.Subscription
    ) -> None:
        """
        Handle customer.subscription.deleted webhook.

        EDGE CASE: User might have active processing when subscription ends.
        We handle this gracefully by checking for active collections first.
        """
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_subscription.id
            )
        )
        subscription = result.scalar_one_or_none()

        if not subscription:
            logger.warning(f"Subscription not found: {stripe_subscription.id}")
            return

        # Get user with lock
        result = await self.db.execute(
            select(User)
            .where(User.id == subscription.user_id)
            .with_for_update()
        )
        user = result.scalar_one()

        # 🚨 CHECK FOR ACTIVE PROCESSING
        # Check if user has collections currently being processed
        pending_collections = await self.db.execute(
            select(Collection).where(
                Collection.user_id == subscription.user_id,
                Collection.status.in_(['pending', 'processing'])
            )
        )
        pending = pending_collections.scalars().all()

        if pending:
            logger.warning(
                f"⚠️ User {subscription.user_id} has {len(pending)} active collections. "
                f"Delaying credit reset until processing completes."
            )

            # Mark subscription as cancelled but DON'T zero credits yet
            subscription.status = 'cancelled'
            subscription.cancelled_at = datetime.utcnow()
            # Note: Credits remain until processing completes

            await self.db.commit()

            # Schedule delayed cleanup check (1 hour from now)
            # This will verify processing is complete and zero credits
            from app.core.inngest import inngest_client
            await inngest_client.send({
                "name": "subscription/cleanup.check",
                "data": {
                    "subscription_id": str(subscription.id),
                    "user_id": str(subscription.user_id)
                }
            })

            logger.info(f"Scheduled delayed cleanup for user {subscription.user_id}")
            return

        # No active processing - safe to zero credits immediately
        old_balance = user.credits
        user.credits = 0

        # Update subscription
        subscription.status = 'cancelled'
        subscription.cancelled_at = datetime.utcnow()

        # Log credit reset
        await self.transaction_service.create_transaction(
            user_id=user.id,
            transaction_type="cancellation_reset",
            credits_amount=-old_balance,
            description="Subscription cancelled - all credits removed",
            subscription_id=subscription.id,
            previous_balance=old_balance,
            new_balance=0,
            status='completed',
            completed_at=datetime.utcnow()
        )

        await self.db.commit()

        logger.info(
            f"✅ Subscription deleted: user={subscription.user_id}, "
            f"credits reset: {old_balance} → 0"
        )

    async def get_user_subscription(self, user_id) -> Optional[Subscription]:
        """Get user's subscription if exists."""
        result = await self.db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def cancel_subscription(
        self,
        user_id,
        cancel_immediately: bool = False
    ) -> Subscription:
        """
        Cancel user's subscription.

        Args:
            user_id: User ID
            cancel_immediately: If True, cancel now. If False, cancel at period end (default)
        """
        subscription = await self.get_user_subscription(user_id)

        if not subscription:
            raise ValueError("No active subscription found")

        # Cancel in Stripe
        if cancel_immediately:
            stripe.Subscription.delete(subscription.stripe_subscription_id)
        else:
            stripe.Subscription.modify(
                subscription.stripe_subscription_id,
                cancel_at_period_end=True
            )
            subscription.cancel_at_period_end = True

        await self.db.commit()
        await self.db.refresh(subscription)

        return subscription

    def _get_monthly_credits_for_tier(self, tier: str) -> int:
        """Get monthly credit allowance for tier."""
        credits = {
            'basic': 100,
            'pro': 400,
            'ultimate': 1500
        }
        return credits.get(tier, 0)

    async def _get_or_create_stripe_customer(self, user: User) -> StripeCustomer:
        """Get existing Stripe customer or create new one."""
        # Check if customer exists
        result = await self.db.execute(
            select(StripeCustomer).where(StripeCustomer.user_id == user.id)
        )
        stripe_customer = result.scalar_one_or_none()

        if stripe_customer:
            return stripe_customer

        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            metadata={
                "user_id": str(user.id),
                "clerk_user_id": user.clerk_user_id
            }
        )

        # Save to database
        stripe_customer = StripeCustomer(
            user_id=user.id,
            stripe_customer_id=customer.id,
            email=user.email
        )
        self.db.add(stripe_customer)
        await self.db.commit()
        await self.db.refresh(stripe_customer)

        return stripe_customer
```

#### Enhanced `backend/app/services/credit_service.py`

```python
# Add these methods to existing CreditService:

import logging
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

async def add_credits_atomic(
    self,
    user_id: UUID,
    credits: int,
    transaction_type: str,
    description: str,
    subscription_id: Optional[UUID] = None,
    stripe_invoice_id: Optional[str] = None,
    stripe_payment_intent_id: Optional[str] = None,
    top_up_package: Optional[str] = None,
    discount_applied: Optional[float] = None
) -> Dict:
    """
    Add credits atomically with database locking and idempotency.

    CRITICAL: This method MUST be idempotent to handle duplicate webhooks!
    """
    async with self.db.begin_nested():  # Creates savepoint for rollback
        try:
            # 🔒 LOCK: Acquire row-level lock on user
            # Prevents concurrent modifications to same user's credits
            result = await self.db.execute(
                select(User)
                .where(User.id == user_id)
                .with_for_update()  # SELECT FOR UPDATE
            )
            user = result.scalar_one()

            # 🔍 IDEMPOTENCY CHECK: Has this exact transaction been processed?
            if stripe_invoice_id:
                existing = await self.db.execute(
                    select(CreditTransaction)
                    .where(
                        CreditTransaction.user_id == user_id,
                        CreditTransaction.stripe_invoice_id == stripe_invoice_id,
                        CreditTransaction.transaction_type == transaction_type,
                        CreditTransaction.status == 'completed'
                    )
                )
                existing_tx = existing.scalar_one_or_none()

                if existing_tx:
                    logger.info(
                        f"⚠️ DUPLICATE WEBHOOK: Invoice {stripe_invoice_id} already processed. "
                        f"Skipping credit grant. Transaction ID: {existing_tx.id}"
                    )
                    return {
                        "duplicate": True,
                        "existing_transaction_id": str(existing_tx.id),
                        "previous_balance": existing_tx.previous_balance,
                        "credits_added": 0,
                        "new_balance": existing_tx.new_balance
                    }

            # Same check for payment intents (top-up purchases)
            if stripe_payment_intent_id:
                existing = await self.db.execute(
                    select(CreditTransaction)
                    .where(
                        CreditTransaction.user_id == user_id,
                        CreditTransaction.stripe_payment_intent_id == stripe_payment_intent_id,
                        CreditTransaction.status == 'completed'
                    )
                )
                existing_tx = existing.scalar_one_or_none()

                if existing_tx:
                    logger.info(f"⚠️ DUPLICATE: Payment intent {stripe_payment_intent_id} already processed.")
                    return {
                        "duplicate": True,
                        "existing_transaction_id": str(existing_tx.id),
                        "previous_balance": existing_tx.previous_balance,
                        "credits_added": 0,
                        "new_balance": existing_tx.new_balance
                    }

            # 💰 PERFORM CREDIT OPERATION
            previous_balance = user.credits
            new_balance = previous_balance + credits

            # Sanity check
            if new_balance < 0:
                logger.error(
                    f"❌ Attempted negative balance: user={user_id}, "
                    f"previous={previous_balance}, adding={credits}"
                )
                raise ValueError("Credit balance cannot be negative")

            user.credits = new_balance

            # 📝 CREATE AUDIT RECORD
            transaction = CreditTransaction(
                user_id=user_id,
                subscription_id=subscription_id,
                transaction_type=transaction_type,
                credits_amount=credits,
                previous_balance=previous_balance,
                new_balance=new_balance,
                description=description,
                stripe_invoice_id=stripe_invoice_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
                top_up_package=top_up_package,
                discount_applied=discount_applied,
                status='completed',
                completed_at=datetime.utcnow()
            )

            self.db.add(transaction)
            await self.db.flush()  # Write to DB but don't commit yet

            logger.info(
                f"✅ Credits added: user={user_id}, amount={credits}, "
                f"balance: {previous_balance} → {new_balance}, type={transaction_type}"
            )

            return {
                "duplicate": False,
                "transaction_id": str(transaction.id),
                "previous_balance": previous_balance,
                "credits_added": credits,
                "new_balance": new_balance
            }

        except IntegrityError as e:
            logger.error(f"❌ Integrity error in credit operation: {e}")
            await self.db.rollback()
            raise
        except Exception as e:
            logger.error(f"❌ Error adding credits: {e}")
            await self.db.rollback()
            raise

async def can_process_collection(
    self,
    user_id: UUID,
    video_count: int
) -> tuple[bool, Optional[str]]:
    """
    Check if user can process a collection.
    Requires active subscription AND sufficient credits.
    """
    result = await self.db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one()

    # Check subscription
    if not user.has_active_subscription:
        return False, "Active subscription required to process collections"

    # Check credits
    if user.credits < video_count:
        return False, f"Insufficient credits. Need {video_count}, have {user.credits}"

    return True, None
```

### 6.4 API Endpoints

#### `backend/app/api/v1/endpoints/subscriptions.py`

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.services.subscription_service import SubscriptionService
from app.schemas.subscription import (
    SubscriptionCheckoutCreate,
    SubscriptionCheckoutResponse,
    SubscriptionResponse,
    CancelSubscriptionRequest
)
from app.core.config import settings

router = APIRouter()

@router.post("/create-checkout", response_model=SubscriptionCheckoutResponse)
async def create_subscription_checkout(
    data: SubscriptionCheckoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create Stripe Checkout session for subscription.

    Request:
        {
            "tier": "pro",
            "billing_interval": "month",
            "success_url": "https://yourapp.com/subscription/success",
            "cancel_url": "https://yourapp.com/pricing"
        }

    Response:
        {
            "session_id": "cs_xxx",
            "checkout_url": "https://checkout.stripe.com/..."
        }
    """
    subscription_service = SubscriptionService(db)

    # Get price ID from config based on tier and interval
    price_id = settings.get_subscription_price_id(data.tier, data.billing_interval)

    try:
        result = await subscription_service.create_checkout_session(
            user=current_user,
            price_id=price_id,
            tier=data.tier,
            billing_interval=data.billing_interval,
            success_url=data.success_url or settings.SUBSCRIPTION_SUCCESS_URL,
            cancel_url=data.cancel_url or settings.SUBSCRIPTION_CANCEL_URL,
            trial_period_days=data.trial_days
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create checkout: {str(e)}")

@router.get("/me", response_model=SubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user's subscription details.
    """
    subscription_service = SubscriptionService(db)
    subscription = await subscription_service.get_user_subscription(current_user.id)

    if not subscription:
        raise HTTPException(status_code=404, detail="No subscription found")

    return subscription

@router.post("/cancel")
async def cancel_subscription(
    data: CancelSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel subscription.

    Request:
        {
            "cancel_immediately": false  // If true, cancel now. If false, cancel at period end
        }
    """
    subscription_service = SubscriptionService(db)

    try:
        subscription = await subscription_service.cancel_subscription(
            user_id=current_user.id,
            cancel_immediately=data.cancel_immediately
        )

        return {
            "message": "Subscription cancelled" if data.cancel_immediately else "Subscription will cancel at period end",
            "subscription": subscription
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/plans")
async def get_subscription_plans():
    """
    Get available subscription plans and pricing.
    """
    return {
        "plans": [
            {
                "tier": "basic",
                "name": "Basic",
                "monthly": {
                    "price_cents": 999,
                    "price_display": "$9.99/mo",
                    "credits": 100,
                    "price_id": settings.STRIPE_PRICE_BASIC_MONTHLY
                },
                "annual": {
                    "price_cents": 9900,
                    "price_display": "$99/yr",
                    "monthly_equivalent": "$8.25/mo",
                    "credits": 100,
                    "price_id": settings.STRIPE_PRICE_BASIC_ANNUAL,
                    "savings": "17%"
                }
            },
            {
                "tier": "pro",
                "name": "Pro",
                "badge": "MOST POPULAR",
                "monthly": {
                    "price_cents": 1699,
                    "price_display": "$16.99/mo",
                    "credits": 400,
                    "price_id": settings.STRIPE_PRICE_PRO_MONTHLY
                },
                "annual": {
                    "price_cents": 16922,
                    "price_display": "$169/yr",
                    "monthly_equivalent": "$24.92/mo",
                    "credits": 400,
                    "price_id": settings.STRIPE_PRICE_PRO_ANNUAL,
                    "savings": "17%"
                },
                "features": [
                    "10% discount on top-ups",
                    "Priority support"
                ]
            },
            {
                "tier": "ultimate",
                "name": "Ultimate",
                "badge": "BEST VALUE",
                "monthly": {
                    "price_cents": 4999,
                    "price_display": "$49.99/mo",
                    "credits": 1500,
                    "price_id": settings.STRIPE_PRICE_ULTIMATE_MONTHLY
                },
                "annual": {
                    "price_cents": 49790,
                    "price_display": "$498/yr",
                    "monthly_equivalent": "$66.58/mo",
                    "credits": 1500,
                    "price_id": settings.STRIPE_PRICE_ULTIMATE_ANNUAL,
                    "savings": "17%"
                },
                "features": [
                    "20% discount on top-ups",
                    "Priority support (24h)",
                    "Early access to features"
                ]
            }
        ]
    }
```

#### `backend/app/api/v1/endpoints/webhooks.py`

```python
from fastapi import APIRouter, Request, HTTPException, Header
import stripe
import logging

from app.core.config import settings
from app.core.inngest import inngest_client  # Inngest client for async processing

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/stripe")
async def stripe_webhook_handler(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    """
    🔒 CRITICAL SECURITY: Stripe webhook receiver with signature verification.

    This endpoint MUST:
    1. Verify webhook signature (prevents attacks)
    2. Return 200 quickly (< 2 seconds to Stripe)
    3. Queue events to Inngest for async processing

    DO NOT process events synchronously here - use Inngest workers!
    """
    # 1️⃣ READ RAW BODY (required for signature verification)
    payload = await request.body()

    # 2️⃣ VERIFY SIGNATURE (CRITICAL SECURITY!)
    if not stripe_signature:
        logger.error("❌ Missing Stripe signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        # Construct and verify event
        # This ensures the webhook came from Stripe and hasn't been tampered with
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET  # From environment
        )
    except ValueError as e:
        # Invalid payload format
        logger.error(f"❌ Invalid webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature - POSSIBLE ATTACK!
        logger.error(f"🚨 SECURITY ALERT: Invalid webhook signature: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")

    # 3️⃣ QUEUE TO INNGEST FOR ASYNC PROCESSING
    # This ensures we return 200 to Stripe within milliseconds
    # The actual processing happens in Inngest workers (see inngest_functions.py)
    try:
        await inngest_client.send({
            "name": f"stripe/{event.type}",  # e.g., "stripe/invoice.paid"
            "data": {
                "event_id": event.id,
                "event_type": event.type,
                "stripe_event": event.to_dict(),  # Full event data
                "created": event.created
            }
        })

        logger.info(f"✅ Webhook queued: {event.type} (ID: {event.id})")

    except Exception as e:
        logger.error(f"❌ Failed to queue webhook to Inngest: {e}")
        # Still return 200 to Stripe to avoid retries
        # Monitoring should alert on this error

    # 4️⃣ RETURN SUCCESS IMMEDIATELY
    # Stripe expects 2xx response within a few seconds
    return {"received": True, "event_id": event.id, "event_type": event.type}
```

#### `backend/app/inngest_functions.py` (Add Webhook Handlers)

```python
# Add these Inngest functions to handle webhooks asynchronously

@inngest_client.create_function(
    fn_id="stripe-subscription-created",
    trigger=inngest.TriggerEvent(event="stripe/customer.subscription.created")
)
async def handle_subscription_created_event(
    ctx: inngest.Context,
    step: inngest.Step
):
    """
    Process subscription.created webhook asynchronously.
    Grants initial credits and creates subscription record.
    """
    event_data = ctx.event.data["stripe_event"]
    stripe_subscription = event_data["data"]["object"]

    logger.info(f"Processing subscription.created: {stripe_subscription['id']}")

    async with get_db() as db:
        service = SubscriptionService(db)

        try:
            await service.handle_subscription_created(stripe_subscription)
            logger.info(f"✅ Subscription created: {stripe_subscription['id']}")
        except Exception as e:
            logger.error(f"❌ Error processing subscription.created: {e}")
            raise  # Inngest will retry automatically

@inngest_client.create_function(
    fn_id="stripe-invoice-paid",
    trigger=inngest.TriggerEvent(event="stripe/invoice.paid"),
    retries=3  # Retry up to 3 times if it fails
)
async def handle_invoice_paid_event(ctx: inngest.Context, step: inngest.Step):
    """
    Process invoice.paid webhook asynchronously.
    Grants monthly credits on renewal.
    """
    event_data = ctx.event.data["stripe_event"]
    stripe_invoice = event_data["data"]["object"]

    logger.info(f"Processing invoice.paid: {stripe_invoice['id']}")

    async with get_db() as db:
        service = SubscriptionService(db)
        try:
            await service.handle_invoice_paid(stripe_invoice)
            logger.info(f"✅ Invoice processed: {stripe_invoice['id']}")
        except Exception as e:
            logger.error(f"❌ Error processing invoice.paid: {e}")
            raise

@inngest_client.create_function(
    fn_id="stripe-subscription-updated",
    trigger=inngest.TriggerEvent(event="stripe/customer.subscription.updated")
)
async def handle_subscription_updated_event(ctx: inngest.Context, step: inngest.Step):
    """Process subscription.updated webhook asynchronously."""
    event_data = ctx.event.data["stripe_event"]
    stripe_subscription = event_data["data"]["object"]

    async with get_db() as db:
        service = SubscriptionService(db)
        await service.handle_subscription_updated(stripe_subscription)

@inngest_client.create_function(
    fn_id="stripe-subscription-deleted",
    trigger=inngest.TriggerEvent(event="stripe/customer.subscription.deleted")
)
async def handle_subscription_deleted_event(ctx: inngest.Context, step: inngest.Step):
    """
    Process subscription.deleted webhook asynchronously.
    Handles credit reset with grace period for active processing.
    """
    event_data = ctx.event.data["stripe_event"]
    stripe_subscription = event_data["data"]["object"]

    async with get_db() as db:
        service = SubscriptionService(db)
        await service.handle_subscription_deleted(stripe_subscription)

@inngest_client.create_function(
    fn_id="stripe-checkout-completed",
    trigger=inngest.TriggerEvent(event="stripe/checkout.session.completed")
)
async def handle_checkout_completed_event(ctx: inngest.Context, step: inngest.Step):
    """Process checkout.session.completed for top-up purchases."""
    event_data = ctx.event.data["stripe_event"]
    session = event_data["data"]["object"]

    # Only handle one-time payments (top-ups), not subscriptions
    if session["mode"] == "payment":
        async with get_db() as db:
            payment_service = PaymentService(db)
            await payment_service.handle_top_up_purchase(session)

@inngest_client.create_function(
    fn_id="stripe-payment-failed",
    trigger=inngest.TriggerEvent(event="stripe/invoice.payment_failed")
)
async def handle_payment_failed_event(ctx: inngest.Context, step: inngest.Step):
    """
    Handle payment failure.
    Send email notification, update subscription status.
    """
    event_data = ctx.event.data["stripe_event"]
    invoice = event_data["data"]["object"]

    # TODO: Send payment failure email
    # TODO: Update subscription status to 'past_due'
    logger.warning(f"⚠️ Payment failed: invoice {invoice['id']}")
```

**Why Async Processing?**
- ✅ Webhook endpoint responds to Stripe in < 100ms
- ✅ Complex operations (DB queries, credit grants) happen in background
- ✅ Automatic retries if processing fails
- ✅ No timeout issues
- ✅ Better monitoring and debugging via Inngest dashboard

### 6.5 Dependency Enhancement

#### `backend/app/api/deps.py`

```python
# Add this dependency for subscription-required endpoints

from fastapi import Depends, HTTPException
from app.models.user import User
from app.api.deps import get_current_user

async def require_active_subscription(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to ensure user has active subscription.
    Raises 403 if subscription is inactive or doesn't exist.
    """
    if not current_user.has_active_subscription:
        raise HTTPException(
            status_code=403,
            detail="Active subscription required to access this feature. Please subscribe at /pricing"
        )

    return current_user
```

Use this dependency on protected endpoints:

```python
# Example usage in collections endpoint
@router.post("/collections/process")
async def process_collection(
    data: CollectionProcessRequest,
    current_user: User = Depends(require_active_subscription),  # ← Subscription required
    db: AsyncSession = Depends(get_db)
):
    # User guaranteed to have active subscription here
    ...
```

---

## 7. Frontend Implementation

### 7.1 New Pages

#### `frontend/app/(app)/pricing/page.tsx`

```typescript
'use client';

import { useAuth } from '@clerk/nextjs';
import { useMutation } from '@tanstack/react-query';
import { createAuthenticatedClient } from '@/app/lib/api-client';
import { Check, Sparkles } from 'lucide-react';
import { useState } from 'react';

export default function PricingPage() {
  const { getToken } = useAuth();
  const [billingInterval, setBillingInterval] = useState<'month' | 'year'>('month');

  const subscribeMutation = useMutation({
    mutationFn: async ({ tier, interval }: { tier: string; interval: string }) => {
      const api = createAuthenticatedClient(getToken);
      return api.subscriptions.createCheckout({
        tier,
        billing_interval: interval,
        success_url: `${window.location.origin}/subscription/success`,
        cancel_url: `${window.location.origin}/pricing`
      });
    },
    onSuccess: (data) => {
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
    }
  });

  const handleSubscribe = (tier: string) => {
    subscribeMutation.mutate({ tier, interval: billingInterval });
  };

  return (
    <div className="container mx-auto px-4 py-12 max-w-7xl">
      {/* Header */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4">
          Choose Your Plan
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
          Subscribe to start processing TikTok collections
        </p>

        {/* Billing Toggle */}
        <div className="inline-flex items-center bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          <button
            onClick={() => setBillingInterval('month')}
            className={`
              px-4 py-2 rounded-md transition-colors
              ${billingInterval === 'month'
                ? 'bg-white dark:bg-gray-700 shadow'
                : 'text-gray-600 dark:text-gray-400'
              }
            `}
          >
            Monthly
          </button>
          <button
            onClick={() => setBillingInterval('year')}
            className={`
              px-4 py-2 rounded-md transition-colors relative
              ${billingInterval === 'year'
                ? 'bg-white dark:bg-gray-700 shadow'
                : 'text-gray-600 dark:text-gray-400'
              }
            `}
          >
            Annual
            <span className="absolute -top-2 -right-2 bg-green-500 text-white text-xs px-2 py-0.5 rounded-full">
              Save 17%
            </span>
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
        {/* Basic Plan */}
        <PricingCard
          tier="basic"
          name="Basic"
          monthlyPrice={999}
          annualPrice={9900}
          credits={100}
          features={[
            '100 credits/month',
            'Process ~100 videos/month',
            'Email support',
            'All core features'
          ]}
          billingInterval={billingInterval}
          onSubscribe={handleSubscribe}
          loading={subscribeMutation.isPending}
        />

        {/* Pro Plan (Popular) */}
        <PricingCard
          tier="pro"
          name="Pro"
          monthlyPrice={2999}
          annualPrice={29900}
          credits={400}
          features={[
            '400 credits/month',
            'Process ~400 videos/month',
            'Priority email support',
            '10% discount on top-ups',
            'All core features'
          ]}
          badge="MOST POPULAR"
          billingInterval={billingInterval}
          onSubscribe={handleSubscribe}
          loading={subscribeMutation.isPending}
        />

        {/* Ultimate Plan */}
        <PricingCard
          tier="ultimate"
          name="Ultimate"
          monthlyPrice={7999}
          annualPrice={79900}
          credits={1500}
          features={[
            '1500 credits/month',
            'Process ~1500 videos/month',
            'Priority support (24h)',
            '20% discount on top-ups',
            'Early access to features',
            'All core features'
          ]}
          badge="BEST VALUE"
          billingInterval={billingInterval}
          onSubscribe={handleSubscribe}
          loading={subscribeMutation.isPending}
        />
      </div>

      {/* FAQ */}
      <div className="max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold mb-6 text-center">
          Frequently Asked Questions
        </h2>

        <div className="space-y-4">
          <FAQItem
            question="What happens to unused credits?"
            answer="Unused credits accumulate unlimited while your subscription is active. However, all credits are reset to 0 if you cancel your subscription."
          />
          <FAQItem
            question="Can I cancel anytime?"
            answer="Yes! You can cancel anytime. Your subscription will remain active until the end of your billing period, then credits will be reset to 0."
          />
          <FAQItem
            question="What if I need more credits?"
            answer="You can purchase top-up credit packs anytime. Pro and Ultimate subscribers get discounts on top-ups."
          />
          <FAQItem
            question="Is there a free trial?"
            answer="We offer a 7-day free trial on all plans. You can cancel before the trial ends with no charge."
          />
        </div>
      </div>
    </div>
  );
}

function PricingCard({ tier, name, monthlyPrice, annualPrice, credits, features, badge, billingInterval, onSubscribe, loading }: any) {
  const isPopular = badge === 'MOST POPULAR';
  const price = billingInterval === 'month' ? monthlyPrice : annualPrice;
  const displayPrice = (price / 100).toFixed(2);
  const monthlyEquivalent = billingInterval === 'year' ? (annualPrice / 12 / 100).toFixed(2) : null;

  return (
    <div className={`
      relative p-8 rounded-2xl border-2 transition-all
      ${isPopular
        ? 'border-blue-500 shadow-xl scale-105'
        : 'border-gray-200 dark:border-gray-800 hover:border-gray-300'
      }
    `}>
      {badge && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-blue-500 text-white text-sm font-bold rounded-full">
          {badge}
        </div>
      )}

      <div className="text-center mb-8">
        <h3 className="text-2xl font-bold mb-2">{name}</h3>
        <div className="mb-4">
          <div className="text-4xl font-bold">
            ${displayPrice}
          </div>
          <div className="text-gray-500">
            per {billingInterval}
          </div>
          {monthlyEquivalent && (
            <div className="text-sm text-green-600 font-medium mt-1">
              ${monthlyEquivalent}/mo billed annually
            </div>
          )}
        </div>
        <div className="text-lg font-semibold text-blue-600">
          {credits} credits/month
        </div>
      </div>

      <ul className="space-y-3 mb-8">
        {features.map((feature: string, i: number) => (
          <li key={i} className="flex items-start gap-2">
            <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
            <span className="text-sm">{feature}</span>
          </li>
        ))}
      </ul>

      <button
        onClick={() => onSubscribe(tier)}
        disabled={loading}
        className={`
          w-full py-3 rounded-lg font-medium transition-colors
          ${isPopular
            ? 'bg-blue-500 hover:bg-blue-600 text-white'
            : 'bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700'
          }
          disabled:opacity-50 disabled:cursor-not-allowed
        `}
      >
        {loading ? 'Processing...' : 'Subscribe Now'}
      </button>
    </div>
  );
}

function FAQItem({ question, answer }: { question: string; answer: string }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg p-6 border border-gray-200 dark:border-gray-700">
      <h3 className="font-semibold mb-2">{question}</h3>
      <p className="text-gray-600 dark:text-gray-400">{answer}</p>
    </div>
  );
}
```

#### `frontend/app/(app)/subscription/success/page.tsx`

```typescript
'use client';

import { useEffect } from 'use';
import { useSearchParams } from 'next/navigation';
import { useCredits } from '@/app/lib/hooks/use-credits';
import { CheckCircle } from 'lucide-react';
import Link from 'next/link';

export default function SubscriptionSuccessPage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const { invalidate } = useCredits();

  useEffect(() => {
    // Refresh credit balance
    invalidate();
  }, [sessionId]);

  return (
    <div className="container mx-auto px-4 py-16 max-w-2xl text-center">
      <CheckCircle className="w-20 h-20 text-green-500 mx-auto mb-6" />

      <h1 className="text-4xl font-bold mb-4">
        Welcome to Sampletok! 🎉
      </h1>

      <p className="text-xl text-gray-600 dark:text-gray-400 mb-8">
        Your subscription is now active and your credits have been added.
      </p>

      <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-6 mb-8">
        <h2 className="font-semibold mb-2">What's Next?</h2>
        <ul className="text-left space-y-2 text-gray-700 dark:text-gray-300">
          <li>✓ Process TikTok collections</li>
          <li>✓ Download audio samples</li>
          <li>✓ Credits roll over while subscribed</li>
          <li>✓ Purchase top-ups if needed</li>
        </ul>
      </div>

      <div className="flex gap-4 justify-center">
        <Link
          href="/my-collections"
          className="px-8 py-3 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium"
        >
          Start Processing
        </Link>

        <Link
          href="/subscription/manage"
          className="px-8 py-3 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg font-medium"
        >
          Manage Subscription
        </Link>
      </div>
    </div>
  );
}
```

### 7.2 Components

#### `frontend/app/components/subscriptions/subscription-status.tsx`

```typescript
'use client';

import { useSubscription } from '@/app/lib/hooks/use-subscription';
import { format } from 'date-fns';
import { Crown, AlertTriangle, XCircle } from 'lucide-react';
import Link from 'next/link';

export function SubscriptionStatus() {
  const { subscription, isLoading } = useSubscription();

  if (isLoading) {
    return <div className="animate-pulse bg-gray-200 dark:bg-gray-800 h-24 rounded-lg" />;
  }

  if (!subscription) {
    return (
      <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-6">
        <div className="flex items-start gap-4">
          <AlertTriangle className="w-6 h-6 text-yellow-600 flex-shrink-0" />
          <div className="flex-1">
            <h3 className="font-semibold mb-1">No Active Subscription</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
              Subscribe to start processing TikTok collections and unlock all features.
            </p>
            <Link
              href="/pricing"
              className="inline-block px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium"
            >
              View Plans
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const statusConfig = {
    active: {
      icon: Crown,
      color: 'text-green-600',
      bg: 'bg-green-50 dark:bg-green-900/20',
      border: 'border-green-200 dark:border-green-800',
      title: 'Active Subscription'
    },
    trialing: {
      icon: Crown,
      color: 'text-blue-600',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
      border: 'border-blue-200 dark:border-blue-800',
      title: 'Trial Period'
    },
    past_due: {
      icon: AlertTriangle,
      color: 'text-orange-600',
      bg: 'bg-orange-50 dark:bg-orange-900/20',
      border: 'border-orange-200 dark:border-orange-800',
      title: 'Payment Failed'
    },
    cancelled: {
      icon: XCircle,
      color: 'text-red-600',
      bg: 'bg-red-50 dark:bg-red-900/20',
      border: 'border-red-200 dark:border-red-800',
      title: 'Subscription Cancelled'
    }
  };

  const config = statusConfig[subscription.status as keyof typeof statusConfig] || statusConfig.active;
  const Icon = config.icon;

  return (
    <div className={`${config.bg} border ${config.border} rounded-lg p-6`}>
      <div className="flex items-start gap-4">
        <Icon className={`w-6 h-6 ${config.color} flex-shrink-0`} />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold">{config.title}</h3>
            <span className="text-sm font-medium capitalize px-3 py-1 bg-white dark:bg-gray-800 rounded-full">
              {subscription.tier} Plan
            </span>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-gray-500 mb-1">Monthly Credits</div>
              <div className="font-semibold">{subscription.monthly_credits} credits</div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">Next Billing Date</div>
              <div className="font-semibold">
                {format(new Date(subscription.current_period_end), 'MMM d, yyyy')}
              </div>
            </div>
          </div>

          {subscription.cancel_at_period_end && (
            <div className="mt-4 text-sm text-orange-600 dark:text-orange-400">
              ⚠️ Subscription will cancel on {format(new Date(subscription.current_period_end), 'MMM d, yyyy')}
            </div>
          )}

          <div className="mt-4">
            <Link
              href="/subscription/manage"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              Manage Subscription →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
```

---

## 8. User Flows & Edge Cases

### 8.1 Complete User Journey

```
NEW USER
    ↓
[Visits sampletok.com]
    │ - Lands on homepage
    │ - Sees "Start Processing" CTA
    ↓
[Clicks "Start Processing"]
    │ - Redirected to /pricing (no subscription check yet)
    ↓
[Views Pricing Page]
    │ - Sees 3 tiers: Basic, Pro, Ultimate
    │ - Monthly vs Annual toggle
    │ - Clicks "Subscribe to Pro Monthly - $16.99"
    ↓
[Stripe Checkout]
    │ - Enters payment details
    │ - Completes 3D Secure if required
    │ - Stripe processes payment
    ↓
[Subscription Created]
    │ Webhooks fire:
    │ 1. customer.subscription.created → Grant 400 credits
    │ 2. invoice.paid → Confirm payment
    ↓
[Redirected to /subscription/success]
    │ - Shows "Subscription Activated!"
    │ - Displays credit balance: 400 credits
    │ - "Start Processing" button
    ↓
[Navigates to /my-collections]
    │ - Subscription status widget shows "Pro Plan - Active"
    │ - Can now process collections
    │ - Credits displayed in navbar
    ↓
[Processes TikTok Collection (50 videos)]
    │ - Credits deducted: 400 → 350
    │ - Videos processed in background
    │ - Can download samples
    ↓
[30 Days Later: Renewal]
    │ Stripe charges card automatically
    │ Webhook: invoice.paid → Grant 400 more credits
    │ Balance: 350 + 400 = 750 credits (accumulated!)
    ↓
[Uses 300 credits in Month 2]
    │ Balance: 750 → 450
    ↓
[Runs out of credits mid-month]
    │ - Sees "Buy Top-Up Credits" suggestion
    │ - Purchases 150 credits (+10% Pro discount = $16.19)
    │ - Balance: 450 + 150 = 600
    ↓
[Decides to Cancel Subscription]
    │ - Goes to /subscription/manage
    │ - Clicks "Cancel Subscription"
    │ - Choose: "Cancel at period end" (grace period)
    │ - Subscription marked: cancel_at_period_end = true
    │ - Still has access until period ends
    ↓
[Period Ends (Day 60)]
    │ Webhook: customer.subscription.deleted
    │ - All credits reset to 0 (600 → 0)
    │ - No platform access
    │ - Can view old samples but can't process new
    ↓
[Re-subscribes 3 Months Later]
    │ - Subscribes to Ultimate Plan ($49.99/mo)
    │ - Grants 1500 credits
    │ - Starts fresh (no credit history from previous subscription)
```

### 8.2 Edge Case Matrix

```
┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Payment Fails on Renewal                        │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - User has active Pro subscription (400 credits/mo)         │
│ - Balance: 650 credits                                      │
│ - Renewal date arrives, card declined                       │
│                                                              │
│ What Happens:                                                │
│ 1. Stripe attempts payment → Fails                          │
│ 2. Webhook: invoice.payment_failed                          │
│ 3. Subscription status → 'past_due'                         │
│ 4. User KEEPS access and credits (grace period)             │
│ 5. Email sent: "Payment failed, please update card"         │
│ 6. Stripe retries payment (Smart Retries over 7 days)       │
│                                                              │
│ If Payment Succeeds During Retries:                         │
│ - Webhook: invoice.paid                                     │
│ - Status → 'active'                                         │
│ - Grant monthly credits: 650 + 400 = 1050                   │
│ - Normal operation resumes                                  │
│                                                              │
│ If All Retries Fail (7 days):                               │
│ - Webhook: customer.subscription.deleted                    │
│ - Status → 'cancelled'                                      │
│ - Credits reset: 650 → 0                                    │
│ - Platform access locked                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: User Upgrades Mid-Cycle                         │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - User on Basic plan (100 credits/mo, $9.99/mo)            │
│ - Balance: 150 credits                                      │
│ - Billing period: Jan 1 - Jan 31                            │
│ - Upgrades to Pro on Jan 15                                 │
│                                                              │
│ Stripe Behavior (Proration):                                │
│ - Charges prorated amount immediately                       │
│ - Basic: $5 credit for unused 15 days                       │
│ - Pro: $15 charge for remaining 15 days                     │
│ - Net charge: $10                                           │
│ - Resets billing period to Jan 15 - Feb 15                  │
│                                                              │
│ Credit Handling:                                             │
│ - Webhook: customer.subscription.updated                    │
│ - Tier changed: basic → pro                                 │
│ - Monthly allowance updated: 100 → 400                      │
│ - DO NOT grant additional credits immediately               │
│ - Next renewal (Feb 15): Grant 400 credits                  │
│ - Current balance stays: 150 credits                        │
│                                                              │
│ Rationale:                                                   │
│ - User already got 100 credits on Jan 1                     │
│ - Prorated payment doesn't warrant mid-cycle credit grant   │
│ - Prevents double-dipping                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: User Downgrades Mid-Cycle                       │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - User on Ultimate plan (1500 credits/mo, $49.99/mo)       │
│ - Balance: 2000 credits (rolled over from previous month)  │
│ - Downgrades to Basic ($9.99/mo)                            │
│                                                              │
│ Stripe Behavior:                                             │
│ - Generates credit for unused time on Ultimate              │
│ - Applies credit to future invoices                         │
│ - Change takes effect at next billing period                │
│                                                              │
│ Credit Handling:                                             │
│ - Existing credits stay: 2000 (not removed)                 │
│ - User can use 2000 credits until period ends               │
│ - At renewal:                                               │
│   • Subscription tier updates: ultimate → basic             │
│   • Monthly allowance updates: 1500 → 100                   │
│   • Grant 100 credits: 2000 + 100 = 2100                    │
│ - Credits continue accumulating at new rate                 │
│                                                              │
│ Alternative (Strict Policy):                                 │
│ - Cap credits at new tier's allowance                       │
│ - On downgrade, reduce to max 100 credits                   │
│ - Prevents hoarding credits on lower tier                   │
│                                                              │
│ Recommendation: Use lenient policy (don't remove credits)   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Top-Up Purchase Without Subscription            │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - User's subscription expired                               │
│ - Tries to buy top-up credits                               │
│                                                              │
│ Prevention:                                                  │
│ - Frontend: Hide top-up UI if no active subscription        │
│ - Backend: Validate subscription status before checkout     │
│ - Error: "Active subscription required to purchase top-ups" │
│ - Redirect to /pricing page                                 │
│                                                              │
│ Code:                                                        │
│ @router.post("/top-up/checkout")                            │
│ async def create_top_up_checkout(                           │
│     current_user: User = Depends(require_active_subscription)│
│ ):                                                           │
│     # User guaranteed to have subscription here             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Webhook Arrives Before Redirect                 │
├─────────────────────────────────────────────────────────────┤
│ Timeline:                                                    │
│ 1. User completes payment in Stripe (t=0)                   │
│ 2. Stripe sends webhook → Backend (t=0.5s)                  │
│ 3. Backend grants credits (t=1s)                            │
│ 4. Stripe redirects user → Success page (t=2s)              │
│                                                              │
│ Result:                                                      │
│ - Success page loads, credits already granted               │
│ - Shows updated balance immediately                         │
│ - Normal happy path ✅                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Redirect Arrives Before Webhook                 │
├─────────────────────────────────────────────────────────────┤
│ Timeline:                                                    │
│ 1. User completes payment (t=0)                             │
│ 2. Stripe redirects user → Success page (t=0.5s)            │
│ 3. Success page loads, credits NOT updated yet              │
│ 4. Webhook arrives → Backend (t=2s)                         │
│ 5. Backend grants credits (t=2.5s)                          │
│                                                              │
│ Solution:                                                    │
│ - Success page polls for subscription status                │
│ - Shows "Processing..." state                               │
│ - Automatically refreshes when credits appear               │
│ - Max wait: 30 seconds, then show: "Credits processing"     │
│                                                              │
│ Code:                                                        │
│ useEffect(() => {                                            │
│   const interval = setInterval(() => {                      │
│     refetchSubscription();                                  │
│   }, 2000); // Poll every 2s                                │
│                                                              │
│   return () => clearInterval(interval);                     │
│ }, []);                                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Duplicate Webhook Delivery                      │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - Stripe sends invoice.paid webhook                         │
│ - Backend processes, grants 400 credits                     │
│ - Stripe re-sends same webhook (retry/network issue)        │
│                                                              │
│ Prevention (Idempotency):                                    │
│ 1. Check if credits already granted for this invoice        │
│ 2. Look up CreditTransaction by stripe_invoice_id           │
│ 3. If exists with status=completed → Skip                   │
│ 4. Return success (don't error, prevents retry loop)        │
│                                                              │
│ Code:                                                        │
│ async def handle_invoice_paid(invoice):                     │
│     # Check if already processed                            │
│     existing_tx = await get_transaction_by_invoice(         │
│         invoice.id                                          │
│     )                                                        │
│     if existing_tx and existing_tx.status == "completed":   │
│         return  # Already processed, skip                   │
│                                                              │
│     # Process normally...                                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: User Has Credits But Subscription Cancelled     │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - Subscription cancelled yesterday                          │
│ - Credits should be 0, but DB shows 500 (race condition?)   │
│                                                              │
│ Prevention:                                                  │
│ - Enforce in application logic, not just webhooks           │
│ - Every API call checks: has_active_subscription            │
│ - If no subscription → Ignore credit balance, return 0      │
│                                                              │
│ Code:                                                        │
│ @property                                                    │
│ def effective_credits(self) -> int:                         │
│     """Get effective credit balance."""                     │
│     if not self.has_active_subscription:                    │
│         return 0  # No subscription = no credits            │
│     return self.credits                                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASE: Refund After Credits Used                       │
├─────────────────────────────────────────────────────────────┤
│ Scenario:                                                    │
│ - User subscribed to Pro, got 400 credits                   │
│ - Used 300 credits (100 remaining)                          │
│ - Requests refund after 10 days                             │
│                                                              │
│ Stripe Behavior:                                             │
│ - Admin issues refund via Stripe dashboard                  │
│ - Webhook: charge.refunded                                  │
│                                                              │
│ Credit Handling:                                             │
│ - Deduct 400 credits (original grant amount)                │
│ - 100 - 400 = -300... But credits can't go negative!        │
│ - Set credits = 0 (DB constraint prevents negative)         │
│ - Cancel subscription immediately                           │
│ - Log incident for review                                   │
│                                                              │
│ Policy:                                                      │
│ - Refunds only for technical issues, not usage              │
│ - Clear refund policy in TOS                                │
│ - Monitor refund rate (<2% acceptable)                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 8.5 Critical Risk Mitigations (MUST IMPLEMENT)

### Delayed Credit Cleanup (Handles Active Processing)

When subscription is deleted but user has active processing, we delay credit reset:

```python
# backend/app/inngest_functions.py

@inngest_client.create_function(
    fn_id="subscription-cleanup-check",
    trigger=inngest.TriggerEvent(event="subscription/cleanup.check")
)
async def check_subscription_cleanup(
    ctx: inngest.Context,
    step: inngest.Step
):
    """
    Check if subscription can be cleaned up (credits zeroed).
    Called 1 hour after subscription.deleted if processing was active.

    Will retry every hour until processing completes.
    """
    subscription_id = ctx.event.data["subscription_id"]
    user_id = ctx.event.data["user_id"]

    logger.info(f"Checking cleanup eligibility for user {user_id}")

    async with get_db() as db:
        # Check for still-active processing
        pending = await db.execute(
            select(Collection).where(
                Collection.user_id == user_id,
                Collection.status.in_(['pending', 'processing'])
            )
        )

        if pending.scalars().first():
            # Still processing - schedule another check in 1 hour
            logger.info(f"User {user_id} still has active processing. Will check again in 1 hour.")
            await inngest_client.send({
                "name": "subscription/cleanup.check",
                "data": {
                    "subscription_id": subscription_id,
                    "user_id": user_id
                }
            })
            return {"status": "delayed", "reason": "active_processing"}

        # All processing complete - safe to zero credits
        user = await db.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
        )
        user = user.scalar_one()

        previous_balance = user.credits
        user.credits = 0

        # Log the delayed reset
        tx_service = TransactionService(db)
        await tx_service.create_transaction(
            user_id=user_id,
            transaction_type="delayed_cancellation_reset",
            credits_amount=-previous_balance,
            description="Delayed credit reset after processing completed",
            previous_balance=previous_balance,
            new_balance=0,
            status='completed',
            completed_at=datetime.utcnow(),
            metadata={
                "reason": "subscription_cancelled_during_processing",
                "subscription_id": subscription_id
            }
        )

        await db.commit()

        logger.info(
            f"✅ Delayed cleanup completed: user={user_id}, "
            f"credits reset: {previous_balance} → 0"
        )

        return {"status": "completed", "credits_reset": previous_balance}
```

### Credit Reconciliation Service

Detects and corrects drift in credit balances (runs weekly):

```python
# backend/app/services/reconciliation_service.py

from typing import Dict
import logging

logger = logging.getLogger(__name__)

class ReconciliationService:
    """
    Periodically reconcile user credit balances against transaction history.
    Detects and corrects drift caused by bugs or race conditions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def reconcile_user_credits(self, user_id: str) -> Dict:
        """
        Reconcile a single user's credits against transaction history.

        Returns:
            {
                "user_id": str,
                "current_balance": int,
                "calculated_balance": int,
                "drift": int,
                "corrected": bool
            }
        """
        # Get user with lock
        user = await self.db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = user.scalar_one()

        # Calculate expected balance from transaction history
        transactions = await self.db.execute(
            select(CreditTransaction)
            .where(
                CreditTransaction.user_id == user_id,
                CreditTransaction.status == 'completed'
            )
            .order_by(CreditTransaction.created_at.asc())
        )

        calculated_balance = 0
        transaction_count = 0

        for tx in transactions.scalars().all():
            calculated_balance += tx.credits_amount
            transaction_count += 1

        # Compare with actual balance
        current_balance = user.credits
        drift = current_balance - calculated_balance

        if drift != 0:
            logger.error(
                f"⚠️ CREDIT DRIFT DETECTED: user={user_id}, "
                f"current={current_balance}, calculated={calculated_balance}, "
                f"drift={drift}, transactions={transaction_count}"
            )

            # Correct the drift
            user.credits = calculated_balance

            # Create correction transaction
            correction_tx = CreditTransaction(
                user_id=user_id,
                transaction_type="reconciliation_correction",
                credits_amount=-drift,  # Negative to bring back to calculated
                previous_balance=current_balance,
                new_balance=calculated_balance,
                description=f"Automatic correction: drift of {drift} credits detected",
                status='completed',
                completed_at=datetime.utcnow(),
                metadata={
                    "drift_amount": drift,
                    "transaction_count": transaction_count,
                    "reconciliation_date": datetime.utcnow().isoformat()
                }
            )

            self.db.add(correction_tx)
            await self.db.commit()

            # TODO: Send alert to monitoring service
            # await send_alert(f"Credit drift corrected for user {user_id}: {drift} credits")

            return {
                "user_id": str(user_id),
                "current_balance": current_balance,
                "calculated_balance": calculated_balance,
                "drift": drift,
                "corrected": True
            }

        return {
            "user_id": str(user_id),
            "current_balance": current_balance,
            "calculated_balance": calculated_balance,
            "drift": 0,
            "corrected": False
        }

    async def reconcile_all_users(self) -> Dict:
        """
        Reconcile all users with active subscriptions.
        Run this as a scheduled job (weekly).
        """
        # Get all users with subscriptions
        users = await self.db.execute(
            select(User)
            .join(Subscription)
            .where(Subscription.status.in_(['active', 'past_due']))
        )

        results = {
            "total_users": 0,
            "users_with_drift": 0,
            "total_drift": 0,
            "corrected": []
        }

        for user in users.scalars().all():
            result = await self.reconcile_user_credits(user.id)
            results["total_users"] += 1

            if result["drift"] != 0:
                results["users_with_drift"] += 1
                results["total_drift"] += abs(result["drift"])
                results["corrected"].append(result)

        logger.info(
            f"✅ Reconciliation complete: {results['total_users']} users checked, "
            f"{results['users_with_drift']} had drift"
        )

        return results
```

### Weekly Reconciliation Job

```python
# backend/app/inngest_functions.py

@inngest_client.create_function(
    fn_id="weekly-credit-reconciliation",
    trigger=inngest.TriggerCron(cron="0 2 * * 0")  # Every Sunday at 2 AM
)
async def weekly_reconciliation(ctx: inngest.Context, step: inngest.Step):
    """
    Weekly reconciliation of all user credits.
    Detects and corrects any drift between actual and expected balances.
    """
    logger.info("Starting weekly credit reconciliation...")

    async with get_db() as db:
        service = ReconciliationService(db)
        results = await service.reconcile_all_users()

        # Alert if significant drift found
        if results["users_with_drift"] > 0:
            logger.error(
                f"⚠️ Weekly reconciliation found drift in {results['users_with_drift']} users. "
                f"Total drift: {results['total_drift']} credits"
            )

            # Send alert to monitoring service (Sentry, Slack, etc.)
            # await send_monitoring_alert({
            #     "type": "credit_drift_detected",
            #     "affected_users": results["users_with_drift"],
            #     "total_drift": results["total_drift"],
            #     "details": results["corrected"]
            # })

        logger.info("✅ Weekly credit reconciliation completed successfully")
        return results
```

### Critical Testing Checklist

Before deploying to production, test these scenarios:

**1. Race Condition Tests:**
```python
# Test concurrent credit grants (should be idempotent)
async def test_concurrent_webhook_processing():
    # Simulate two webhooks hitting simultaneously
    tasks = [
        add_credits_atomic(user_id, 100, stripe_invoice_id="inv_123"),
        add_credits_atomic(user_id, 100, stripe_invoice_id="inv_123")
    ]
    results = await asyncio.gather(*tasks)

    # Should only grant once due to idempotency
    assert user.credits == 100  # Not 200!
    assert results[0]["duplicate"] == False
    assert results[1]["duplicate"] == True
```

**2. Signature Verification Tests:**
```python
async def test_invalid_signature_rejected():
    response = await client.post(
        "/api/v1/webhooks/stripe",
        json={"type": "invoice.paid", "data": {}},
        headers={"stripe-signature": "invalid_sig"}
    )
    assert response.status_code == 400
    assert "Invalid signature" in response.text
```

**3. Immediate Deletion Tests:**
```python
async def test_deletion_during_processing():
    # Start processing
    collection = await create_collection(user_id)
    assert collection.status == "processing"

    # Delete subscription
    await handle_subscription_deleted(stripe_subscription)

    # Should NOT zero credits yet
    assert user.credits > 0
    assert subscription.status == "cancelled"

    # Should schedule cleanup
    # (Check Inngest events sent)
```

**4. Credit Reconciliation Tests:**
```python
async def test_reconciliation_detects_drift():
    # Manually corrupt credits
    user.credits = 500  # Should be 400 based on transactions

    result = await reconciliation_service.reconcile_user_credits(user.id)

    assert result["drift"] == 100
    assert result["corrected"] == True
    assert user.credits == 400  # Corrected
```

---

## 9. Security & Compliance

### 9.1 Critical Security Measures

```
✅ WEBHOOK SIGNATURE VERIFICATION (Highest Priority)
   - ALWAYS verify Stripe-Signature header
   - Use stripe.Webhook.construct_event()
   - Reject requests with invalid signatures
   - Prevents attackers from spoofing webhooks and granting credits

✅ HTTPS ONLY IN PRODUCTION
   - TLS 1.2+ required
   - Webhook endpoint must be HTTPS
   - Stripe will not deliver to HTTP

✅ IDEMPOTENCY
   - Check for duplicate webhook events
   - Use stripe_invoice_id to detect duplicates
   - Prevents double-crediting

✅ DATABASE CONSTRAINTS
   - credits >= 0 (prevent negative balances)
   - CHECK constraints on subscriptions table
   - Foreign key cascades configured correctly

✅ ATOMIC OPERATIONS
   - Use database transactions with locks
   - SELECT FOR UPDATE when modifying credits
   - Prevents race conditions

✅ AUTHENTICATION
   - Clerk JWT verification on all protected routes
   - User ID from verified token only (never from request body)
   - require_active_subscription dependency

✅ RATE LIMITING
   - Limit subscription checkout creation (prevent abuse)
   - Limit top-up purchases (prevent fraud)
   - Slowapi rate limiter on critical endpoints

✅ ENVIRONMENT SEPARATION
   - Different webhook secrets per environment
   - Dev: whsec_test_xxx
   - Prod: whsec_xxx
   - Never mix test/prod keys
```

### 9.2 Stripe Security Best Practices

```python
# GOOD: Verify webhook signature
@router.post("/stripe-webhook")
async def handle_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature")
):
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            settings.STRIPE_WEBHOOK_SECRET  # ← Verification
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Process event...


# BAD: No verification (VULNERABLE!)
@router.post("/stripe-webhook")
async def handle_webhook(request: Request):
    data = await request.json()
    event_type = data["type"]  # ← Anyone can send this!

    # ❌ CRITICAL VULNERABILITY: No signature check
    # Attacker can grant themselves unlimited credits
```

---

## 10. Testing Strategy

### 10.1 Stripe Test Mode Setup

```bash
# Use test mode keys for development
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_test_xxxxxxxxxxxxxxxxxxxxx
```

**Test Credit Cards:**
```
✅ Success: 4242 4242 4242 4242
   - Expiry: Any future date
   - CVC: Any 3 digits

❌ Declined: 4000 0000 0000 0002
   - Card will be declined

🔐 3D Secure Required: 4000 0025 0000 3155
   - Triggers authentication flow

🔄 Insufficient Funds: 4000 0000 0000 9995
   - Payment fails with specific error
```

### 10.2 Test Scenarios Checklist

```
┌─────────────────────────────────────────────────────────────┐
│ SUBSCRIPTION LIFECYCLE TESTS                                │
├─────────────────────────────────────────────────────────────┤
│ □ New subscription (all tiers)                              │
│ □ Monthly renewal (credits granted)                         │
│ □ Annual subscription                                        │
│ □ Upgrade tier mid-cycle                                    │
│ □ Downgrade tier mid-cycle                                  │
│ □ Cancel subscription (cancel_at_period_end)                │
│ □ Cancel subscription (immediate)                           │
│ □ Re-subscribe after cancellation                           │
│ □ Trial period (if enabled)                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ PAYMENT TESTS                                               │
├─────────────────────────────────────────────────────────────┤
│ □ Successful payment                                        │
│ □ Declined card                                             │
│ □ 3D Secure authentication                                  │
│ □ Payment retry (failed → succeeds)                         │
│ □ Payment retry (fails completely)                          │
│ □ Top-up purchase (with subscription)                       │
│ □ Top-up purchase (without subscription) → Blocked          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ CREDIT TESTS                                                │
├─────────────────────────────────────────────────────────────┤
│ □ Credits granted on subscription                           │
│ □ Credits granted on renewal                                │
│ □ Credits accumulate (rollover)                             │
│ □ Credits deducted for collection processing                │
│ □ Credits refunded for failed videos                        │
│ □ Credits reset to 0 on cancellation                        │
│ □ Top-up credits added correctly                            │
│ □ Tier discount applied to top-ups                          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ WEBHOOK TESTS                                               │
├─────────────────────────────────────────────────────────────┤
│ □ customer.subscription.created                             │
│ □ customer.subscription.updated                             │
│ □ customer.subscription.deleted                             │
│ □ invoice.paid (subscription)                               │
│ □ invoice.payment_failed                                    │
│ □ checkout.session.completed (top-up)                       │
│ □ Duplicate webhook (idempotency)                           │
│ □ Invalid signature → Rejected                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ ACCESS CONTROL TESTS                                        │
├─────────────────────────────────────────────────────────────┤
│ □ Active subscription → Can process collections             │
│ □ No subscription → Blocked with error message              │
│ □ past_due status → Still has access (grace period)         │
│ □ cancelled status → No access                              │
│ □ Insufficient credits → Blocked with suggestion            │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ EDGE CASES                                                  │
├─────────────────────────────────────────────────────────────┤
│ □ Webhook arrives before redirect                           │
│ □ Redirect arrives before webhook                           │
│ □ Concurrent credit deduction (race condition)              │
│ □ Refund after credits used                                 │
│ □ Subscription cancelled mid-processing                     │
└─────────────────────────────────────────────────────────────┘
```

### 10.3 Local Webhook Testing

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhooks to local backend
stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe

# In another terminal, trigger test events
stripe trigger customer.subscription.created
stripe trigger invoice.paid
stripe trigger customer.subscription.deleted
```

---

## 11. Deployment Plan

### 11.1 Pre-Deployment Checklist

```
□ STRIPE SETUP
  □ Create production Stripe account
  □ Create subscription products (Basic, Pro, Ultimate)
  □ Create annual pricing variants
  □ Create top-up products
  □ Copy all Price IDs
  □ Configure webhook endpoint
  □ Get production API keys
  □ Get webhook signing secret

□ DATABASE
  □ Backup production database
  □ Run migrations locally
  □ Test rollback
  □ Run migrations in production
  □ Verify tables created

□ BACKEND
  □ Add Stripe secrets to GCP Secret Manager
  □ Update Cloud Run environment variables
  □ Deploy backend
  □ Test webhook endpoint (Stripe CLI)
  □ Verify API endpoints

□ FRONTEND
  □ Add NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  □ Update pricing page with production prices
  □ Deploy to Vercel
  □ Test end-to-end flow

□ TESTING
  □ Make test subscription (small amount)
  □ Verify credits granted
  □ Process test collection
  □ Cancel subscription
  □ Verify credits reset
  □ Check webhook logs

□ MONITORING
  □ Set up Stripe webhook monitoring
  □ Configure error alerts
  □ Set up revenue tracking
  □ Monitor failed payments
  □ Track conversion funnel
```

### 11.2 Environment Variables

```bash
# Backend (GCP Secret Manager)
STRIPE_SECRET_KEY=sk_live_xxxxxxxxxxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxxxxxxxxxx

# Subscription Price IDs
STRIPE_PRICE_BASIC_MONTHLY=price_xxxxx
STRIPE_PRICE_BASIC_ANNUAL=price_xxxxx
STRIPE_PRICE_PRO_MONTHLY=price_xxxxx
STRIPE_PRICE_PRO_ANNUAL=price_xxxxx
STRIPE_PRICE_ULTIMATE_MONTHLY=price_xxxxx
STRIPE_PRICE_ULTIMATE_ANNUAL=price_xxxxx

# Top-up Price IDs
STRIPE_PRICE_TOPUP_SMALL=price_xxxxx
STRIPE_PRICE_TOPUP_MEDIUM=price_xxxxx
STRIPE_PRICE_TOPUP_LARGE=price_xxxxx

# URLs
SUBSCRIPTION_SUCCESS_URL=https://sampletok.com/subscription/success
SUBSCRIPTION_CANCEL_URL=https://sampletok.com/pricing

# Frontend (Vercel)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_live_xxxxxxxxxxxxxxxxxxxxx
NEXT_PUBLIC_API_URL=https://api.sampletok.com
```

---

## 12. Key Differences from One-Time Purchase Model

| Aspect | One-Time Purchase | Subscription (This Plan) |
|--------|------------------|-------------------------|
| **Revenue Model** | Single transactions | Recurring monthly/annual |
| **Credit Persistence** | Forever (until used) | Lost on cancellation |
| **Free Tier** | 10 free credits | No free tier |
| **Credit Rollover** | N/A (purchased credits stay) | Unlimited while subscribed |
| **Pricing** | $4.99-$39.99 per pack | $9.99-$49.99 per month |
| **Platform Access** | Always (if have credits) | Only with active subscription |
| **Grace Period** | N/A | Yes (past_due status) |
| **Top-Ups** | Primary model | Secondary (subscribers only) |
| **Stripe API** | Checkout (one-time payment) | Subscriptions API |
| **Webhooks** | checkout.session.completed | subscription.*, invoice.* |
| **Complexity** | Lower | Higher (lifecycle management) |
| **Revenue Predictability** | Low | High (MRR) |
| **Customer Retention** | Low | Higher (lock-in via credits) |

---

## Implementation Timeline

```
WEEK 1: Database & Backend Core
├─ Day 1: Database models (Subscription, CreditTransaction, StripeCustomer)
├─ Day 2: Alembic migrations, test locally
├─ Day 3: Subscription service + Stripe integration
├─ Day 4: Webhook handlers (subscription lifecycle)
└─ Day 5: API endpoints (subscriptions, credits)

WEEK 2: Payment Flow & Top-Ups
├─ Day 1: Payment service for top-ups
├─ Day 2: Enhanced credit service (subscription logic)
├─ Day 3: Access control dependencies
├─ Day 4: Top-up webhook handling
└─ Day 5: Testing webhooks locally (Stripe CLI)

WEEK 3: Frontend Development
├─ Day 1: Pricing page component
├─ Day 2: Subscription hooks & API client
├─ Day 3: Success/cancel pages
├─ Day 4: Subscription status widget
└─ Day 5: Top-up purchase UI

WEEK 4: Testing, Deployment & Launch
├─ Day 1: End-to-end testing (test mode)
├─ Day 2: Stripe production setup
├─ Day 3: Production deployment (backend + frontend)
├─ Day 4: Production testing + monitoring
└─ Day 5: Soft launch + adjustments
```

---

## Success Metrics

```
CONVERSION FUNNEL:
├─ Homepage Visit → Pricing Page: Target 30%
├─ Pricing Page → Checkout: Target 20%
├─ Checkout Started → Completed: Target 70%
└─ Overall Conversion: ~4-5%

REVENUE METRICS:
├─ Monthly Recurring Revenue (MRR): Primary KPI
├─ Average Revenue Per User (ARPU): $20-30/mo
├─ Customer Lifetime Value (LTV): $200-300
├─ Churn Rate: Target <5% monthly

OPERATIONAL:
├─ Payment Success Rate: >95%
├─ Webhook Processing Time: <2s
├─ Failed Payment Recovery: >50%
└─ Support Tickets (payment): <2% of users

USER ENGAGEMENT:
├─ Credit Utilization Rate: >60% of monthly allowance
├─ Top-Up Purchase Rate: 10-15% of subscribers
├─ Upgrade Rate (Basic → Pro): >20% within 3 months
└─ Re-subscription Rate: >30% after cancellation
```

---

## Conclusion

This subscription-based model provides:

✅ **Recurring Revenue**: Predictable MRR from subscriptions
✅ **Strong Retention**: Credits lost on churn incentivizes staying subscribed
✅ **Flexible Capacity**: Top-ups for subscribers who need more
✅ **Better Unit Economics**: Higher LTV vs one-time purchases
✅ **SaaS Metrics**: Track MRR, churn, ARPU like traditional SaaS
✅ **Splice-Style Model**: Proven model from successful audio platform

**Advantages Over One-Time Purchase:**
- More predictable revenue (MRR vs sporadic purchases)
- Higher customer lifetime value
- Lower customer acquisition cost (CAC) payback period
- Better retention through credit lock-in
- Clearer upgrade path (tier-based)

**Next Steps:**
1. Review this plan and confirm model details
2. Set up Stripe account and products
3. Begin implementation following 4-week timeline
4. Test thoroughly in test mode
5. Deploy to production with monitoring
