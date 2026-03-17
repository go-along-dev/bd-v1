from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone


revision = '856309d0de69'
down_revision = '65e1286bfeaf'
branch_labels = None
depends_on = None


def upgrade() -> None:
    now = datetime.now(timezone.utc)

    op.execute(f"""
        INSERT INTO platform_config (id, key, value, description, updated_at)
        VALUES
        (gen_random_uuid(), 'fuel_price_per_litre',       '103.00',  'Petrol price per litre in INR',                              '{now}'),
        (gen_random_uuid(), 'platform_commission_pct',    '10',      'Platform margin percentage added to fuel cost',              '{now}'),
        (gen_random_uuid(), 'min_fare',                   '50.00',   'Minimum fare floor in INR',                                  '{now}'),
        (gen_random_uuid(), 'fare_rounding',              '5',       'Round fare to nearest N rupees',                             '{now}'),
        (gen_random_uuid(), 'max_seats_per_booking',      '4',       'Maximum seats a passenger can book in one booking',          '{now}'),
        (gen_random_uuid(), 'cancellation_window_hours',  '2',       'Hours before departure within which cancellation is blocked','{now}'),
        (gen_random_uuid(), 'cashback_eligibility_days',  '90',      'Days from driver onboarding during which cashback is valid', '{now}'),
        (gen_random_uuid(), 'max_cashback_per_ride',      '500.00',  'Maximum cashback amount per ride in INR',                    '{now}'),
        (gen_random_uuid(), 'max_withdrawal_amount',      '5000.00', 'Maximum single withdrawal amount in INR',                    '{now}')
    """)


def downgrade() -> None:
    op.execute("DELETE FROM platform_config")