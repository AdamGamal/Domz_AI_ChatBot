from flask import Blueprint, request, jsonify, session, render_template
from app.chat import is_product_query, get_ai_response
from fuzzywuzzy import fuzz
import sqlite3
import os

# Create a Blueprint for the main routes
main = Blueprint("main", __name__)

# Database path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE_PATH = os.path.join(BASE_DIR, "ecommerce_products.db")

# Fetch products with fuzzy matching
def fetch_products_by_name(database_path, query):
    try:
        connection = sqlite3.connect(database_path)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM products")
        columns = [column[0] for column in cursor.description]
        all_products = cursor.fetchall()
        connection.close()

        matches = []
        for product in all_products:
            name_match = fuzz.partial_ratio(query.lower(), product[1].lower())
            description_match = fuzz.partial_ratio(query.lower(), product[3].lower())
            if name_match > 52 or description_match > 52:
                matches.append((name_match + description_match, product))

        matches.sort(reverse=True, key=lambda x: x[0])
        return [match[1] for match in matches], columns
    except Exception as e:
        print(f"Database error: {e}")
        return [], []

@main.before_request
def initialize_session():
    """Initialize session variables."""
    if "cart" not in session:
        session["cart"] = []  # Initialize empty cart
    if "products" not in session:
        session["products"] = []
    session.setdefault("current_page", 1)
    session.setdefault("awaiting_product_selection", False)
    session.setdefault("last_selected_product", None)
    session.setdefault("filtered_products", [])
    session.setdefault("comparison_mode", False)

@main.route("/")
def index():
    """Serve the chatbot UI."""
    return render_template("chat.html")

@main.route("/cart", methods=["GET"])
def get_cart():
    """Fetch the cart details."""
    cart = session.get("cart", [])
    try:
        total = sum([float(item["price"].replace("LE", "").replace(",", "").strip()) for item in cart])
        cart_details = []
        for item in cart:
            product_url = item.get("url")
            if not product_url:
                print(f"Warning: Missing URL for product ID {item.get('id')}")
                continue
            cart_details.append({
                "name": item["name"],
                "price": item["price"],
                "url": product_url,
                "id": item.get("id")
            })
        return jsonify({"cart": cart_details, "total": f"LE {total:.2f}"})
    except ValueError as e:
        print(f"Error calculating total: {e}")
        return jsonify({"cart": [], "total": "LE 0.00"})

@main.route("/get", methods=["POST"])
def chat():
    """Handle user queries and product exploration."""
    user_input = request.form.get("msg").strip().lower()
    if not user_input:
        return jsonify({"response": "Please provide a valid input.", "enableNext": False, "updateCart": False})

    user_input = " ".join(user_input.split()).lower()

    products = session.get("products", [])
    cart = session.get("cart", [])
    last_selected_product = session.get("last_selected_product", None)
    page_size = 5

    # Check if user is asking about a product's details
    if last_selected_product:
        product_details = {
            "name": last_selected_product[1],
            "price": last_selected_product[2],
            "description": last_selected_product[3],
            "colors": last_selected_product[4],
            "sizes": last_selected_product[5],
            "stock_status": last_selected_product[6],
            "url": last_selected_product[7]
        }
        for key in product_details.keys():
            if key in user_input:
                return jsonify({"response": f"The {key} of {last_selected_product[1]} is: {product_details[key]}", "updateCart": False})

    if (
    user_input == "reset my cart" or
    user_input == "clear my cart" or
    user_input == "empty my cart" or
    user_input == "reset cart" or
    user_input == "clear cart" or
    user_input == "empty cart"
):

        session["cart"] = []
        return jsonify({"response": "Your cart has been cleared.", "updateCart": True})

    if (
    user_input == "what is in my cart" or
    user_input == "show my cart" or
    user_input == "what's in my cart" or
    user_input == "show cart" or
    user_input == "view my cart" or
    user_input == "view cart" or
    user_input == "cart"
):

        if not cart:
            return jsonify({"response": "Your cart is empty.", "updateCart": False})
        response = "Your cart contains:\n"
        for item in cart:
            response += f"- {item['name']}: {item['price']}\nView Product: {item['url']}\n"
        total = sum([float(item["price"].replace("LE", "").replace(",", "").strip()) for item in cart])
        response += f"Total: LE {total:.2f}"
        return jsonify({"response": response, "updateCart": False})

    # Add product to the cart
    if (
    "add this product" in user_input or
    "add it to the cart" in user_input or
    "add it" in user_input or
    "put it" in user_input or
    "add to cart" in user_input or
    "add to my cart" in user_input
):

        if last_selected_product:
            cart.append({
                "name": last_selected_product[1],
                "price": last_selected_product[2],
                "url": last_selected_product[7]
            })
            session["cart"] = cart
            return jsonify({"response": f"Added {last_selected_product[1]} to your cart.", "updateCart": True})
        else:
            return jsonify({"response": "Please select a product first before adding it to your cart.", "updateCart": False})

    # Product search
    selected_product = next((p for p in products if user_input in p[1].strip().lower()), None)

    if selected_product:
        session["last_selected_product"] = selected_product
        brief_response = (
            f"Certainly! '{selected_product[1]}' is a popular item. It stands out for its {selected_product[4]}, "
            f"color options and availability in {selected_product[5]} sizes, making it a favorite among our customers."
        )
        if selected_product[6].lower() == "out of stock":
            response = (
                f"Here are the details for {selected_product[1]}:\n"
                f"💲 Price: {selected_product[2]}\n"
                f"📖 Description: {selected_product[3]}\n"
                f"🎉 Colors: {selected_product[4]}\n"
                f"🔠 Sizes: {selected_product[5]}\n"
                f"The product '{selected_product[1]}' is currently out of stock."
            )
        else:
            response = (
                f"Here are the details for {selected_product[1]}:\n"
                f"💲 Price: {selected_product[2]}\n"
                f"📖 Description: {selected_product[3]}\n"
                f"🎉 Colors: {selected_product[4]}\n"
                f"🔠 Sizes: {selected_product[5]}\n"
                f"📦 Stock Status: {selected_product[6]}\n"
            )

        # Add the prompt to add the product to the cart
        response += "\nsimply type add this product to the cart?."

        checkout_links = f"Checkout URLs: {selected_product[7]}" if selected_product[7] else "No checkout URL available."
        return jsonify({"response": f"{brief_response}\n\n{response}", "checkout_links": checkout_links, "updateCart": False})

    # Handle next page pagination
    if user_input == "next":
        total_pages = (len(products) + page_size - 1) // page_size
        current_page = session["current_page"]

        if current_page < total_pages:
            session["current_page"] += 1
            start = (session["current_page"] - 1) * page_size
            end = start + page_size
            products_on_page = products[start:end]

            response = "Here are more products:\n"
            for product in products_on_page:
                response += f"🛏️ {product[1]}\n"
            response += "Type the product name for more details."
            return jsonify({"response": response.strip(), "enableNext": session["current_page"] < total_pages})

    # Handle product query (search products)
    if is_product_query(user_input):
        products, columns = fetch_products_by_name(DATABASE_PATH, user_input)
        if products:
            session["products"] = products
            session["current_page"] = 1
            response = "I found these products. Are you interested in any? Type the product name for more details:\n"
            for product in products[:5]:
                response += f"🛏️ {product[1]}\n"
            if len(products) > 5:
                response += "Reply 'Next' to see more products."
            return jsonify({"response": response.strip(), "enableNext": len(products) > 5})

        return jsonify({"response": "Sorry, I couldn't find any products matching your query."})

    if (
    "do they have sizes" in user_input or
    "what sizes are available" in user_input or
    "available sizes" in user_input or
    "sizes available" in user_input or
    "what sizes do they have" in user_input or
    "do they have this size" in user_input or
    "is this size available" in user_input or
    "what are the sizes" in user_input
):
        if last_selected_product:
            sizes = last_selected_product[5]
            response = f"The available sizes for {last_selected_product[1]} are: {sizes}."
            return jsonify({"response": response, "updateCart": False})
    if (
    "what is the price" in user_input or
    "how much is it" in user_input or
    "what's the price" in user_input or
    "price of" in user_input or
    "how much does it cost" in user_input
):
        if last_selected_product:
            price = last_selected_product[2]
            response = f"The price of {last_selected_product[1]} is: {price}."
            return jsonify({"response": response, "updateCart": False})
    if (
    "do they have colors" in user_input or
    "what colors are available" in user_input or
    "available colors" in user_input or
    "colors available" in user_input or
    "what colors do they have" in user_input or
    "is this color available" in user_input or
    "what are the colors" in user_input
):
        if last_selected_product:
            colors = last_selected_product[4]
            response = f"The available colors for {last_selected_product[1]} are: {colors}."
            return jsonify({"response": response, "updateCart": False})

    if (
    "what is the description" in user_input or
    "tell me about it" in user_input or
    "describe this product" in user_input or
    "what does it do" in user_input or
    "can you describe it" in user_input or
    "details about the product" in user_input
):
        if last_selected_product:
            description = last_selected_product[3]
            response = f"Here is the description for {last_selected_product[1]}: {description}."
            return jsonify({"response": response, "updateCart": False})

    if (
    "where can I buy it" in user_input or
    "give me the link" in user_input or
    "product URL" in user_input or
    "show me the website" in user_input or
    "where is it listed" in user_input or
    "can I see the link" in user_input
):
        if last_selected_product:
            url = last_selected_product[7]
            response = f"You can find {last_selected_product[1]} here: {url}."
            return jsonify({"response": response, "updateCart": False})

    response = get_ai_response(user_input)
    return jsonify({"response": response, "updateCart": False})
