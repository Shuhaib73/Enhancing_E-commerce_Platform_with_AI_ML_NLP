import os 
import re

from flask import Flask, render_template, redirect, url_for, json, request, jsonify, session, flash
from functools import wraps
from dotenv import load_dotenv

import pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from langchain_community.document_loaders import DataFrameLoader


from src.configuration.register_db import User
from src.configuration.products_db import Products


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):        # Check if 'logged_in' is in session and True
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def home():
    return render_template('base.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    user = User()
    return user.signup()


@app.route('/login', methods=['GET' ,'POST'])
def login():
    user = User()
    return user.login()


@app.route('/home', methods=['GET', 'POST'])
@login_required
def logged_home():
    return render_template('home.html')


@app.route('/men', methods=['GET', 'POST'])
def men_pg():
    # Get selected categories from the form if any
    selected_categories = request.args.getlist('category')

    # create an instance of the Products class 
    products_ins = Products()

    if selected_categories:
        men_products = products_ins.men_products_filter(filters={'category': selected_categories})
    else:
        # Otherwise, fetch the default products
        men_products = products_ins.top_50_men_products_default()

    # Render the template and pass the products data
    return render_template('men_pg.html', men_top50_products=men_products, logged_in=session.get('logged_in'))


@app.route('/women', methods=['GET', 'POST'])
def women_pg():
    # Get selected categories from the form if any
    selected_categories = request.args.getlist('category')

    # create an instance of the Products class 
    products_ins = Products()

    if selected_categories:
        women_products = products_ins.women_products_filter(filters={'category': selected_categories})
    else:
        # Otherwise, fetch the default products
        women_products = products_ins.top_50_women_products_default()

    # Render the template and pass the products data
    return render_template('women_pg.html', women_top50_products=women_products, logged_in=session.get('logged_in'))


@app.route('/personal_pg', methods=['GET', 'POST'])
def personal_pg():
    # Get selected categories from the form if any
    selected_categories = request.args.getlist('category')

    # create an instance of the Products class 
    products_ins = Products()

    if selected_categories:
        personal_products = products_ins.personal_products_filter(filters={'category': selected_categories})
    else:
        # Otherwise, fetch the default products
        personal_products = products_ins.top_50_Personal_products_default()

    # Render the template and pass the products data
    return render_template('Personal_Care.html', personal_top50_products=personal_products, logged_in=session.get('logged_in'))


@app.route('/accessories_pg', methods=['GET', 'POST'])
def accessories_pg():
    # Get selected categories from the form if any
    selected_categories = request.args.getlist('category')

    # create an instance of the Products class 
    products_ins = Products()

    if selected_categories:
        accessories_products = products_ins.accessories_products_filter(filters={'category': selected_categories})
    else:
        # Otherwise, fetch the default products
        accessories_products = products_ins.top_50_accessories_products_default()

    # Render the template and pass the products data
    return render_template('accessories.html', accessories_top50_products=accessories_products, logged_in=session.get('logged_in'))


@app.route('/footwear_pg', methods=['GET', 'POST'])
def footwear_pg():
    # Get selected categories from the form if any
    selected_categories = request.args.getlist('category')

    # create an instance of the Products class 
    products_ins = Products()

    if selected_categories:
        footwear_products = products_ins.footwear_products_filter(filters={'category': selected_categories})
    else:
        # Otherwise, fetch the default products
        footwear_products = products_ins.top_50_footwear_products_default()

    # Render the template and pass the products data
    return render_template('footwear.html', footwear_top50_products=footwear_products, logged_in=session.get('logged_in'))


@app.route('/cart', methods=['GET'])
@login_required
def cart():
    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in to view your cart.", "error")
        redirect(url_for('register'))

    products = Products()
    cart_items = products.get_cart(user_id)

    return render_template('cart.html', items=cart_items)


@app.route('/product/<product_id>', methods=['GET'])
def view_product(product_id):

    products_ins = Products()
    product = products_ins.view_product(product_id)

    # Fetch similar product
    product_name = product['productDisplayName']

    # Get content-based recommendations for the current product
    content_recommendations = products_ins.get_content_recommendations(product_name)

    # Get collaborative recommendations 
    # collaborative_recommendations = products_ins.get_collaborative_recommendations(product_name)

    if product:
        return render_template('view_product.html', product=product, logged_in=session.get('logged_in'), content_recommendations=content_recommendations)
    else:
        flash('Product not found.', 'error')
        redirect(request.referrer or url_for('men_pg'))


@app.route('/search_products', methods=['GET', 'POST'])
def search_products():

    if request.method == 'POST':
        # Retrieve the query from the form data
        query = request.form.get('query')

        # Perform the search using your custom hybrid search method
        products_ins = Products()
        searched_products = products_ins.get_search_product(query=query, index_name="product-index1", n=30)

        # Return results to the user (e.g., render a template with the search results)
        return render_template('search_results.html', searched_products=searched_products, logged_in=session.get('logged_in'))
    
    # If GET request or no query is provided, return a blank or initial page
    return render_template('search_results.html', products=[], logged_in=session.get('logged_in'))


@app.route('/redirect_based_on_category', methods=['GET'])
def redirect_based_on_category():
    category = request.args.get('category')  # Get selected category from form

    # Redirect based on the selected category
    if category == 'Men':
        return redirect(url_for('men_pg'))
    elif category == 'Women':
        return redirect(url_for('women_pg'))
    elif category == 'Personal':
        return redirect(url_for('personal_pg'))
    elif category == 'Accessories':
        return redirect(url_for('accessories_pg'))
    elif category == 'Footwear':
        return redirect(url_for('footwear_pg'))
  


@app.route('/add_item_cart/<product_id>', methods=['POST'])
def add_item_cart(product_id):
    print(f"Adding product to cart with ID: {product_id}")  # Debug print

    user_id = session.get('user_id')

    if not user_id:
        flash("Please log in to view your cart.", "error")
        return redirect(url_for('register'))
    
    products = Products()
    products.add_to_cart(user_id, product_id)

    return redirect(url_for('cart'))


@app.route('/update_item_cart/<product_id>', methods=['POST'])
def update_item_cart(product_id):
    user_id = session.get('user_id')
    quantity = int(request.form.get('quantity'))

    products = Products()
    updated = products.update_cart(user_id, int(product_id), quantity)

    if updated:
        flash("Cart updated successfully.", 'success')
    else:
        flash("Failed to update cart. Please try again.", 'error')

    return redirect(url_for('cart'))


@app.route('/remove_item_cart/<product_id>', methods=['POST'])
def remove_item_cart(product_id):
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in to update your cart.", "error")
        return redirect(url_for('register'))  # Redirect to login if no user session

    products = Products()
    products.remove_from_cart(user_id, int(product_id))

    return redirect(url_for('cart'))


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    return render_template('account.html')


@app.route('/logout')
def logout():
    user = User()
    return user.signout()






if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8080)