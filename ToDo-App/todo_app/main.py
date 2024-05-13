from fastapi import FastAPI, Depends, HTTPException, Query
from sqlmodel import SQLModel, Field, create_engine, Session, select, Relationship
from todo_app import setting
from typing import Annotated, Optional
from contextlib import asynccontextmanager


# Step-1: Create Database on Neon
# Step-2: Create .env file for environment variables
# Step-3: Create setting.py file for encrypting DatabaseURL
# Step-4: Create a Model
# Step-5: Create Engine
# Step-6: Create function for table creation
# Step-7: Create function for session management
# Step-8: Create context manager for app lifespan
# Step-9: Create all endpoints of todo app


app =FastAPI()
class Todo(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    content: str = Field(index=True, min_length=3, max_length=54)
    is_completed: bool = Field(default=False)
    user_id: Optional[int] = Field(default=None, foreign_key="user.id")
    user: Optional['User'] = Relationship(back_populates="todos")


class User(SQLModel, table=True):
    id: int = Field(primary_key=True)
    email: str = Field(index=True)
    password: str = Field()
    todos: Optional[list[Todo]] = Relationship(back_populates="user")


#  Create engine
# engine is one for the whole connection
connection_string: str = str(setting.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg")
engine = create_engine(connection_string, connect_args={
                       "sslmode": "require"}, pool_recycle=300, pool_size=10, echo=True)


# Create table
def create_tables():
    SQLModel.metadata.create_all(engine)


# # instance create ---> data from user to create task
# # Session: for each application /functionality
# session = Session(engine)
# # create todos in database
# session.add(todo1)
# session.add(todo2)
# print(f"Before commit",{"todo1":todo1})
# session.commit()

# print(f"After commit", {"todo1":todo1}
# session.close()

# make dependency and then inject
def get_session():
    with Session(engine) as session:
        yield session


@asynccontextmanager
async def lifespan(app: FastAPI):
    print('Creating Tables')
    #create_tables()
    print("Tables Created")
    yield


app: FastAPI = FastAPI(
    lifespan=lifespan, title="dailyDo Todo App", version='1.0.0')


@app.get('/')
async def root():
    return {"message": "Welcome to dailyDo todo app"}


@app.get('/login/')
async def login(email: str , password: str, session: Session = Depends(get_session)):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Missing email or password")
    user = session.exec(select(User).where(User.email == email)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.password != password:
        raise HTTPException(status_code=401, detail="Incorrect password")
    return {"message": "Login successful", "user":user}


@app.post('/signup/')
async def signup(email: str, password: str, session: Session = Depends(get_session)):
    if not email or not password:
        raise HTTPException(status_code=400, detail="Missing email or password")
    existing_user = session.exec(select(User).where(User.email == email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = User(email=email, password=password)
    session.add(new_user)
    session.commit()
    return {"message": "Signup successful"}

@app.post('/todos/', response_model=Todo)
async def create_todo(todo: Todo, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.id == todo.user_id)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    todo.user_id = user.id
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo

@app.get('/todos/', response_model=list[Todo])
async def get_all(session: Annotated[Session, Depends(get_session)]):
    todos = session.exec(select(Todo)).all()
    if todos:
        return todos
    else:
        raise HTTPException(status_code=404, detail="No Task found")


@app.get('/todos/{id}', response_model=Todo)
async def get_single_todo(id: int, session: Annotated[Session, Depends(get_session)]):
    todo = session.exec(select(Todo).where(Todo.id == id)).first()
    if todo:
        return todo
    else:
        raise HTTPException(status_code=404, detail="No Task found")


@app.put('/todos/{id}')
async def edit_todo(id: int, todo: Todo, session: Annotated[Session, Depends(get_session)]):
    existing_todo = session.exec(select(Todo).where(Todo.id == id)).first()
    if existing_todo:
        existing_todo.content = todo.content
        existing_todo.is_completed = todo.is_completed
        session.add(existing_todo)
        session.commit()
        session.refresh(existing_todo)
        return existing_todo
    else:
        raise HTTPException(status_code=404, detail="No task found")


@app.delete('/todos/{id}')
async def delete_todo(id: int, session: Annotated[Session, Depends(get_session)]):
    todo = session.exec(select(Todo).where(Todo.id == id)).first()
    
    if todo:
        session.delete(todo)
        session.commit()
        # session.refresh(todo)
        return {"message": "Task successfully deleted"}
    else:
        raise HTTPException(status_code=404, detail="No task found")
