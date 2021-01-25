from sqlalchemy.orm import sessionmaker ,relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy import create_engine , func
from sqlalchemy import (Column , Integer,BigInteger ,
		Numeric ,String , ForeignKey,UniqueConstraint,
		CheckConstraint , LargeBinary , DateTime , Text , Float ,Boolean )
import datetime, os 
from dotenv import load_dotenv

load_dotenv("./.env")

username = os.getenv("db_username")
password = os.getenv("db_password")
database = os.getenv("db_database")
host =os.getenv("db_host")

ModelBase = declarative_base( )
engine = create_engine(f'postgresql+psycopg2://{username}:{password}@{host}/{database}')
session_maker = sessionmaker ( bind= engine )

''''''

class User( ModelBase ) :
    __tablename__ = "users"

    id = Column( BigInteger , primary_key = True, autoincrement=True )
    first_name = Column( String , nullable = False )
    last_name= Column( String , nullable = False )
    user_name= Column( String , nullable = False )
    user_pwd=Column( String , nullable = False )
    is_active=Column(Boolean, nullable=False )
    created_time=Column( DateTime , nullable= False )
    user_datas = relationship( "UserData",backref="user"  )

class UserData( ModelBase ) :
    __tablename__ = "user_data"

    id = Column( BigInteger , primary_key = True, autoincrement=True )
    data_file_name = Column( String , nullable = False )
    total_count = Column ( Integer , nullable=True , default=100 )
    success_count = Column(Integer, nullable=True, default=80)
    fail_count = Column(Integer, nullable=True, default=20)
    user_id = Column ( BigInteger , ForeignKey("users.id"), nullable=False )
    created_time = Column(DateTime, default=datetime.datetime.utcnow )
    user_data_details = relationship( "UserDataDetails" , backref="user_data" )

class UserDataDetails( ModelBase ) :
    __tablename__ = "user_data_details"

    id = Column( BigInteger , primary_key = True, autoincrement=True  )
    data_year = Column ( Integer , default=lambda :datetime.datetime.utcnow().year )
    industry_aggregation_nzsioc = Column( String , nullable = False )
    industry_code_nzsioc = Column( String , nullable = False )
    industry_name_nzsioc = Column( String , nullable = False )
    units = Column( String , nullable = False )
    variable_code = Column( String , nullable = False )
    variable_name = Column( String , nullable = False )
    variable_category = Column( String , nullable = False )
    data_value = Column(Integer, nullable=True )
    industry_code_anzsic06 = Column( String , nullable = False )
    user_data_id = Column ( BigInteger , ForeignKey ( "user_data.id" ), nullable=False )
    created_time = Column(DateTime, default=datetime.datetime.utcnow )

    def dict(self ):
        _ =  self.__dict__
        _.pop("_sa_instance_state")
        _[ "created_time"] = _[ "created_time"].__str__( )
        return _

def getSession( ) :
    return session_maker( )

if __name__ == "__main__" :
    ModelBase.metadata.create_all ( bind= engine )