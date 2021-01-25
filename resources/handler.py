from flask import Flask, request
from flask_restful import Resource, Api
import sqlite3, bcrypt, os, datetime
from pathlib import Path
from functools import wraps
import jwt
from dotenv import load_dotenv
import pandas as pd
from pandas import ExcelFile
from io import StringIO

from .models import ( engine, getSession ,
        User, UserData, UserDataDetails )

load_dotenv("./.env")

app = Flask(__name__)
api = Api(app)


class DBConn:
    def __init__(self):
        self.sess = getSession()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sess.close()

def getFileName( add=1 ):
    files = os.listdir( "./media" )
    file_name = f"temp_{str( add+len(files))}.xlsx"
    return "./media/"+file_name if file_name not in files else getFileName(add= add+1 )

def authenticate(func) : 
    @wraps(func)
    def wrapper(self,  *args, **kwargs) :
        if "Authorization" in request.headers :
            jwt_token = request.headers.get("Authorization" ) .split("Bearer ")[1]
        else:
            return {"resp":"Token is missing;"}
        secret = os.getenv("SECRET_KEY")
        try:
            pay_load = jwt.decode(jwt_token, secret , algorithms=["HS256"])
        except :
            return {"resp":"Your token is invalid or expired;"}
        return func(self, user=pay_load.get("username"), *args, **kwargs)
    return wrapper


class Login ( Resource ) :
    def post(self, ):
        # data = .get_json(force=True)
        username = request.form.get("username")
        password = request.form.get("password")
        with  DBConn() as conn : 
            user = conn.sess.query(User.user_pwd ).filter( User.user_name == username ) .first()

            if user:
                (user_pwd,) = user
                if bcrypt.checkpw( password.encode("utf-8"), user_pwd.encode("utf-8") ) :
                    secret = os.getenv("SECRET_KEY")
                    encoded_jwt = jwt.encode({"username": username ,
                        "exp":datetime.datetime.utcnow()+ datetime.timedelta(days=1) }, secret, algorithm="HS256")
                    return {"resp":encoded_jwt }
                return {"resp":"Password Entered Wrong!!!"}
            return {"resp":"UnAuthorised User"}

class DataHandler(Resource) :
    # method_decorators = [authenticate]
    @authenticate
    def get(self , *args, **kwargs ) :
        username = kwargs.get("user")
        with DBConn( ) as conn :
            (user_id,) =  conn.sess.query ( User.id ).filter( User.user_name == username ).first()
            data = conn.sess.query(UserData.id, UserData.data_file_name ).filter ( UserData.user_id == user_id ).all()
            json_data = [ {"id":id_, "data_file_name":data_file_name }for id_,data_file_name in data ]
            return json_data

    @authenticate
    def post(self, *args,**kwargs ):
        username = kwargs.get("user")  # Username Should be Unique
        file_stream = request.files["data_file"]
        bytes_data =  file_stream.stream.read()
        file_name = getFileName()
        with open( file_name , "wb") as f :
            f.write( bytes_data )
        with DBConn( ) as conn :
            df = pd.read_excel(file_name, index_col = 0, engine = "openpyxl" ).rename(
                    columns=lambda x: x.lower() if x!= "Value" else "data_value" )
            os.remove( file_name )
            (user_id,) =  conn.sess.query ( User.id ).filter( User.user_name == username ).first()

            user_data = UserData ( )
            user_data.data_file_name = file_stream.filename
            user_data.user_id = user_id
            conn.sess.add( user_data )
            try:
                conn.sess.commit()
            except:
                return {"resp": "there is something problem in file uploading"}
            rtn = dataUpload(df=df, user_data_id=user_data.id)
            if rtn == True :
                return {"id": user_data.id, "data_file_name": user_data.data_file_name}
            else: return rtn

def dataUpload( df,user_data_id ) :
    columns = ['industry_aggregation_nzsioc', 'industry_code_nzsioc', 'industry_name_nzsioc',
         'units', 'variable_code', 'variable_name', 'variable_category', 'data_value',
         'industry_code_anzsic06']
    try :
        assert  columns == df.columns.tolist( )
    except :
        for column in columns:
            if column not in df.columns.tolist() :
                return {"resp": "Your data uploaded file has different columns with its table structure;Please check"}
    df_ = df [ df.data_value.apply(cleanString )]
    with DBConn() as conn :
        objects = [ UserDataDetails( user_data_id =user_data_id,**data_dict ) for data_dict  in  df_.to_dict(orient="records") ]
        conn.sess.bulk_save_objects( objects )
        try:
            conn.sess.commit()
        except :
            conn.sess.rollback()
            return {"resp": "There is something problem in saving records to user-data-details;"}
        return True

def isusercanview( func ) :
    @wraps( func )
    def wrapper(self , *args, **kwargs ) :
        print("this")
        username = kwargs.get("user")
        data_id = kwargs.get("data_id")
        with DBConn() as conn :
            (user_id_left,) = conn.sess.query ( UserData.user_id ).filter( UserData.id == data_id ).first()
            (user_id_right,) = conn.sess.query(User.id).filter(User.user_name == username).first()
            if user_id_left == user_id_right :
                return func ( self,*args, **kwargs )
            else :
                return {"resp" : "You are not authorised user to view the data" }
    return wrapper

class FetchDataDetails( Resource ) :

    @authenticate
    @isusercanview
    def get(self, data_id , *args, **kwargs  ):
        # data_id = kwargs.get("data_id")
        print(data_id, type(data_id))
        with DBConn() as conn :
            data_arr = conn.sess.query(UserDataDetails).filter(UserDataDetails.user_data_id == data_id).limit(5).all()
            return [ data.dict() for data in data_arr ]

def cleanString( x  ) :
    try :
        int(x)
        return True
    except:return False

api.add_resource(Login ,  "/api/dm/login" )
api.add_resource( DataHandler , "/api/dm/datafiles")
api.add_resource( FetchDataDetails , "/api/dm/datafiles/<int:data_id>" )

