import mysql.connector
import os
from mysql.connector import IntegrityError
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=os.environ.get('MYSQL_DATABASE_PASSWORD'),
        database="code_analyzer"
    )
from flask import Flask,render_template,redirect,url_for,request,session
app=Flask(__name__)
app.secret_key="secret"


@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        role = request.form['role']
        conn=None
        cur=None
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("insert into users(username,password,role) values(%s,%s,%s)",(username,password,role))
            conn.commit()
        except IntegrityError:
            return "Bu kullanıcı adı zaten kayıtlı"
        finally:
            cur.close()
            conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "select username,password,role from users where username=%s",
                (username,))
            user = cur.fetchone()
        finally:
            if cur is not None:
                cur.close()
            if conn is not None:
                conn.close()
        if user and user["password"] == password:
            session["username"] = user["username"]
            session["role"] = user["role"]
            if user["role"] == "teacher":
                return redirect(url_for("teacher_panel"))
            else:
                return redirect(url_for("student_panel"))
        return "Hatalı giriş!"
    return render_template("login.html")

@app.route('/teacher')
def teacher_panel():
    if session.get('role')!='teacher':
        return "Yetki yok"
    return "Öğretmen Paneli"

@app.route('/student')
def student_panel():
    if session.get('role') != 'student':
        return "Yetki yok"
    return "Öğrenci Paneli"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__=="__main__":
    app.run(debug=True)