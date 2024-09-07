# 1. Мақсатым - қала беріледі. Сол қаланы базада бүгінгі күнмен іздеу қажет.
# 2. Бірінші сценарий бойынша егер ол қала және бүгінгі күн бойынша жауап бар болса базада ауа райды қайтару.
# 3. Екінші сценарий бойынша базада жоқ болса 'https://api.openweathermap.org/data/2.5/weather?q' - запрос жіберемін. Қайтқан жауаптап бүгінгі күн мен қаланы базаға жазамын.
# 4. GetList Қалалардың списогіне екі зат қосу керек. Біріншісі пагинация,
# 5. Екіншісі фильтрация , мысалға А-дан немесе а деген әріпі бар қалалрды шығару керек.
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional
import requests

app = FastAPI()

# Database орнату
DATABASE_URL = "sqlite:///./my_first_database.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Бұл базаның моделі. Бірінші модель құру керек
class City(Base):
    #Бұл бізде базадағы кестенің аты
    __tablename__ = "city"
    # Мынау кестенің бағандары, тапсырмаға сәйкес id, name_city, date_today, weather_city (может дұрыс емес)
    id = Column(Integer, primary_key=True, index=True)
    name_city = Column(String)
    date_today = Column(String)
    weather_city = Column(String)


# Кестені құрамыз
Base.metadata.create_all(bind=engine)


# Базамен жұмыс істеуге арналған сеанс. Сеанс деген не келесі сілтемеде жазылған: https://fastapi.tiangolo.com/tutorial/sql-databases/#alembic-note
# Создание зависимости
# Теперь используйте SessionLocal класс, который мы создали в sql_app/database.py файле, для создания зависимости.
#
# Нам нужно иметь независимый сеанс / соединение с базой данных (SessionLocal) для каждого запроса, использовать один и тот же сеанс на протяжении всего запроса, а затем закрывать его после завершения запроса.
#
# Затем для следующего запроса будет создан новый сеанс.
#
# Для этого мы создадим новую зависимость с помощью yield, как объяснялось ранее в разделе о зависимостях с помощью yield.
#
# Наша зависимость создаст новую SQLAlchemy SessionLocal, которая будет использоваться в одном запросе, а затем закроет ее, как только запрос будет завершен.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Мәліметтерді құрауға арналған Pydantic model
class CityCreate(BaseModel):
    name_city : str
    date_today : str
    weather_city : str


# Мәліметтерді сұрауға арналған Pydantic model
class CityResponse(BaseModel):
    id: int
    name_city: str
    date_today: str
    weather_city: str



# Элемент құруға арналған  endpoint
@app.post("/city/", response_model=CityResponse)
async def create_item(city: CityCreate, db: Session = Depends(get_db)):
    db_city = City(**city.dict())
    db_city.date_today = str(datetime.today())
    response = requests.get(
        'https://api.openweathermap.org/data/2.5/weather?q=' + db_city.name_city + '&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347')
    data = response.json()
    db_city.weather_city = str(data)
    db.add(db_city)
    db.commit()
    db.refresh(db_city)
    return db_city



# Элементті city_name бойынша оқуға арналған  endpoint
@app.get("/city/{city_name}", response_model=CityResponse)
async def read_item(city_name: str, db: Session = Depends(get_db)):
    db_city = db.query(City).filter(City.name_city == city_name).first()
    if db_city is None:
        db_city = City()
        db_city.name_city = str(city_name)
        db_city.date_today = str(datetime.today())
        response = requests.get(
            'https://api.openweathermap.org/data/2.5/weather?q=' + db_city.name_city + '&units=metric&lang=ru&appid=79d1ca96933b0328e1c7e3e7a26cb347')
        data = response.json()
        db_city.weather_city = str(data)
        db.add(db_city)
        db.commit()
        db.refresh(db_city)
    return db_city

# Элементтердің барлығын көруге арналған  endpoint
@app.get("/cities/")
def read_cities(db: Session = Depends(get_db)):
    cities = db.query(City).all()
    return cities

# Фильтрацияға арналған  endpoint
@app.get("/filter_city/{city_name}", response_model=List[CityResponse])
async def get_filter_city(city_name: str, db: Session = Depends(get_db)):
    db_city = db.query(City).filter(City.name_city.like(f"%{city_name}%")).all()
    return db_city

# Пагинацияға арналған  endpoint - дұрыс па дұрыс емес па
@app.get("/pagination_city/", response_model=List[CityResponse])
async def get_pagination_city(city_name: str = "", start: int = 0, end: int = 10, db: Session = Depends(get_db)):
    query = db.query(City).filter(City.name_city.like(f"%{city_name}%"))
    db_city = query.offset(start).limit(end).all()
    return db_city