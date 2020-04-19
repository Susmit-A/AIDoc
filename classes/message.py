from .DBWrapper import DBWrapper
from datetime import datetime


class Message(DBWrapper):
    def __init__(self, user, content):
        super().__init__()
        self.time = datetime.now()
        self.content = content
        self.user = user

    def upload(self):
        self.cursor.execute('''
            INSERT INTO MESSAGE(user, content, time) VALUES (%s,%s,%s);

        ''', (self.user, self.content, self.time))

    @staticmethod
    def create_table():
        DBWrapper.exec_query('''
           create table MESSAGE(
                user varchar(4),
                content text,
                time varchar(15)
            );
        ''')

    @staticmethod
    def drop_table():
        DBWrapper.exec_query('''
            DROP TABLE MESSAGE;
        ''')


