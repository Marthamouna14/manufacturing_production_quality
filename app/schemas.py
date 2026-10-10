from datetime import date,datetime
from pydantic import BaseModel,EmailStr,Field,ConfigDict,model_validator
class UserCreate(BaseModel):
    full_name:str
    email:EmailStr
    password:str=Field(min_length=8,max_length=72)
    role:str="Worker"
class UserOut(BaseModel):
    id:int; full_name:str; email:EmailStr; role:str; is_active:bool
    model_config=ConfigDict(from_attributes=True)
class RefreshIn(BaseModel): refresh_token:str
class PlantIn(BaseModel):
    code:str; name:str; address:str=""; production_capacity:float=Field(ge=0); status:str="Active"; manager_id:int|None=None
class LineIn(BaseModel):
    plant_id:int; code:str; name:str; capacity:float=Field(ge=0); status:str="Active"; supervisor_id:int|None=None
class ProductIn(BaseModel):
    sku:str; name:str; category:str="General"; unit:str="piece"; status:str="Active"; standard_production_minutes:float=Field(default=1,gt=0)
class MaterialIn(BaseModel):
    code:str; name:str; category:str="General"; unit:str="unit"; available_quantity:float=Field(default=0,ge=0); minimum_stock_level:float=Field(default=0,ge=0); reorder_level:float=Field(default=0,ge=0); supplier_reference:str|None=None; status:str="Active"
class BOMIn(BaseModel):
    product_id:int; material_id:int; quantity_per_product:float=Field(gt=0); version:int=Field(default=1,ge=1); is_active:bool=True
class MachineIn(BaseModel):
    code:str; name:str; machine_type:str="General"; line_id:int; installation_date:date|None=None; status:str="Idle"; operating_hours:float=Field(default=0,ge=0)
class OrderIn(BaseModel):
    order_number:str; product_id:int; line_id:int; quantity:int=Field(gt=0); target_date:date; priority:str="Normal"; supervisor_id:int|None=None
class BatchIn(BaseModel):
    batch_number:str; order_id:int; line_id:int; machine_id:int|None=None; supervisor_id:int|None=None; planned_quantity:int=Field(gt=0)
class OutputIn(BaseModel):
    produced_quantity:int=Field(ge=0); rejected_quantity:int=Field(ge=0)
    @model_validator(mode="after")
    def valid_rejected(self):
        if self.rejected_quantity>self.produced_quantity: raise ValueError("Rejected quantity cannot exceed produced quantity")
        return self
class InspectionIn(BaseModel):
    batch_id:int; inspection_type:str; parameter:str; expected_value:str; actual_value:str; result:str; remarks:str=""
class DefectIn(BaseModel):
    batch_id:int; product_id:int; defect_type:str; severity:str="Minor"; quantity_affected:int=Field(gt=0); root_cause:str=""; corrective_action:str=""
class MovementIn(BaseModel):
    material_id:int; movement_type:str; quantity:float=Field(gt=0); reference:str=""; notes:str=""
class MaintenanceIn(BaseModel):
    machine_id:int; maintenance_type:str; scheduled_at:datetime; technician_id:int|None=None; cost:float=Field(default=0,ge=0); spare_parts_notes:str=""
class DowntimeIn(BaseModel):
    machine_id:int; line_id:int; start_time:datetime; end_time:datetime|None=None; category:str; reason:str=""; responsible_person_id:int|None=None
