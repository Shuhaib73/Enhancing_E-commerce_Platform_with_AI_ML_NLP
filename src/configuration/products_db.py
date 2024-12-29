import os 
import random
from flask import render_template, redirect, url_for, jsonify, request, flash
import pymongo
import pandas as pd
import numpy as np 
from dotenv import load_dotenv

import pinecone
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore

from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from langchain_community.document_loaders import DataFrameLoader
from langchain.retrievers import EnsembleRetriever

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


from src.configuration.mongo_db_connection import product_db

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
pinecone_api_key = os.getenv("PINECONE_API_KEY")

pc = Pinecone(api_key=pinecone_api_key)
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")


class Products:

    def recommend_top_n_popular_products(self, gender, n=300):
        """
        Fetch the top 'n' popular products based on average ratings and number of ratings for a specific gender.
        Returns all columns from the product collection.
        """
        
        # Aggregate query to group by 'productDisplayName' and calculate mean and count of ratings
        pipeline = [
            {
                "$match": {
                    "gender": gender,  # Dynamic filter for gender
                    "ratings": {"$gt": 0},  # Exclude products with no ratings
                    "subCategory": {"$in": ["Topwear", "Bottomwear", "Headwear", "Belts", "Watches"]}
                }
            },
            {
                "$group": {
                    "_id": "$productDisplayName",  # Group by product name
                    "avg_ratings": {"$avg": "$ratings"},  # Calculate average rating
                    "total_rated": {"$sum": 1},  # Count the total number of ratings
                    "product_info": {"$first": "$$ROOT"}  # retain the entire product document
                }
            },
            {
                "$sort": {
                    "total_rated": -1,  # Sort by number of ratings in descending order
                    "avg_ratings": -1   # Sort by average rating in descending order
                }
            },
            {
                "$limit": n  # Limit the result to top 'n' products
            },
            {
                "$replaceRoot": {  # Replace the root with the product_info document
                    "newRoot": "$product_info"
                }
            }
        ]

        # we're using $replaceRoot to ensure that the document returned after the aggregation process contains the full product information (including all fields from the original product documents).
        
        # Execute the aggregation query
        top_products = list(product_db.products.aggregate(pipeline))

        # Shuffle the results to introduce randomness (optional)
        random.shuffle(top_products)

        return top_products

    def top_50_men_products_default(self):
        """
        Fetch the top 50 products for a specific gender based on default filter 
        and sort by ratings in descending order.
        """

        top_50_popular_products = self.recommend_top_n_popular_products('Men', 300)

        return top_50_popular_products[:50]

    def men_products_filter(self, filters):
        """
        Fetch the men's products based on the applied filters.
        """

        query = {"gender": "Men", "ratings": {"$gt": 3}}

        # Apply additional filters if provided
        if filters.get("category"):
            query["subCategory"] = {"$in": filters['category']}

        # fetch products from the db based on the query 
        filtered_products = product_db.products.find(query).sort("ratings", pymongo.DESCENDING).limit(200)

        # Convert the cursor to a list 
        filtered_products = list(filtered_products)

        # Shuffle the products
        random.shuffle(filtered_products)

        return filtered_products[:50]
    

    def view_product(self, product_id):
        """
        Fetch a single product based on product_id
        """
    
        product = product_db.products.find_one({"id": int(product_id)})

        return product
    
    def get_content_recommendations(self, product_name, n=14):
        """
        Get content-based recommendations for similar products.
        """

        product = product_db.products.find_one({"productDisplayName": product_name})

        # Check if the product name exists
        if not product:
            return redirect(url_for('home'))
           
        # Extract the features for filtering 
        gender = product.get('gender')
        sub_category = product.get('subCategory')
        usage = product.get('usage')

        query = {
            "gender": gender,
            "subCategory": sub_category,
            "usage": usage
        }

        # Fetch products from the db based on the query
        products_cursor = product_db.products.find(query).limit(3000)

        # Convert MongoDB cursor to a list and then to a DataFrame
        products_list = list(products_cursor)
        products_df = pd.DataFrame(products_list)

        # Initialize the TF-IDF Vectorizer with English stop words removal
        tfidf_vec = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf_vec.fit_transform(products_df['tag'].fillna(''))

        # Calculate the cosine similarity matrix between all the products based on their TF-IDF values
        cos_similarity = cosine_similarity(tfidf_matrix, tfidf_matrix)

        # Get the index of the product name provided by the user in the filtered DataFrame
        idx = products_df[products_df['productDisplayName'] == product_name].index[0]

        # Calculate cosine similarities between the target product and all others
        sim_score = cos_similarity[idx]

        # Sort the similarity scores and get the indices of the most similar products
        sorted_sim_indices = np.argsort(sim_score)[::-1]

        # Exclude the product itself (index 0 will be the product's self-similarity, so skip it)
        sorted_sim_indices = sorted_sim_indices[1:n]

        # Get the product details of the most similar products based on the indices
        recommended_products = products_df.iloc[sorted_sim_indices].to_dict(orient='records')
        
        return recommended_products
    
        
    def add_to_cart(self, user_id, product_id):

        # Fetch the product using the same product_id
        product = self.view_product(product_id)

        if product:

            # Add new product to cart
            cart_item = {
                'product_id': product['id'],
                'link': product['link'],
                'brand': product['brand'],
                'articleType': product['articleType'],
                'baseColour': product['baseColour'],
                'price': product['price'],
                'quantity': 1
            }

            # Upsert to add or update the cart
            product_db.carts.update_one(
                {"user_id": user_id},
                {"$push": {"items": cart_item}},
                upsert=True
            )

        #     flash(f"{product['productDisplayName']} added to cart.", 'success')
        # else:
        #     flash("Product not found.", 'error')

    def get_cart(self, user_id):

        cart = product_db.carts.find_one({"user_id": user_id})
        return cart['items'] if cart else []
    
    def update_cart(self, user_id, product_id, quantity):
        """
        Update the quantity of a specific product
        """
        try:
            # Find the user's cart first to check if the product exists
            cart = product_db.carts.find_one({"user_id": user_id})

            if cart and any(item['product_id'] == product_id for item in cart['items']):
                product_db.carts.update_one(
                    {"user_id": user_id, "items.product_id": product_id},
                    {"$set": {"items.$.quantity": quantity}}
                )
                return True
            else:
                print(f"Product {product_id} not found in cart.")
                return False
        except Exception as e:
            print(f"Error updating cart: {e}")
            return False

    def remove_from_cart(self, user_id, product_id):
        """
        Remove a specific product from the cart.
        """
        try:
            # Fetch the cart for the user
            cart = product_db.carts.find_one({"user_id": user_id})

            if cart:
                # Check if the product with the given product_id exists in the cart
                product_in_cart = any(item['product_id'] == product_id for item in cart['items'])

                if product_in_cart:
                    print(f"Product with ID {product_id} found in cart.")
                    
                    # Remove the product from the cart
                    result = product_db.carts.update_one(
                        {"user_id": user_id},
                        {"$pull": {"items": {"product_id": product_id}}}
                    )

                    # if result.modified_count > 0:
                    #     print(f"Product with ID {product_id} has been removed from the cart.")
                    #     return True
                    # else:
                    #     print(f"Failed to remove product with ID {product_id} from cart.")
                    #     return False
                # else:
                #     print(f"Product with ID {product_id} not found in cart.")
                #     return False
            else:
                print("Cart not found for the user.")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False


    def top_50_women_products_default(self):
        """
        Fetch the top 50 products for a specific gender based on default filter 
        and sort by ratings in descending order.
        """

        top_50_popular_products = self.recommend_top_n_popular_products('Women', 300)

        return top_50_popular_products[:50]    

    def women_products_filter(self, filters):
        """
        Fetch the men's products based on the applied filters.
        """

        query = {"gender": "Women", "ratings": {"$gt": 3}}

        # Apply additional filters if provided
        if filters.get("category"):
            query["subCategory"] = {"$in": filters['category']}

        # fetch products from the db based on the query 
        filtered_products = product_db.products.find(query).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list 
        filtered_products = list(filtered_products)

        # Shuffle the products
        random.shuffle(filtered_products)

        return filtered_products[:50]

    
    def top_50_Personal_products_default(self):
        """
        Fetch the top 50 Personal products based on default filter (ratings > 4)
        and sort by ratings in descending order.
        """

        top_300 = product_db.products.find(
            {"masterCategory": "Personal Care", "ratings": {"$gt": 4}}
        ).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list and return 
        top_300 = list(top_300)

        # Shuffle the data
        random.shuffle(top_300)

        return top_300[:50]
    
    def personal_products_filter(self, filters):
        """
        Fetch the kid's products based on the applied filters.
        """

        query = {"masterCategory": "Personal Care", "ratings": {"$gt": 3}}

        # Apply additional filters if provided
        if filters.get("category"):
            query["subCategory"] = {"$in": filters['category']}

        # fetch products from the db based on the query 
        filtered_products = product_db.products.find(query).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list 
        filtered_products = list(filtered_products)

        # Shuffle the products
        random.shuffle(filtered_products)

        return filtered_products[:50]


    def top_50_accessories_products_default(self):
        """
        Fetch the top 50 men's products based on default filter (ratings > 4)
        and sort by ratings in descending order.
        """

        top_300 = product_db.products.find(
            {"masterCategory": "Accessories", "ratings": {"$gt": 4}}
        ).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list and return 
        top_300 = list(top_300)

        # Shuffle the data
        random.shuffle(top_300)

        return top_300[:50]
    
    def accessories_products_filter(self, filters):
        """
        Fetch the kid's products based on the applied filters.
        """

        query = {"masterCategory": "Accessories", "ratings": {"$gt": 3}}

        # Apply additional filters if provided
        if filters.get("category"):
            query["subCategory"] = {"$in": filters['category']}

        # fetch products from the db based on the query 
        filtered_products = product_db.products.find(query).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list 
        filtered_products = list(filtered_products)

        # Shuffle the products
        random.shuffle(filtered_products)

        return filtered_products[:50]


    def top_50_footwear_products_default(self):
        """
        Fetch the top 50 men's products based on default filter (ratings > 4)
        and sort by ratings in descending order.
        """

        top_300 = product_db.products.find(
            {"masterCategory": "Footwear", "ratings": {"$gt": 4}}
        ).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list and return 
        top_300 = list(top_300)

        # Shuffle the data
        random.shuffle(top_300)

        return top_300[:50]
    
    def footwear_products_filter(self, filters):
        """
        Fetch the kid's products based on the applied filters.
        """

        query = {"masterCategory": "Footwear", "ratings": {"$gt": 3}}

        # Apply additional filters if provided
        if filters.get("category"):
            query["subCategory"] = {"$in": filters['category']}

        # fetch products from the db based on the query 
        filtered_products = product_db.products.find(query).sort("ratings", pymongo.DESCENDING).limit(300)

        # Convert the cursor to a list 
        filtered_products = list(filtered_products)

        # Shuffle the products
        random.shuffle(filtered_products)

        return filtered_products[:50]

        
    def get_collaborative_recommendations(self, product_name, n=4):
        # Fetch product data from MongoDB
        ratings_data = list(product_db.products.find({}, {"userId": 1, "productDisplayName": 1, "ratings": 1}))
        
        if not ratings_data:
            return []

        # Convert to DataFrame
        ratings_df = pd.DataFrame(ratings_data)

        # Create Pivot Table (Products by Users with Ratings as Values)
        pt = ratings_df.pivot_table(index='productDisplayName', columns='userId', values='ratings').fillna(0)

        # Compute Cosine Similarity (Collaborative Filtering)
        similarity_matrix = cosine_similarity(pt)

        # Handle Missing Product
        if product_name not in pt.index:
            return []

        # Get Index of Target Product and Calculate Similarities
        product_idx = pt.index.get_loc(product_name)
        sim_scores = similarity_matrix[product_idx]

        # Sort by Similarity (Exclude Self)
        top_indices = np.argsort(sim_scores)[::-1][1:n+1]  # Exclude index 0 (self)

        # Fetch Top Similar Products
        top_products = pt.index[top_indices].tolist()
        
        # Return Full Product Details from MongoDB
        recommended_products = list(product_db.products.find({"productDisplayName": {"$in": top_products}}))
        
        return recommended_products


    def get_hybrid_search(self, query, index_name, n=40):

        # loading the vectorstore 
        vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings
        )

        top_n1 = top_n2 = n // 2

        retriever_vanilla = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": top_n1})

        # retriever_vectorstore = vector_store.as_retriever(search_kwargs={"k": 2})
        retriever_mmr = vector_store.as_retriever(search_type="mmr", search_kwargs={"k": top_n2})

        # Combine both retrievers using an ensemble approach
        ensemble_retriever = EnsembleRetriever(
            retrievers=[retriever_vanilla, retriever_mmr],
            weights=[0.5, 0.4]
        )

        # Generate a response from the hybrid retriever
        products = ensemble_retriever.invoke(query)

        product_ids = [int(product.metadata.get('id')) for product in products] 

        # Retrieve all products that match the product IDs
        searched_products = product_db.products.find({"id": {"$in": product_ids}})

        searched_products = list(searched_products)
        
        return searched_products
    
    def get_search_product(self, query, index_name, n=30):

        # loading the vectorstore 
        vector_store = PineconeVectorStore(
            index_name=index_name,
            embedding=embeddings
        )

        retriever_vanilla = vector_store.similarity_search(query=query, k=n)

        product_ids = [int(product.metadata.get('id')) for product in retriever_vanilla] 

        # Retrieve all products that match the product IDs
        searched_products = product_db.products.find({"id": {"$in": product_ids}})

        searched_products = list(searched_products)
        
        return searched_products