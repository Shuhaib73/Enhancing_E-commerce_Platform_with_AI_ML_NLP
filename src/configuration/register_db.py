from flask import Flask, render_template, redirect, url_for, json, request, jsonify, flash, session
from datetime import datetime
from passlib.hash import pbkdf2_sha256 
import uuid

from src.configuration.mongo_db_connection import db


class User:

    def start_session(self, user):
        session['logged_in'] = True 
        session['user_name'] = user['name']
        session['user_email'] = user['email']
        session['user_id'] = user['_id']

        return redirect(url_for('logged_home'))

    
    def signup(self):

        if request.method == 'POST':
            try:
                # Get data from the form
                name = request.form.get('name')
                email = request.form.get('email')
                password = request.form.get('password')

                # Check for existing email address 
                if db.users.find_one({ 'email': email }):
                    flash("This email address is already registered. Please use a different one.", "error")
                    return redirect(url_for('register'))


                # Validate input
                if len(password) <= 3:
                    flash('Password must be at least 4 characters long', 'error')
                    return redirect(url_for('register'))
                
                # Hash the password
                password_hash = pbkdf2_sha256.encrypt(password)

                # Create the new user if email doesn't exist
                user = {
                    "_id": uuid.uuid4().hex,  
                    "name": name,
                    "email": email,
                    "password": password_hash,
                    "details": datetime.now()
                }

                # Insert the new user into the database
                db.users.insert_one(user)

                # flash("Registration Successful!", "success")
        
                return self.start_session(user)
            
            except Exception as e:
                flash(f'An unexpected error occurred - details : {str(e)}', 'error')
                return redirect(url_for('register'))

        # Render login/signup page for GET request
        return render_template('login.html')
    

    def signout(self):
        session.clear()
        return redirect(url_for('register'))


    def login(self):

        if request.method == 'POST':
            try:
                email = request.form.get('email')
                password = request.form.get('password')

                if email and password:
                    # Find the user by email in the database
                    ex_user = db.users.find_one({ 'email': email})

                    if ex_user:
                        # Verify the password
                        if pbkdf2_sha256.verify(password, ex_user['password']):
                            # flash("You have successfully logged in. Welcome back!", "success")
                            # return redirect(url_for('logged_home'))
                            return self.start_session(ex_user)
                        else:
                            flash("Incorrect password. Please try again.", "error")
                    else:
                        flash("We couldn't find an account associated with that email. Please check the email address or register for a new account.", "error")
                        return redirect('register')

            except Exception as e:
                flash(f'An unexpected error occurred: {str(e)}', 'error') 

        return render_template('login.html') 
    
