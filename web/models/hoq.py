from typing import List

from sqlalchemy import ForeignKeyConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base



class HoqATV(Base):
    __tablename__ = 'hoq_atv'

    atv_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    requirement: Mapped[str]
    note: Mapped[str] = mapped_column(default='')
    atv_order: Mapped[int]
    design_id: Mapped[int]

    ahp_values: Mapped[List['HoqAHP']] = relationship(foreign_keys='HoqAHP.precedent_atv_id')
    hoq_values: Mapped[List['HoqHOQ']] = relationship(foreign_keys='HoqHOQ.atv_id')

    __table_args__ = (
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
    )


class HoqAHP(Base):
    __tablename__ = 'hoq_ahp'

    precedent_atv_id: Mapped[int] = mapped_column(ForeignKey('hoq_atv.atv_id', ondelete='CASCADE'), primary_key=True)
    consequent_atv_id: Mapped[int] = mapped_column(ForeignKey('hoq_atv.atv_id', ondelete='CASCADE'), primary_key=True)
    value: Mapped[str]

    consequent: Mapped[HoqATV] = relationship(foreign_keys=[consequent_atv_id])


class HoqECHC(Base):
    __tablename__ = 'hoq_echc'

    echc_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    direction: Mapped[int]
    characteristic: Mapped[str]
    note: Mapped[str] = mapped_column(default='')
    market_value: Mapped[str] = mapped_column(default='')
    target_value: Mapped[str] = mapped_column(default='')

    echc_order: Mapped[int]
    design_id: Mapped[int]

    __table_args__ = (
        ForeignKeyConstraint(['design_id'], ['designs.design_id']),
    )


class HoqHOQ(Base):
    __tablename__ = 'hoq_hoq'

    atv_id: Mapped[int] = mapped_column(ForeignKey('hoq_atv.atv_id', ondelete='CASCADE'), primary_key=True)
    echc_id: Mapped[int] = mapped_column(ForeignKey('hoq_echc.echc_id', ondelete='CASCADE'), primary_key=True)
    value: Mapped[int]

    echc: Mapped[HoqECHC] = relationship(foreign_keys=[echc_id])
