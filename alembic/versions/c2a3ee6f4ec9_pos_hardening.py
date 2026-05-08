"""pos_hardening

Revision ID: c2a3ee6f4ec9
Revises: 20260508_0001
Create Date: 2026-05-08 06:10:37.557789+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c2a3ee6f4ec9'
down_revision: Union[str, None] = '20260508_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Data Cleanup: Map existing values to new Enum values ---
    op.execute("UPDATE orders SET status = 'pending' WHERE status NOT IN ('pending', 'paid', 'cancelled', 'refunded', 'completed')")
    op.execute("UPDATE orders SET payment_method = 'promptpay' WHERE payment_method = 'qr'")
    op.execute("UPDATE orders SET payment_method = 'cash' WHERE payment_method NOT IN ('cash', 'promptpay', 'credit_card', 'transfer')")
    
    op.execute("UPDATE payments SET method = 'promptpay' WHERE method = 'qr'")
    op.execute("UPDATE payments SET method = 'cash' WHERE method NOT IN ('cash', 'promptpay', 'credit_card', 'transfer')")

    # --- Create Enum types manually ---
    ordertype_enum = postgresql.ENUM('pos', 'online', name='ordertype')
    ordertype_enum.create(op.get_bind())
    
    orderstatus_enum = postgresql.ENUM('pending', 'paid', 'cancelled', 'refunded', 'completed', name='orderstatus')
    orderstatus_enum.create(op.get_bind())
    
    paymentmethod_enum = postgresql.ENUM('cash', 'promptpay', 'credit_card', 'transfer', name='paymentmethod')
    paymentmethod_enum.create(op.get_bind())

    # --- Apply changes ---
    op.add_column('orders', sa.Column('order_type', sa.Enum('pos', 'online', name='ordertype'), nullable=True))
    op.execute("UPDATE orders SET order_type = 'online'") # Default existing to online
    
    # Casting for orders.status
    op.execute("ALTER TABLE orders ALTER COLUMN status TYPE orderstatus USING status::orderstatus")
    
    # Casting for orders.payment_method
    op.execute("ALTER TABLE orders ALTER COLUMN payment_method TYPE paymentmethod USING payment_method::paymentmethod")
    
    # Casting for payments.method
    op.execute("ALTER TABLE payments ALTER COLUMN method TYPE paymentmethod USING method::paymentmethod")

    op.add_column('products', sa.Column('sku', sa.String(), nullable=True))
    op.add_column('products', sa.Column('barcode', sa.String(), nullable=True))
    op.add_column('products', sa.Column('cost_price', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('products', sa.Column('selling_price', sa.Float(), nullable=True, server_default='0.0'))
    op.add_column('products', sa.Column('low_stock_alert', sa.Integer(), nullable=True, server_default='10'))
    op.add_column('products', sa.Column('image_url', sa.String(), nullable=True))
    op.add_column('products', sa.Column('status', sa.String(), nullable=True, server_default='active'))
    op.add_column('products', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))
    op.add_column('products', sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))
    op.create_index(op.f('ix_products_barcode'), 'products', ['barcode'], unique=True)
    op.create_index(op.f('ix_products_name'), 'products', ['name'], unique=False)
    op.create_index(op.f('ix_products_sku'), 'products', ['sku'], unique=True)
    op.add_column('users', sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_column('users', 'created_at')
    op.drop_index(op.f('ix_products_sku'), table_name='products')
    op.drop_index(op.f('ix_products_name'), table_name='products')
    op.drop_index(op.f('ix_products_barcode'), table_name='products')
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'created_at')
    op.drop_column('products', 'status')
    op.drop_column('products', 'image_url')
    op.drop_column('products', 'low_stock_alert')
    op.drop_column('products', 'selling_price')
    op.drop_column('products', 'cost_price')
    op.drop_column('products', 'barcode')
    op.drop_column('products', 'sku')
    
    # Downgrade enums back to varchar
    op.alter_column('payments', 'method', type_=sa.VARCHAR(), existing_type=sa.Enum(name='paymentmethod'))
    op.alter_column('orders', 'payment_method', type_=sa.VARCHAR(), existing_type=sa.Enum(name='paymentmethod'))
    op.alter_column('orders', 'status', type_=sa.VARCHAR(), existing_type=sa.Enum(name='orderstatus'))
    op.drop_column('orders', 'order_type')
    
    # Drop Enum types
    op.execute("DROP TYPE ordertype")
    op.execute("DROP TYPE orderstatus")
    op.execute("DROP TYPE paymentmethod")
