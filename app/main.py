from datetime import datetime
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from jose import jwt,JWTError
from app.core.config import settings
from app.db.session import Base,engine,get_db
from app.models import *
from app.schemas import *
from app.security import hash_password,verify_password,token,current_user,roles
app=FastAPI(title=settings.app_name,version="1.0.0",description="Manufacturing operations, production, quality, inventory and analytics API")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(","),allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def startup(): Base.metadata.create_all(bind=engine)
def audit(db,u,action,entity,eid,old="",new=""):
    db.add(AuditLog(user_id=u.id if u else None,action=action,entity=entity,entity_id=str(eid),previous_value=str(old),new_value=str(new)))
@app.get("/")
def root(): return {"message":settings.app_name,"docs":"/docs","health":"/health"}
@app.get("/health")
def health(): return {"status":"ok"}
@app.post("/api/v1/auth/register",response_model=UserOut,tags=["Authentication"])
def register(d:UserCreate,db:Session=Depends(get_db)):
    if db.query(User).filter_by(email=d.email).first(): raise HTTPException(409,"Email already registered")
    allowed={"Super Admin","Plant Manager","Production Manager","Quality Manager","Maintenance Engineer","Store Manager","Production Supervisor","Worker"}
    if d.role not in allowed: raise HTTPException(422,"Invalid role")
    u=User(full_name=d.full_name,email=d.email,password_hash=hash_password(d.password),role=d.role)
    db.add(u);db.flush();audit(db,u,"REGISTER","User",u.id);db.commit();db.refresh(u);return u
@app.post("/api/v1/auth/login",tags=["Authentication"])
def login(f:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    u=db.query(User).filter_by(email=f.username).first()
    if not u or not verify_password(f.password,u.password_hash): raise HTTPException(401,"Incorrect email or password")
    if not u.is_active: raise HTTPException(403,"Account deactivated")
    audit(db,u,"LOGIN","User",u.id);db.commit()
    return {"access_token":token(u.id,"access",settings.access_token_minutes),"refresh_token":token(u.id,"refresh",settings.refresh_token_days*1440),"token_type":"bearer"}
@app.post("/api/v1/auth/refresh",tags=["Authentication"])
def refresh(d:RefreshIn,db:Session=Depends(get_db)):
    try:
        p=jwt.decode(d.refresh_token,settings.secret_key,algorithms=["HS256"])
        if p.get("type")!="refresh": raise HTTPException(401,"Invalid refresh token")
        u=db.get(User,int(p["sub"]))
    except (JWTError,ValueError): raise HTTPException(401,"Invalid refresh token")
    if not u or not u.is_active: raise HTTPException(401,"User inactive or missing")
    return {"access_token":token(u.id,"access",settings.access_token_minutes),"token_type":"bearer"}
@app.post("/api/v1/auth/logout",tags=["Authentication"])
def logout(u=Depends(current_user),db:Session=Depends(get_db)):
    audit(db,u,"LOGOUT","User",u.id);db.commit();return {"message":"Remove tokens on client; server-side revocation requires a token store."}
@app.get("/api/v1/auth/me",response_model=UserOut,tags=["Authentication"])
def me(u=Depends(current_user)): return u
@app.patch("/api/v1/auth/users/{uid}/activation",tags=["Authentication"])
def activation(uid:int,active:bool,db:Session=Depends(get_db),u=Depends(roles("Super Admin"))):
    x=db.get(User,uid)
    if not x: raise HTTPException(404,"User not found")
    old=x.is_active;x.is_active=active;audit(db,u,"ACCOUNT_STATUS","User",uid,old,active);db.commit();return {"id":uid,"is_active":active}
@app.post("/api/v1/plants",tags=["Plants"])
def plant_create(d:PlantIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager"))):
    x=Plant(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","Plant",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/plants",tags=["Plants"])
def plants(search:str|None=None,status:str|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(Plant).filter(Plant.is_deleted==False)
    if search:q=q.filter((Plant.name.ilike(f"%{search}%"))|(Plant.code.ilike(f"%{search}%")))
    if status:q=q.filter(Plant.status==status)
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.get("/api/v1/plants/{pid}",tags=["Plants"])
def plant_detail(pid:int,db:Session=Depends(get_db),u=Depends(current_user)):
    x=db.get(Plant,pid)
    if not x or x.is_deleted: raise HTTPException(404,"Plant not found")
    return x
@app.patch("/api/v1/plants/{pid}",tags=["Plants"])
def plant_update(pid:int,d:PlantIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager"))):
    x=db.get(Plant,pid)
    if not x: raise HTTPException(404,"Plant not found")
    old={"name":x.name,"status":x.status}
    for k,v in d.model_dump().items():setattr(x,k,v)
    audit(db,u,"UPDATE","Plant",pid,old,d.model_dump());db.commit();db.refresh(x);return x
@app.post("/api/v1/production-lines",tags=["Production Lines"])
def line_create(d:LineIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager","Production Manager"))):
    if not db.get(Plant,d.plant_id):raise HTTPException(404,"Plant not found")
    x=ProductionLine(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","ProductionLine",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/production-lines",tags=["Production Lines"])
def lines(plant_id:int|None=None,status:str|None=None,search:str|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(ProductionLine).filter(ProductionLine.is_deleted==False)
    if plant_id:q=q.filter(ProductionLine.plant_id==plant_id)
    if status:q=q.filter(ProductionLine.status==status)
    if search:q=q.filter((ProductionLine.name.ilike(f"%{search}%"))|(ProductionLine.code.ilike(f"%{search}%")))
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.post("/api/v1/products",tags=["Products"])
def product_create(d:ProductIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager","Production Manager"))):
    x=Product(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","Product",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/products",tags=["Products"])
def products(search:str|None=None,category:str|None=None,status:str|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(Product).filter(Product.is_deleted==False)
    if search:q=q.filter((Product.name.ilike(f"%{search}%"))|(Product.sku.ilike(f"%{search}%")))
    if category:q=q.filter(Product.category==category)
    if status:q=q.filter(Product.status==status)
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.post("/api/v1/materials",tags=["Materials"])
def material_create(d:MaterialIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Store Manager"))):
    x=Material(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","Material",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/materials",tags=["Materials"])
def materials(low_stock:bool=False,search:str|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(Material).filter(Material.is_deleted==False)
    if search:q=q.filter((Material.name.ilike(f"%{search}%"))|(Material.code.ilike(f"%{search}%")))
    if low_stock:q=q.filter(Material.available_quantity<=Material.reorder_level)
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.post("/api/v1/bom",tags=["BOM"])
def bom_create(d:BOMIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager"))):
    if not db.get(Product,d.product_id) or not db.get(Material,d.material_id):raise HTTPException(404,"Product/material not found")
    x=BOMItem(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","BOMItem",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/bom/{product_id}",tags=["BOM"])
def bom_list(product_id:int,db:Session=Depends(get_db),u=Depends(current_user)):
    return db.query(BOMItem).filter_by(product_id=product_id,is_active=True).all()
@app.post("/api/v1/machines",tags=["Machines"])
def machine_create(d:MachineIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager","Maintenance Engineer"))):
    if not db.get(ProductionLine,d.line_id):raise HTTPException(404,"Line not found")
    x=Machine(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","Machine",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/machines",tags=["Machines"])
def machines(status:str|None=None,line_id:int|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(Machine).filter(Machine.is_deleted==False)
    if status:q=q.filter(Machine.status==status)
    if line_id:q=q.filter(Machine.line_id==line_id)
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.patch("/api/v1/machines/{mid}/status",tags=["Machines"])
def machine_status(mid:int,status:str,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Maintenance Engineer","Production Manager"))):
    transitions={"Idle":{"Running","Maintenance","Decommissioned"},"Running":{"Idle","Maintenance","Breakdown"},"Maintenance":{"Idle","Running","Breakdown"},"Breakdown":{"Maintenance"},"Decommissioned":set()}
    x=db.get(Machine,mid)
    if not x:raise HTTPException(404,"Machine not found")
    if status not in transitions.get(x.status,set()):raise HTTPException(400,f"Invalid transition {x.status} -> {status}")
    old=x.status;x.status=status;audit(db,u,"STATUS_CHANGE","Machine",mid,old,status)
    if status=="Breakdown":db.add(Notification(category="Machine Breakdown",message=f"Machine {x.code} breakdown",entity="Machine",entity_id=str(mid)))
    db.commit();return {"id":mid,"status":status}
@app.post("/api/v1/production-orders",tags=["Production Orders"])
def order_create(d:OrderIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager"))):
    if not db.get(Product,d.product_id) or not db.get(ProductionLine,d.line_id):raise HTTPException(404,"Product/line not found")
    x=ProductionOrder(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","ProductionOrder",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/production-orders",tags=["Production Orders"])
def orders(status:str|None=None,product_id:int|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(ProductionOrder).filter(ProductionOrder.is_deleted==False)
    if status:q=q.filter(ProductionOrder.status==status)
    if product_id:q=q.filter(ProductionOrder.product_id==product_id)
    return {"items":q.offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.post("/api/v1/production-orders/{oid}/transition",tags=["Production Orders"])
def order_transition(oid:int,new_status:str,db:Session=Depends(get_db),u=Depends(current_user)):
    x=db.get(ProductionOrder,oid)
    if not x:raise HTTPException(404,"Order not found")
    transitions={"Draft":{"Scheduled","Cancelled"},"Scheduled":{"In Progress","Cancelled"},"In Progress":{"Paused","Completed"},"Paused":{"In Progress","Cancelled"},"Completed":set(),"Cancelled":set()}
    if new_status not in transitions.get(x.status,set()):raise HTTPException(400,f"Invalid transition {x.status} -> {new_status}")
    if new_status=="Scheduled" and u.role not in {"Super Admin","Production Manager"}:raise HTTPException(403,"Production Manager required")
    if new_status=="In Progress":
        bom=db.query(BOMItem).filter_by(product_id=x.product_id,is_active=True).all()
        if not bom:raise HTTPException(400,"Active BOM required")
        shortage=[]
        for b in bom:
            m=db.get(Material,b.material_id);need=b.quantity_per_product*x.quantity
            if m.available_quantity<need:shortage.append({"material":m.name,"required":need,"available":m.available_quantity})
        if shortage:raise HTTPException(409,detail={"message":"Insufficient inventory","shortages":shortage})
        x.supervisor_reviewed=True
    if new_status=="Completed" and not x.manager_approved:raise HTTPException(400,"Manager approval required")
    old=x.status;x.status=new_status;audit(db,u,"STATUS_TRANSITION","ProductionOrder",oid,old,new_status);db.commit();return {"id":oid,"status":new_status}
@app.post("/api/v1/production-orders/{oid}/approve",tags=["Production Orders"])
def approve_order(oid:int,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager","Production Manager"))):
    x=db.get(ProductionOrder,oid)
    if not x:raise HTTPException(404,"Order not found")
    if x.status not in {"In Progress","Paused"}:raise HTTPException(400,"Order must be in progress/paused before approval")
    x.manager_approved=True;audit(db,u,"APPROVE","ProductionOrder",oid);db.commit();return {"id":oid,"manager_approved":True}
@app.post("/api/v1/batches",tags=["Batches"])
def batch_create(d:BatchIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager","Production Supervisor"))):
    o=db.get(ProductionOrder,d.order_id)
    if not o or o.status not in {"Scheduled","In Progress"}:raise HTTPException(400,"Batch requires scheduled/in-progress order")
    if d.planned_quantity>o.quantity:raise HTTPException(400,"Batch exceeds order quantity")
    if d.machine_id:
        m=db.get(Machine,d.machine_id)
        if not m or m.line_id!=d.line_id or m.status in {"Breakdown","Maintenance","Decommissioned"}:raise HTTPException(409,"Machine unavailable or not on line")
    x=ProductionBatch(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","ProductionBatch",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.post("/api/v1/batches/{bid}/start",tags=["Batches"])
def batch_start(bid:int,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager","Production Supervisor"))):
    x=db.get(ProductionBatch,bid)
    if not x:raise HTTPException(404,"Batch not found")
    if x.started_at:raise HTTPException(400,"Batch already started")
    if x.machine_id:
        m=db.get(Machine,x.machine_id)
        if m.status!="Idle":raise HTTPException(409,"Machine must be idle")
        m.status="Running"
    x.started_at=datetime.utcnow();audit(db,u,"START","ProductionBatch",bid);db.commit();return {"id":bid,"started_at":x.started_at}
@app.post("/api/v1/batches/{bid}/output",tags=["Batches"])
def batch_output(bid:int,d:OutputIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager","Production Supervisor"))):
    x=db.get(ProductionBatch,bid)
    if not x or not x.started_at or x.ended_at:raise HTTPException(400,"Batch must be started and not completed")
    if x.produced_quantity+d.produced_quantity>x.planned_quantity:raise HTTPException(400,"Output exceeds planned quantity")
    x.produced_quantity+=d.produced_quantity;x.rejected_quantity+=d.rejected_quantity
    audit(db,u,"OUTPUT","ProductionBatch",bid,new=d.model_dump());db.commit()
    return {"batch_id":bid,"produced_quantity":x.produced_quantity,"rejected_quantity":x.rejected_quantity,"completion_percent":round(x.produced_quantity/x.planned_quantity*100,2),"rejection_percent":round(x.rejected_quantity/x.produced_quantity*100,2) if x.produced_quantity else 0}
@app.post("/api/v1/batches/{bid}/complete",tags=["Batches"])
def batch_complete(bid:int,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Production Manager","Production Supervisor"))):
    x=db.get(ProductionBatch,bid)
    if not x or not x.started_at:raise HTTPException(400,"Started batch required")
    if x.produced_quantity<x.planned_quantity:raise HTTPException(400,"Planned quantity not reached")
    if db.query(QualityInspection).filter_by(batch_id=bid,result="Fail").count():raise HTTPException(400,"Resolve failed inspections first")
    x.ended_at=datetime.utcnow()
    if x.machine_id:db.get(Machine,x.machine_id).status="Idle"
    audit(db,u,"COMPLETE","ProductionBatch",bid);db.commit();return {"message":"Batch completed","id":bid}
@app.post("/api/v1/quality/inspections",tags=["Quality"])
def inspection_create(d:InspectionIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Quality Manager"))):
    if d.result not in {"Pass","Fail"}:raise HTTPException(422,"Result must be Pass or Fail")
    if not db.get(ProductionBatch,d.batch_id):raise HTTPException(404,"Batch not found")
    x=QualityInspection(batch_id=d.batch_id,inspection_type=d.inspection_type,inspector_id=u.id,parameter=d.parameter,expected_value=d.expected_value,actual_value=d.actual_value,result=d.result,remarks=d.remarks)
    db.add(x);db.flush();audit(db,u,"CREATE","QualityInspection",x.id,new=d.model_dump())
    if d.result=="Fail":db.add(Notification(category="Quality Issue",message=f"Failed inspection {x.id}",entity="QualityInspection",entity_id=str(x.id)))
    db.commit();db.refresh(x);return x
@app.post("/api/v1/quality/defects",tags=["Quality"])
def defect_create(d:DefectIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Quality Manager"))):
    if d.severity not in {"Minor","Major","Critical"}:raise HTTPException(422,"Invalid severity")
    if not db.get(ProductionBatch,d.batch_id) or not db.get(Product,d.product_id):raise HTTPException(404,"Batch/product not found")
    x=Defect(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","Defect",x.id,new=d.model_dump())
    if d.severity=="Critical":db.add(Notification(category="Critical Defect",message=f"Critical defect {x.id}",entity="Defect",entity_id=str(x.id)))
    db.commit();db.refresh(x);return x
@app.post("/api/v1/inventory/movements",tags=["Inventory"])
def movement_create(d:MovementIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Store Manager"))):
    m=db.query(Material).filter_by(id=d.material_id).with_for_update().first()
    if not m:raise HTTPException(404,"Material not found")
    if d.movement_type not in {"StockIn","StockOut","Adjustment"}:raise HTTPException(422,"Invalid movement type")
    old=m.available_quantity
    if d.movement_type=="StockIn":m.available_quantity+=d.quantity
    elif d.movement_type=="StockOut":
        if m.available_quantity<d.quantity:raise HTTPException(409,"Negative inventory prohibited")
        m.available_quantity-=d.quantity
    else:m.available_quantity=d.quantity
    x=InventoryMovement(material_id=m.id,movement_type=d.movement_type,quantity=d.quantity,reference=d.reference,performed_by=u.id,notes=d.notes);db.add(x);db.flush();audit(db,u,"MATERIAL_MOVEMENT","Material",m.id,old,m.available_quantity)
    if m.available_quantity<=m.reorder_level:db.add(Notification(category="Low Stock",message=f"{m.name} at/below reorder level",entity="Material",entity_id=str(m.id)))
    db.commit();return {"material_id":m.id,"previous_quantity":old,"available_quantity":m.available_quantity,"movement_id":x.id}
@app.get("/api/v1/inventory/movements",tags=["Inventory"])
def movements(material_id:int|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(InventoryMovement)
    if material_id:q=q.filter_by(material_id=material_id)
    return {"items":q.order_by(InventoryMovement.created_at.desc()).offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.post("/api/v1/maintenance",tags=["Maintenance"])
def maintenance_create(d:MaintenanceIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Maintenance Engineer"))):
    if not db.get(Machine,d.machine_id):raise HTTPException(404,"Machine not found")
    x=MaintenanceRecord(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","MaintenanceRecord",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/maintenance/due",tags=["Maintenance"])
def maintenance_due(db:Session=Depends(get_db),u=Depends(current_user)):
    return db.query(MaintenanceRecord).filter(MaintenanceRecord.status=="Scheduled",MaintenanceRecord.scheduled_at<=datetime.utcnow()).all()
@app.post("/api/v1/downtime",tags=["Downtime"])
def downtime_create(d:DowntimeIn,db:Session=Depends(get_db),u=Depends(roles("Super Admin","Maintenance Engineer","Production Manager"))):
    if d.end_time and d.end_time<d.start_time:raise HTTPException(422,"End time before start time")
    x=DowntimeRecord(**d.model_dump());db.add(x);db.flush();audit(db,u,"CREATE","DowntimeRecord",x.id,new=d.model_dump());db.commit();db.refresh(x);return x
@app.get("/api/v1/dashboard",tags=["Reports"])
def dashboard(db:Session=Depends(get_db),u=Depends(current_user)):
    total=db.query(ProductionOrder).count();active=db.query(ProductionOrder).filter(ProductionOrder.status.in_(["Scheduled","In Progress","Paused"])).count();done=db.query(ProductionOrder).filter_by(status="Completed").count()
    made=db.query(func.coalesce(func.sum(ProductionBatch.produced_quantity),0)).scalar();reject=db.query(func.coalesce(func.sum(ProductionBatch.rejected_quantity),0)).scalar()
    inspections=db.query(QualityInspection).count();passed=db.query(QualityInspection).filter_by(result="Pass").count()
    return {"total_orders":total,"active_orders":active,"completed_orders":done,"total_produced":made,"total_rejected":reject,"rejection_rate_percent":round(reject/made*100,2) if made else 0,"quality_pass_percent":round(passed/inspections*100,2) if inspections else 0,"low_stock_materials":db.query(Material).filter(Material.available_quantity<=Material.reorder_level).count(),"machines_in_breakdown":db.query(Machine).filter_by(status="Breakdown").count(),"defects":db.query(Defect).count()}
@app.get("/api/v1/reports/production",tags=["Reports"])
def production_report(status:str|None=None,product_id:int|None=None,page:int=Query(1,ge=1),size:int=Query(20,ge=1,le=100),db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(ProductionOrder)
    if status:q=q.filter_by(status=status)
    if product_id:q=q.filter_by(product_id=product_id)
    return {"items":q.order_by(ProductionOrder.created_at.desc()).offset((page-1)*size).limit(size).all(),"total":q.count(),"page":page,"size":size}
@app.get("/api/v1/audit-logs",tags=["Audit"])
def audit_logs(entity:str|None=None,action:str|None=None,page:int=Query(1,ge=1),size:int=Query(50,ge=1,le=200),db:Session=Depends(get_db),u=Depends(roles("Super Admin","Plant Manager"))):
    q=db.query(AuditLog)
    if entity:q=q.filter_by(entity=entity)
    if action:q=q.filter_by(action=action)
    return {"items":q.order_by(AuditLog.timestamp.desc()).offset((page-1)*size).limit(size).all(),"total":q.count()}
@app.get("/api/v1/notifications",tags=["Notifications"])
def notifications(unread_only:bool=True,db:Session=Depends(get_db),u=Depends(current_user)):
    q=db.query(Notification)
    if unread_only:q=q.filter_by(is_read=False)
    return q.order_by(Notification.created_at.desc()).limit(100).all()
