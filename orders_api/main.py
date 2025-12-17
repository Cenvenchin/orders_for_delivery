from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from pydantic import BaseModel
from datetime import datetime

DATABASE_URL = "postgresql://admin:admin@db:5432/orders"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class OrderDB(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    customer = Column(String)
    product = Column(String)
    quantity = Column(Integer, default=1)
    price = Column(Float)
    status = Column(String, default="новый")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


Base.metadata.create_all(bind=engine)


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


app = FastAPI(title="Orders API", version="1.0")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def root():
    return {"api": "orders", "version": "1.0"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/orders/", response_model=OrderResponse)
def create_order(order: OrderCreate):
    try:
        db = SessionLocal()
        db_order = OrderDB(
            customer=order.customer,
            product=order.product,
            quantity=order.quantity,
            price=order.price
        )
        db.add(db_order)
        db.commit()
        db.refresh(db_order)
        db.close()
        return db_order
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/", response_model=list[OrderResponse])
def get_orders():
    try:
        db = SessionLocal()
        orders = db.query(OrderDB).order_by(OrderDB.created_at.desc()).all()
        db.close()
        return orders
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/orders/{order_id}/status")
def update_status(order_id: int, status: str):
    try:
        db = SessionLocal()
        order = db.query(OrderDB).filter(OrderDB.id == order_id).first()
        if not order:
            db.close()
            raise HTTPException(status_code=404, detail="Нет заказа")
        order.status = status
        db.commit()
        db.close()
        return {"message": f"Статус {order_id} изменен на {status}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)