# package importing
from flask import Flask, make_response, request, render_template, url_for, redirect
import io
from io import StringIO
import csv
from flask_sqlalchemy import SQLAlchemy
import numpy as np
import pickle
from werkzeug.utils import secure_filename
import json
import os
from datetime import datetime
from os.path import join, dirname, realpath

import pandas as pd
import mysql.connector

# for Individual-Prediction:-
app = Flask(__name__)
model = pickle.load(open('model.pkl', 'rb'))

# # Upload folder
UPLOAD_FOLDER = 'static/files'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Database connection
mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="heart"
)

mycursor = mydb.cursor()

mycursor.execute("SHOW DATABASES")

# View All Database
for x in mycursor:
    print(x)

def transform(text_file_contents):
    return text_file_contents.replace("=", ",")

# individual page
@app.route('/Individual-Test')
def Individual_Test():
    return render_template('Individual-Test.html', params=params)

# for individual Dataset
@app.route('/predict', methods=['POST', 'GET'])
def predict():
    int_features = [float(x) for x in request.form.values()]
    final_features = [np.array(int_features)]
    prediction = model.predict(final_features)
    output = prediction[0]
    if output == 1:
        return render_template('Individual-Test.html', params=params,
                               prediction_text="Prediction result:-  Sorry to say that you may have heart disease in upcoming 10 years. Do consult your family doctor and take a proper treatment.")
    else:
        return render_template('Individual-Test.html', params=params,
                               prediction_text="Prediction result:- Congratulations, you don't have any chances of heart disease in upcoming 10 years and continue your diet and have a good health.")


with open('config.json', 'r') as c:
    params = json.load(c)["params"]

# local sever connecting
local_server = True

app.config['UPLOAD_FOLDER'] = params['upload_location']
if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)

# for contact feedback
class Contact(db.Model):
    srno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    phone_no = db.Column(db.String(12), nullable=False)
    message = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(12), nullable=True)

# home page
@app.route("/")
def home():
    return render_template("index.html", params=params)

# about us page
@app.route("/about")
def about():
    return render_template("about.html", params=params)

# dataset page
@app.route("/Dataset_test")
def Dataset_test():
    return render_template("Dataset_test.html", params=params)

# home page
@app.route("/index.html")
def index():
    return render_template("index.html", params=params)


# for loading dataset in sql

def parseCSV(filePath, mycursor):
    # CVS Column Names
    col_names = ['male', 'age', 'cigsPerDay', 'BPMeds', 'prevalentStroke', 'prevalentHyp', 'diabetes', 'totChol',
                 'sysBP', 'diaBP', 'BMI', 'heartRate', 'glucose']
    # Use Pandas to parse the CSV file
    csvData = pd.read_csv(filePath, names=col_names, header=None)
    # Loop through the Rows
    for i, row in csvData.iterrows():
        sql = "INSERT INTO bulk (male, age, cigsPerDay, BPMeds, prevalentStroke, prevalentHyp, diabetes, totChol, sysBP, diaBP, BMI, heartRate, glucose) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        value = (row['male'], row['age'], row['cigsPerDay'], row['BPMeds'], row['prevalentStroke'], row['prevalentHyp'],
                 row['diabetes'], row['totChol'], row['sysBP'], row['diaBP'], row['BMI'], row['heartRate'], row['glucose'])
        mycursor.execute(sql, value)
        mydb.commit()


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if request.method == 'POST':
        f = request.files['file']
        f.save(os.path.join(
            app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
        parseCSV(os.path.join(
            app.config['UPLOAD_FOLDER'], f.filename), mycursor)
        return render_template('upload.html', params=params)

# for taking contact feedback in sql
@app.route("/contact", methods=['GET', 'POST'])
def contact():
        if request.method == 'POST':
            '''Add entry to the database'''
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            message = request.form.get('message')
            entry = Contact(name=name, phone_no=phone, message=message, date=datetime.now(), email=email)
            db.session.add(entry)
            db.session.commit()
        return render_template('contact.html', params=params)


# for predicting bulk dataset

@app.route('/transform', methods=["POST"])
def transform_view():
    f = request.files['data_file']
    if not f:
        return "No file"

    stream = io.StringIO(f.stream.read().decode("UTF8"), newline=None)
    csv_input = csv.reader(stream)
    print(csv_input)
    for row in csv_input:
        print(row)

    stream.seek(0)
    result = transform(stream.read())

    df = pd.read_csv(StringIO(result))

    # load the model from disk
    loaded_model = pickle.load(open('model.pkl', 'rb'))
    df['TenYearCHD'] = loaded_model.predict(df)

    response = make_response(df.to_csv())
    response.headers["Content-Disposition"] = "attachment; filename=result.csv"
    return response

# upload page
@app.route('/upload')
def upload():
    return render_template('upload.html', params=params)



if __name__ == '__main__':
    app.run(debug=True)
