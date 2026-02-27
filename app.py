from flask import Flask,render_template,redirect,url_for,request,session
app=Flask(__name__)
app.secret_key="secret"
users=[]

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        role = request.form['role']
        users.append({'username':username,'password':password,'role':role})
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form['username']
        password=request.form['password']
        for user in users:
            if user['username'] == username and user['password'] == password:
                session['username']=username 
                session['role']=user['role']
                if user['role']=='teacher':
                    return redirect(url_for('teacher_panel'))
                else:
                    return redirect(url_for('student_panel'))
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
