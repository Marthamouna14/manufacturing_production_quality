from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Date, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base
class Stamp:
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    updated_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    is_deleted: Mapped[bool]=mapped_column(Boolean,default=False)
class User(Stamp,Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    full_name:Mapped[str]=mapped_column(String(120))
    email:Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash:Mapped[str]=mapped_column(String(255))
    role:Mapped[str]=mapped_column(String(40),default="Worker",index=True)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
class Plant(Stamp,Base):
    __tablename__="plants"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(150))
    address:Mapped[str]=mapped_column(Text,default="")
    production_capacity:Mapped[float]=mapped_column(Float,default=0)
    status:Mapped[str]=mapped_column(String(30),default="Active")
    manager_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
class ProductionLine(Stamp,Base):
    __tablename__="production_lines"
    id:Mapped[int]=mapped_column(primary_key=True)
    plant_id:Mapped[int]=mapped_column(ForeignKey("plants.id"),index=True)
    code:Mapped[str]=mapped_column(String(40))
    name:Mapped[str]=mapped_column(String(120))
    capacity:Mapped[float]=mapped_column(Float,default=0)
    status:Mapped[str]=mapped_column(String(30),default="Active")
    supervisor_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    __table_args__=(UniqueConstraint("plant_id","code",name="uq_line_plant_code"),)
class Product(Stamp,Base):
    __tablename__="products"
    id:Mapped[int]=mapped_column(primary_key=True)
    sku:Mapped[str]=mapped_column(String(60),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(160),index=True)
    category:Mapped[str]=mapped_column(String(100),default="General")
    unit:Mapped[str]=mapped_column(String(30),default="piece")
    status:Mapped[str]=mapped_column(String(30),default="Active")
    standard_production_minutes:Mapped[float]=mapped_column(Float,default=1)
class Material(Stamp,Base):
    __tablename__="materials"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(160),index=True)
    category:Mapped[str]=mapped_column(String(100),default="General")
    unit:Mapped[str]=mapped_column(String(30),default="unit")
    available_quantity:Mapped[float]=mapped_column(Float,default=0)
    minimum_stock_level:Mapped[float]=mapped_column(Float,default=0)
    reorder_level:Mapped[float]=mapped_column(Float,default=0)
    supplier_reference:Mapped[str|None]=mapped_column(String(120),nullable=True)
    status:Mapped[str]=mapped_column(String(30),default="Active")
class BOMItem(Stamp,Base):
    __tablename__="bom_items"
    id:Mapped[int]=mapped_column(primary_key=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    material_id:Mapped[int]=mapped_column(ForeignKey("materials.id"),index=True)
    quantity_per_product:Mapped[float]=mapped_column(Float)
    version:Mapped[int]=mapped_column(Integer,default=1)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
class Machine(Stamp,Base):
    __tablename__="machines"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(60),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(120))
    machine_type:Mapped[str]=mapped_column(String(100),default="General")
    line_id:Mapped[int]=mapped_column(ForeignKey("production_lines.id"),index=True)
    installation_date:Mapped[date|None]=mapped_column(Date,nullable=True)
    status:Mapped[str]=mapped_column(String(30),default="Idle")
    operating_hours:Mapped[float]=mapped_column(Float,default=0)
class ProductionOrder(Stamp,Base):
    __tablename__="production_orders"
    id:Mapped[int]=mapped_column(primary_key=True)
    order_number:Mapped[str]=mapped_column(String(60),unique=True,index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    line_id:Mapped[int]=mapped_column(ForeignKey("production_lines.id"),index=True)
    quantity:Mapped[int]=mapped_column(Integer)
    target_date:Mapped[date]=mapped_column(Date)
    priority:Mapped[str]=mapped_column(String(20),default="Normal")
    supervisor_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    status:Mapped[str]=mapped_column(String(30),default="Draft",index=True)
    supervisor_reviewed:Mapped[bool]=mapped_column(Boolean,default=False)
    manager_approved:Mapped[bool]=mapped_column(Boolean,default=False)
class ProductionBatch(Stamp,Base):
    __tablename__="production_batches"
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_number:Mapped[str]=mapped_column(String(60),unique=True,index=True)
    order_id:Mapped[int]=mapped_column(ForeignKey("production_orders.id"),index=True)
    line_id:Mapped[int]=mapped_column(ForeignKey("production_lines.id"),index=True)
    machine_id:Mapped[int|None]=mapped_column(ForeignKey("machines.id"),nullable=True)
    supervisor_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    planned_quantity:Mapped[int]=mapped_column(Integer)
    produced_quantity:Mapped[int]=mapped_column(Integer,default=0)
    rejected_quantity:Mapped[int]=mapped_column(Integer,default=0)
    started_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    ended_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class QualityInspection(Stamp,Base):
    __tablename__="quality_inspections"
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey("production_batches.id"),index=True)
    inspection_type:Mapped[str]=mapped_column(String(60))
    inspector_id:Mapped[int]=mapped_column(ForeignKey("users.id"))
    parameter:Mapped[str]=mapped_column(String(120))
    expected_value:Mapped[str]=mapped_column(String(120))
    actual_value:Mapped[str]=mapped_column(String(120))
    result:Mapped[str]=mapped_column(String(20),index=True)
    remarks:Mapped[str]=mapped_column(Text,default="")
class Defect(Stamp,Base):
    __tablename__="defects"
    id:Mapped[int]=mapped_column(primary_key=True)
    batch_id:Mapped[int]=mapped_column(ForeignKey("production_batches.id"),index=True)
    product_id:Mapped[int]=mapped_column(ForeignKey("products.id"),index=True)
    defect_type:Mapped[str]=mapped_column(String(120))
    severity:Mapped[str]=mapped_column(String(20),default="Minor")
    quantity_affected:Mapped[int]=mapped_column(Integer)
    root_cause:Mapped[str]=mapped_column(Text,default="")
    corrective_action:Mapped[str]=mapped_column(Text,default="")
    resolution_status:Mapped[str]=mapped_column(String(30),default="Open")
class InventoryMovement(Stamp,Base):
    __tablename__="inventory_movements"
    id:Mapped[int]=mapped_column(primary_key=True)
    material_id:Mapped[int]=mapped_column(ForeignKey("materials.id"),index=True)
    movement_type:Mapped[str]=mapped_column(String(30))
    quantity:Mapped[float]=mapped_column(Float)
    reference:Mapped[str]=mapped_column(String(120),default="")
    performed_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
    notes:Mapped[str]=mapped_column(Text,default="")
class MaintenanceRecord(Stamp,Base):
    __tablename__="maintenance_records"
    id:Mapped[int]=mapped_column(primary_key=True)
    machine_id:Mapped[int]=mapped_column(ForeignKey("machines.id"),index=True)
    maintenance_type:Mapped[str]=mapped_column(String(40))
    scheduled_at:Mapped[datetime]=mapped_column(DateTime)
    completed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    technician_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    cost:Mapped[float]=mapped_column(Float,default=0)
    spare_parts_notes:Mapped[str]=mapped_column(Text,default="")
    status:Mapped[str]=mapped_column(String(30),default="Scheduled")
class DowntimeRecord(Stamp,Base):
    __tablename__="downtime_records"
    id:Mapped[int]=mapped_column(primary_key=True)
    machine_id:Mapped[int]=mapped_column(ForeignKey("machines.id"),index=True)
    line_id:Mapped[int]=mapped_column(ForeignKey("production_lines.id"),index=True)
    start_time:Mapped[datetime]=mapped_column(DateTime)
    end_time:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    category:Mapped[str]=mapped_column(String(50))
    reason:Mapped[str]=mapped_column(Text,default="")
    responsible_person_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    action:Mapped[str]=mapped_column(String(100),index=True)
    entity:Mapped[str]=mapped_column(String(100),index=True)
    entity_id:Mapped[str]=mapped_column(String(80),default="")
    previous_value:Mapped[str]=mapped_column(Text,default="")
    new_value:Mapped[str]=mapped_column(Text,default="")
    timestamp:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
class Notification(Stamp,Base):
    __tablename__="notifications"
    id:Mapped[int]=mapped_column(primary_key=True)
    category:Mapped[str]=mapped_column(String(60),index=True)
    message:Mapped[str]=mapped_column(Text)
    entity:Mapped[str]=mapped_column(String(100),default="")
    entity_id:Mapped[str]=mapped_column(String(80),default="")
    is_read:Mapped[bool]=mapped_column(Boolean,default=False)
