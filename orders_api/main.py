from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from pydantic import BaseModel
import time

DATABASE_URL = "postgresql://admin:admin@db:5432/orders"

def wait_for_db(url, retries=10, delay=2):
    for i in range(retries):
        try:
            engine = create_engine(url)
            conn = engine.connect()
            conn.close()
            print("✅ Database is ready")
            return engine
        except Exception as e:
            print(f"⏳ Waiting for database... ({i+1}/{retries})")
            time.sleep(delay)
    raise RuntimeError("❌ Database is not available")

engine = wait_for_db(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- МОДЕЛЬ БД ---
class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer = Column(String, nullable=False)
    product = Column(String, nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float)
    status = Column(String, default="новый")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

Base.metadata.create_all(bind=engine)

# --- Pydantic схемы ---
class OrderCreate(BaseModel):
    customer: str
    product: str
    quantity: int = 1
    price: float

class OrderResponse(BaseModel):
    id: int
    customer: str
    product: str
    quantity: int
    price: float
    status: str

    class Config:
        from_attributes = True

# --- FastAPI ---
app = FastAPI(title="Orders API", version="1.0")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"service": "orders-api", "status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/orders/", response_model=OrderResponse)
def create_order(order: OrderCreate):
    db = SessionLocal()
    try:
        db_order = OrderDB(**order.dict())
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        return db_order
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/orders/", response_model=list[OrderResponse])
def get_orders():
    db = SessionLocal()
    try:
        return db.query(OrderDB).order_by(OrderDB.created_at.desc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/orders/{order_id}/status")
def update_status(order_id: int, status: str):
    db = SessionLocal()
    try:
        order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="Заказ не найден")
        order.status = status
        db.commit()
        return {"message": f"Статус заказа {order_id} изменён на {status}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
