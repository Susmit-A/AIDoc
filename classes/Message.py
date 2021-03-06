from .DBWrapper import DBWrapper
from datetime import datetime


class Message(DBWrapper):
    def __init__(self, username, user, content, time=None):
        super().__init__()
        if time is None:
            self.time = str(datetime.now())
        else:
            self.time = time
        self.content = content
        self.user = user
        self.username = username

    def upload(self):
        self.cursor.execute('''
            INSERT INTO MESSAGE(username, speaker, content, time) VALUES (%s, %s,%s,%s);
        ''', (self.username, self.user, self.content, self.time))

    @staticmethod
    def fetch(username):
        DBWrapper.cursor.execute('''
                SELECT * FROM MESSAGE where username=(%s);
            ''', (username,))
        messages = []
        records = DBWrapper.cursor.fetchall()
        if len(records) == 0:
            msg = Message(username, 'bot', "How may I help you?")
            msg.upload()
            messages.append(msg)
        for rec in records:
            messages.append(Message(rec[0], rec[1], rec[2]))
        return messages

    @staticmethod
    def create_table():
        DBWrapper.exec_query('''
           create table MESSAGE(
                username varchar(15),
                speaker varchar(4),
                content text,
                time varchar(30)
            );
        ''')

    @staticmethod
    def drop_table():
        DBWrapper.exec_query('''
            DROP TABLE MESSAGE;
        ''')
