import datetime
from ctypes import c_int64, c_uint64
from functools import lru_cache
from typing import Optional

import PIL.Image
from sqlalchemy import Column, String, Integer, create_engine, DateTime, ForeignKey, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.types import TypeDecorator

from mosaic_bot import DATA_PATH
from mosaic_bot.hash import compute_image_path_from_hash, diff_hash
from mosaic_bot.hash import hash_image

Base = declarative_base()

engine = create_engine('sqlite:///' + str(DATA_PATH / 'db.sqlite3'), echo=False)
Session = sessionmaker(bind=engine)


class ImageExists(Exception): pass


class UInt64(TypeDecorator):
    # SQLite int is signed 64bits but the hash is unsigned 64 bits
    # so this conversion is necessary so SQLite stops complaining
    
    impl = Integer
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return c_int64(value).value
    
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return c_uint64(value).value


class Hash(TypeDecorator):
    impl = String
    
    def process_bind_param(self, value: Optional[int], dialect) -> Optional[str]:
        if value is not None:
            return str(value)
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[int]:
        if value is not None:
            return int(value)


class User(Base):
    __tablename__ = 'users'
    
    id = Column(UInt64, primary_key=True)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)


class Image(Base):
    __tablename__ = 'images'
    
    name = Column(String, nullable=False, unique=True)
    hash = Column(Hash, primary_key=True)
    uploaded_by = Column(UInt64)
    time_uploaded = Column(DateTime, default=datetime.datetime.utcnow)


class Request(Base):
    __tablename__ = 'requests'
    requesting_message = Column(UInt64, primary_key=True)
    requester = Column(UInt64, nullable=False)
    channel = Column(UInt64, nullable=False)
    image_requested = Column(ForeignKey(Image.hash))
    
    # yes time can be extracted from discord id but it's much easier this way
    time_requested = Column(DateTime, default=datetime.datetime.utcnow)
    
    def __repr__(self):
        return f'<Request {self.requesting_message} by {self.requester} for {self.image_requested}>'


class Response(Base):
    __tablename__ = 'responses'
    response = Column(UInt64, primary_key=True)
    requesting_message = Column(ForeignKey(Request.requesting_message), nullable=False)
    
    def __repr__(self):
        return f'<Response {self.response} for {self.requesting_message}>'


Image.metadata.create_all(engine)
Request.metadata.create_all(engine)
User.metadata.create_all(engine)
Response.metadata.create_all(engine)


def add_image(img: PIL.Image.Image, name: str, min_allowed_diff: int = 6) -> None:
    s = Session()
    hash = hash_image(img)
    
    all_images = s.query(Image).all()
    for img in all_images:
        if (d := diff_hash(img.hash, hash)) < min_allowed_diff:
            raise ImageExists(f'Hash of {name} is in conflict with {img.name}: {img.hash}. Diff is {d}.')
    s.add(Image(name=name, hash=hash))
    s.commit()


def response_deleted(request: int):
    s = Session()
    s.query(Response).filter(Response.requesting_message == request).delete()
    s.commit()


@lru_cache(100)
def get_image_path(hash: int) -> str:
    s = Session()
    
    # this will raise an exception if hash doesn't exist
    s.query(Image.hash).filter(Image.hash == hash).one()
    
    return compute_image_path_from_hash(hash)


@lru_cache(100)
def get_image_hash(name: str) -> int:
    session = Session()
    return session.query(Image.hash).filter(Image.name == name).one()[0]


def request_completed(by: int, hash: int, message_id: int, channel_id: int, response_messages: list[int]) -> None:
    session = Session()
    req = Request(requester=by,
                  image_requested=hash,
                  requesting_message=message_id,
                  channel=channel_id
                  )
    res = []
    for r in response_messages:
        res.append(Response(response=r, requesting_message=message_id))
    session.add(req)
    session.bulk_save_objects(res)
    session.commit()


def get_request(msg: int) -> Request:
    """
    given a message id, returns the associated request, if any
    
    :param msg: the message id
    :return: the request
    :raises: NoResultFound
    """
    s = Session()
    
    req = s.query(Response.requesting_message).filter(Response.response == msg)
    return s.query(Request).filter(or_(Request.requesting_message == req, Request.requesting_message == msg)).one()


def get_associated_messages(msg: int, is_request: bool):
    """
    given a message id, returns all the response message ids and
    the requesting message id. used to delete all associated messages.
    
    :param msg: the request or response message id
    :param is_request: whether msg can be a request id
    :return: the list of message ids. the first item is always the request
    """
    s = Session()
    if is_request:
        req = s.query(Response.requesting_message).filter(or_(Response.response == msg, Response.requesting_message == msg))
    else:
        req = s.query(Response.requesting_message).filter(Response.response == msg)
    res = s.query(Response.response).filter(Response.requesting_message == req)
    
    # because request message always comes first, its id is always smaller
    return list(map(lambda row: row[0], res.union(req).order_by(Response.response).all()))


__all__ = [
    'NoResultFound',
    'add_image',
    'get_associated_messages',
    'get_image_path',
    'get_image_hash',
    'get_request',
    'ImageExists'
]
