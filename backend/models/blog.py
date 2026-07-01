from sqlalchemy import BigInteger, Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class BlogMaterial(Base):
    __tablename__ = "blog_materials"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    destination = Column(String(100), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    people_count = Column(Integer, nullable=True)

    itinerary_text = Column(Text, nullable=False)
    food_text = Column(Text, nullable=True)
    photo_text = Column(Text, nullable=True)
    expense_text = Column(Text, nullable=True)
    feeling_text = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    generations = relationship(
        "BlogGeneration",
        back_populates="material",
        cascade="all, delete-orphan",
    )


class BlogGeneration(Base):
    __tablename__ = "blog_generations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    material_id = Column(
        BigInteger,
        ForeignKey("blog_materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(String(64), nullable=False)

    content_type = Column(String(50), nullable=False)
    writing_style = Column(String(50), nullable=False)

    generated_title = Column(String(255), nullable=True)
    generated_content = Column(Text, nullable=False)
    tags = Column(Text, nullable=True)
    risk_note = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    material = relationship("BlogMaterial", back_populates="generations")