from flask import Flask, render_template, request, redirect, url_for,session
from flask_session import Session
import credentials as c
from io import BytesIO
from PIL import Image
import ibm_db
import base64
from PIL import Image, ImageEnhance
import io

from flask import Flask, render_template, request, redirect, url_for, send_file
from werkzeug.utils import secure_filename
import os
# from pillow import load_image, dupe_image, get_default_slider, apply_enhancers, apply_hue_shift, get_dominant_colors
# from pillow import apply_blur, apply_sharpen, apply_edge_enhance, apply_smooth
# from pillow import get_image_size, rotate_image, resize_image, crop_image
# from cleanup import remove_static_files

app = Flask(__name__)
# app.config["SESSION_PERMANENT"] = False
# app.config["SESSION_TYPE"] = "filesystem"
# Session(app)
app.secret_key = 'something'

#connection of ibm db2
conn_string = "database="+c.db+";hostname="+c.hostname+";port="+c.port+";uid="+c.uid+";password ="+c.pwd+";security= SSL;sslcertificate = DigiCertGlobalRootCA.crt;"
conn = ibm_db.connect(conn_string,"","")
print("connection successful")


# Home page
@app.route('/')
def home():
    return render_template('index.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(username)
        
        sql = "select * from USERDEMO where username=? and password=?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt,1,username)
        ibm_db.bind_param(stmt,2,password)
        ibm_db.execute(stmt)    
        user = ibm_db.fetch_assoc(stmt)
        if user: 
            # session["username"] = username
            return redirect(url_for('dashboard',username=username))
        else:
            error = 'Invalid username or password'
            return render_template('login.html', error=error)
    else:
        return render_template('login.html')

# Registration page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        #check user in db        
        sql = "SELECT * FROM USERDEMO WHERE email = ? or username = ?"
        stmt = ibm_db.prepare(conn, sql)
        ibm_db.bind_param(stmt,1,email)
        ibm_db.bind_param(stmt,2,username)
        ibm_db.execute(stmt)
        stud = ibm_db.fetch_assoc(stmt)
        print(stud)
        if stud:
            msg = "student details exists . no need to create new user"
            return render_template('register.html', msg=msg)
        else:
            #push user into db
            sql = 'insert into USERDEMO values (?,?,?)'
            stmt = ibm_db.prepare(conn, sql)
            ibm_db.bind_param(stmt,1,username)
            ibm_db.bind_param(stmt,2,password)
            ibm_db.bind_param(stmt,3,email)
            ibm_db.execute(stmt)
            msg="Successfully registered.Please use same credentials to login"
            # return render_template('login.html',msg=msg)
            return redirect(url_for('login',msg=msg))
         
    else:
        return render_template('register.html')

# Dashboard page
@app.route("/dashboard/<username>",methods=['GET', 'POST'])
def dashboard(username):
    # if username and request.method=="POST":
    if username:
        sql = f"SELECT * FROM ALL_IMAGES WHERE username='{username}' "
        stmt = ibm_db.prepare(conn, sql)
        # ibm_db.bind_param(stmt,1,username)
        # ibm_db.bind_param(stmt,1,'dummy')
        ibm_db.execute(stmt) 
        my_images = []
        dictionary = ibm_db.fetch_assoc(stmt)
        while dictionary != False:
            dictionary['DATA'] = base64.b64encode(dictionary['DATA']).decode('utf-8')
            my_images.append(dictionary)
            dictionary = ibm_db.fetch_assoc(stmt)
        # print(my_images[0])
        return render_template("dashboard.html",my_images=my_images,username=username)
    else:
        return redirect("/login")

@app.route('/upload/<username>', methods=['GET', 'POST'])
# @login_required
def upload(username):
    # if request.method == 'POST':
    if True:
        file = request.files['file']
        image_data = file.read()
        image_name = file.filename
        # i_id = 56

        # Insert the image data into the database
        stmt = ibm_db.prepare(conn, "INSERT INTO ALL_IMAGES (name, data, username) VALUES (?, ?, ?)")
        ibm_db.bind_param(stmt, 1, image_name)
        ibm_db.bind_param(stmt, 2, image_data)
        ibm_db.bind_param(stmt, 3,username)
        ibm_db.execute(stmt)

        # ibm_db.close(conn)

        # return redirect(url_for('editor',id=i_id,username=username))
        # return render_template("dashboard.html",my_images=my_images,username=username)
        return redirect(url_for('dashboard',username=username))
    else:
        return render_template('dashboard.html',username=username)


@app.route('/editor/<int:id>/<username>', methods=['GET', 'POST'])
def editor(id,username):
    # image_data = get_image_data(1)
    sql = f"SELECT * FROM ALL_IMAGES WHERE id='{id}' "
    stmt = ibm_db.prepare(conn, sql)
    # ibm_db.bind_param(stmt,1,id)
    ibm_db.execute(stmt) 

    image_class = ibm_db.fetch_assoc(stmt)
    INPUT_FILENAME = image_class['NAME']
    image = image_class['DATA']
    image = Image.open(BytesIO(image))
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    im_raw = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return render_template('editing.html',username=username,im_curr=im_raw,im_orig=im_raw,id=id,b=0,c=0,h=0,s=0)

@app.route('/process/<int:id>/<username>', methods=['POST'])
def process(id,username):
    # Get slider values from the AJAX request
    print('GOT SLIDER VALS')
    b = int(request.form['brightness'])
    c = int(request.form['contrast'])
    s = int(request.form['saturation'])
    h = int(request.form['hue'])
    base64_str = request.form.get('image_orig')

    # Decode the Base64 string to bytes
    image_bytes = base64.b64decode(base64_str.split(',')[1])

    # Open the image from the bytes using PIL
    image = Image.open(BytesIO(image_bytes))

    im_orig = image
    buffered = BytesIO()
    im_orig.save(buffered, format="PNG")
    im_orig = base64.b64encode(buffered.getvalue()).decode('utf-8')
    print("Editing")
    # Apply image processing based on slider values
    enhancer = ImageEnhance.Brightness(image)
    image = enhancer.enhance(1.0+(b/100.0))
    
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(1.0+(c/100.0))
    
    enhancer = ImageEnhance.Color(image)
    image = enhancer.enhance(1.0+(s/100.0))
    
    converter = ImageEnhance.Color(image)
    image = converter.enhance(1.0+(h/100.0))
    
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    im_raw = base64.b64encode(buffered.getvalue()).decode('utf-8')
    # return send_file(img_io, mimetype='image/png')
    return render_template('editing.html',username=username,im_curr=im_raw,im_orig=im_orig,id=id,b=b,c=c,h=h,s=s)


@app.route('/save_img/<int:id>/<username>', methods=['GET', 'POST'])
# @login_required
def save_img(id,username):
    # if request.method == 'POST':
    if True:
        base64_str = request.form.get('image_orig')

    # Decode the Base64 string to byte
        img_data = base64.b64decode(base64_str.split(',')[1])
        # Insert the image data into the database
        stmt = ibm_db.prepare(conn, "UPDATE ALL_IMAGES SET data = ? WHERE id=?")
        ibm_db.bind_param(stmt, 1, img_data)
        ibm_db.bind_param(stmt, 2, id)
        ibm_db.execute(stmt)

        # ibm_db.close(conn)

        return redirect(url_for('dashboard',username=username))

@app.route('/logout', methods=['POST'])
def logout():
    return redirect(url_for('login'))





if __name__ == '__main__':
    app.run(debug=True)
