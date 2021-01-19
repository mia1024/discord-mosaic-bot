from mosaic_bot import BASE_PATH
from mosaic_bot.image import hash_image, diff_hash
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, JSON, create_engine, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.types import TypeDecorator
from ctypes import c_int64, c_uint64
import datetime
import PIL.Image

Base = declarative_base()

engine = create_engine('sqlite:///' + str(BASE_PATH / 'db.sqlite3'))
Session = sessionmaker(engine)


class ImageExists(Exception): pass


class ImageHash(TypeDecorator):
    # SQLite int is signed 64bits but the hash is unsigned 64 bits
    # so this conversion is necessary so SQLite stops complaining
    
    impl = Integer
    
    def process_bind_param(self, value, dialect):
        return c_int64(value).value
    
    def process_result_value(self, value, dialect):
        return c_uint64(value).value


class Image(Base):
    __tablename__ = 'images'
    
    name = Column(String, nullable=False, unique=True)
    hash = Column(ImageHash, primary_key=True)
    uploaded_by = Column(Integer)
    time_uploaded = Column(DateTime, default=datetime.datetime.utcnow)


class ImageRequest(Base):
    __tablename__ = 'image_request'
    requesting_message_id = Column(Integer, primary_key=True)
    requested_by = Column(Integer, nullable=False)
    channel = Column(Integer, nullable=False)
    image_requested = Column(ForeignKey(Image.hash), nullable=False)
    time_requested = Column(DateTime, default=datetime.datetime.utcnow)
    response_messages = Column(JSON)


Image.metadata.create_all(engine)
ImageRequest.metadata.create_all(engine)


def add_image(img: PIL.Image.Image, name: str, min_allowed_diff: int = 5):
    session = Session()
    hash = hash_image(img)
    
    all_images = session.query(Image).all()
    for img in all_images:
        if (d := diff_hash(img.hash, hash)) <= min_allowed_diff:
            raise ImageExists(f'Hash of {name} is in conflict with {img.name}: {img.hash}. Diff is {d}.')
    session.add(Image(name=name, hash=hash))
    session.commit()
