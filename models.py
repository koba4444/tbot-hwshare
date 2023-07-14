from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

user_task_association_table = Table('user_task_association', Base.metadata,
                                    Column('user_id', Integer, ForeignKey('users.id')),
                                    Column('task_id', Integer, ForeignKey('tasks.id'))
                                    )

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    nickname = Column(String, nullable=False)
    internal_currency_balance = Column(Integer, nullable=False, default=0)
    tasks = relationship("Task", secondary=user_task_association_table, back_populates="users")

    def find_task(self, tags):
        return [task for task in self.tasks if set(tags).issubset(set(task.tags))]

    def load_task(self, task):
        self.internal_currency_balance -= 1
        task.likes += 1

    def buy_sh(self, sh):
        self.internal_currency_balance += sh

    def upload_task(self, task):
        self.tasks.append(task)
        if task.likes > 10 and task.dislikes < 5:
            self.internal_currency_balance += 5

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    school = Column(String)
    grade = Column(String)
    date = Column(String)
    tags = Column(String)
    image = Column(String)
    likes = Column(Integer, default=0)
    dislikes = Column(Integer, default=0)
    users = relationship("User", secondary=user_task_association_table, back_populates="tasks")

class Subject:
    def __init__(self, name, tags):
        self.name = name
        self.tags = tags

    def search_tasks(self, tasks):
        return [task for task in tasks if set(self.tags).issubset(set(task.tags))]
