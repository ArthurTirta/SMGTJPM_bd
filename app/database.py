from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# jangan lupa diganti url nya jika deploy
URL_DATABASE= 'postgresql://postgres:postgres@localhost:5432/smgt'
engine = create_engine(URL_DATABASE)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()