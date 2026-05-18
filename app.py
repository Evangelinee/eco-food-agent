# app.py
from dotenv import load_dotenv
import streamlit as st
from groq import Groq
import os
import time
import json
import hashlib
from datetime import datetime
import pandas as pd
import plotly.express as px

# Load environment variables
load_dotenv()

# -----------------------------
# API CONFIGURATION
# -----------------------------
groq_key = os.getenv("GROQ_KEY")

if not groq_key:
    st.error("GROQ_KEY not found in .env file")
    st.stop()

client = Groq(api_key=groq_key)

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="EcoChef - Sustainable Recipe Generator",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stButton > button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    .sustainability-high {
        color: #4CAF50;
        font-weight: bold;
    }
    .sustainability-medium {
        color: #FFA726;
        font-weight: bold;
    }
    .sustainability-low {
        color: #f44336;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# DATABASE OF CARBON FOOTPRINTS
# -----------------------------
CARBON_FOOTPRINT_DB = {
    # Proteins
    "beef": 27.0, "lamb": 24.5, "pork": 7.2, "chicken": 5.7, "turkey": 5.0,
    "fish": 4.5, "salmon": 4.2, "tuna": 4.0, "shrimp": 5.1, "tofu": 2.0,
    "tempeh": 2.1, "seitan": 2.2, "lentils": 0.9, "beans": 0.8, "chickpeas": 0.8,
    "eggs": 3.5, "cheese": 8.5, "milk": 2.5, "yogurt": 2.3,
    
    # Vegetables
    "tomato": 0.7, "potato": 0.3, "carrot": 0.4, "broccoli": 0.5, "spinach": 0.6,
    "lettuce": 0.4, "cucumber": 0.4, "bell pepper": 0.5, "onion": 0.3, "garlic": 0.2,
    "mushroom": 0.3, "zucchini": 0.4, "cauliflower": 0.5, "kale": 0.5, "celery": 0.3,
    
    # Fruits
    "apple": 0.4, "banana": 0.6, "orange": 0.5, "berry": 0.3, "avocado": 1.2,
    
    # Grains
    "rice": 1.5, "pasta": 1.2, "bread": 1.0, "quinoa": 1.3, "oats": 0.7,
    "flour": 0.9, "noodles": 1.1, "cereal": 1.4,
    
    # Oils & Fats
    "olive oil": 3.2, "coconut oil": 2.8, "butter": 12.0, "vegetable oil": 2.5,
    
    # Default
    "default": 1.0
}

# -----------------------------
# SUSTAINABILITY SCORE CALCULATOR
# -----------------------------
def calculate_sustainability_score(ingredients):
    """Calculate sustainability score based on carbon footprint"""
    total_footprint = 0
    ingredient_count = 0
    
    for ingredient in ingredients:
        ingredient_lower = ingredient.lower()
        footprint = CARBON_FOOTPRINT_DB.get("default", 1.0)
        
        for key in CARBON_FOOTPRINT_DB:
            if key in ingredient_lower:
                footprint = CARBON_FOOTPRINT_DB[key]
                break
        
        total_footprint += footprint
        ingredient_count += 1
    
    avg_footprint = total_footprint / ingredient_count if ingredient_count > 0 else 0
    
    # Score from 0-10 (lower footprint = higher score)
    if avg_footprint <= 1:
        score = 10
    elif avg_footprint <= 2:
        score = 9
    elif avg_footprint <= 3:
        score = 8
    elif avg_footprint <= 4:
        score = 7
    elif avg_footprint <= 5:
        score = 6
    elif avg_footprint <= 6:
        score = 5
    elif avg_footprint <= 8:
        score = 4
    elif avg_footprint <= 10:
        score = 3
    elif avg_footprint <= 12:
        score = 2
    else:
        score = 1
    
    return score, avg_footprint

def get_sustainability_label(score):
    """Get sustainability label based on score"""
    if score >= 8:
        return "Excellent", "high", "🌱 Low Carbon Footprint"
    elif score >= 6:
        return "Good", "medium", "♻️ Moderate Carbon Footprint"
    elif score >= 4:
        return "Fair", "medium", "⚠️ Average Carbon Footprint"
    else:
        return "Needs Improvement", "low", "🔥 High Carbon Footprint"

# -----------------------------
# RECIPE GENERATION WITH GROQ
# -----------------------------
def generate_recipe(ingredients, meal_type, diet, servings, cuisine, cooking_time):
    """Generate sustainable recipe with all details"""
    
    prompt = f"""Create a detailed, sustainable recipe with the following parameters:

MEAL TYPE: {meal_type}
DIET: {diet}
CUISINE PREFERENCE: {cuisine}
SERVINGS: {servings}
MAX COOKING TIME: {cooking_time} minutes
AVAILABLE INGREDIENTS: {', '.join(ingredients)}

REQUIREMENTS:
1. Scale all ingredient quantities for exactly {servings} servings
2. Calculate total preparation and cooking time
3. Include carbon footprint estimation
4. Provide sustainability tips
5. Suggest leftover reuse ideas

FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS (use these headers):

# RECIPE: [Creative Recipe Name]

## QUICK FACTS
- Prep Time: [X minutes]
- Cook Time: [X minutes]  
- Total Time: [X minutes]
- Servings: {servings}
- Difficulty: [Easy/Medium/Hard]
- Cuisine: {cuisine}

## INGREDIENTS
[For {servings} servings:]
- [Ingredient 1]: [Quantity with units]
- [Ingredient 2]: [Quantity with units]
- [Add more as needed]

## INSTRUCTIONS
[Step-by-step numbered instructions]

## CARBON FOOTPRINT
- Total CO2e: [X.X kg CO2e]
- Per Serving: [X.X kg CO2e]
- Main Contributors: [List top 3 ingredients with highest footprint]

## SUSTAINABILITY SCORE: [X/10]
[Brief explanation of the score]

## FOOD WASTE REDUCTION TIPS
1. [Specific tip 1]
2. [Specific tip 2]  
3. [Specific tip 3]

## LEFTOVER REUSE IDEAS
1. [Creative way to reuse leftovers]
2. [Another creative idea]
3. [How to store for later use]

## ECO-FRIENDLY SWAPS
- [Ingredient] → [More sustainable alternative]
- [Ingredient] → [More sustainable alternative]

Make the recipe practical, delicious, and highly sustainable."""
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert sustainable chef focused on reducing food waste and carbon footprint. Create detailed, practical recipes with precise quantities."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=3000
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Recipe generation error: {e}")
        return None

# -----------------------------
# INGREDIENT SUGGESTIONS DATABASE
# -----------------------------
def get_ingredient_suggestions(meal_type, diet, cuisine):
    """Get dynamic ingredient suggestions"""
    
    suggestions_db = {
        "Breakfast": {
            "Vegetarian": ["Eggs", "Milk", "Bread", "Butter", "Cheese", "Tomatoes", "Spinach", "Mushrooms", "Onions", "Bell Peppers", "Avocado", "Herbs"],
            "Vegan": ["Oats", "Bananas", "Berries", "Almond Milk", "Chia Seeds", "Tofu", "Avocado", "Spinach", "Maple Syrup", "Nuts", "Seeds"],
            "Non-Vegetarian": ["Eggs", "Bacon", "Sausages", "Milk", "Bread", "Cheese", "Ham", "Butter", "Hash Browns", "Smoked Salmon"]
        },
        "Lunch": {
            "Vegetarian": ["Lettuce", "Tomatoes", "Cucumber", "Cheese", "Bread", "Avocado", "Hummus", "Bell Peppers", "Olives", "Quinoa"],
            "Vegan": ["Quinoa", "Chickpeas", "Kale", "Avocado", "Bell Peppers", "Tofu", "Cucumber", "Carrots", "Tahini", "Lentils"],
            "Non-Vegetarian": ["Chicken", "Tuna", "Lettuce", "Tomatoes", "Bread", "Cheese", "Mayonnaise", "Turkey", "Ham", "Eggs"]
        },
        "Dinner": {
            "Vegetarian": ["Pasta", "Tomato Sauce", "Garlic", "Onions", "Zucchini", "Bell Peppers", "Mushrooms", "Spinach", "Parmesan", "Olive Oil"],
            "Vegan": ["Lentils", "Rice", "Coconut Milk", "Curry Paste", "Vegetables", "Tofu", "Ginger", "Garlic", "Spinach", "Sweet Potatoes"],
            "Non-Vegetarian": ["Chicken", "Rice", "Broccoli", "Garlic", "Soy Sauce", "Ginger", "Onions", "Carrots", "Beef", "Fish"]
        },
        "Snack": {
            "Vegetarian": ["Yogurt", "Fruits", "Nuts", "Honey", "Granola", "Cheese", "Crackers", "Peanut Butter", "Hummus"],
            "Vegan": ["Hummus", "Carrots", "Celery", "Nuts", "Fruits", "Rice Cakes", "Apple Slices", "Almond Butter", "Roasted Chickpeas"],
            "Non-Vegetarian": ["Eggs", "Cheese", "Nuts", "Yogurt", "Dried Meat", "Crackers", "Jerky", "Tuna"]
        }
    }
    
    base_suggestions = suggestions_db.get(meal_type, {}).get(diet, ["Vegetables", "Protein", "Grains", "Herbs", "Spices"])
    
    # Add cuisine-specific suggestions
    cuisine_suggestions = {
        "Italian": ["Basil", "Oregano", "Parmesan", "Tomatoes", "Garlic", "Olive Oil", "Pasta"],
        "Mexican": ["Beans", "Corn", "Avocado", "Lime", "Cilantro", "Tortillas", "Chili"],
        "Asian": ["Soy Sauce", "Ginger", "Garlic", "Rice", "Noodles", "Sesame Oil", "Tofu"],
        "Indian": ["Curry Powder", "Turmeric", "Cumin", "Ginger", "Garlic", "Lentils", "Rice"],
        "Mediterranean": ["Olive Oil", "Lemon", "Garlic", "Herbs", "Cucumber", "Tomatoes", "Feta"],
        "American": ["Potatoes", "Corn", "Beans", "Cheese", "Bread", "Chicken", "Beef"]
    }
    
    cuisine_sugg = cuisine_suggestions.get(cuisine, [])
    all_suggestions = list(set(base_suggestions + cuisine_sugg))
    
    return all_suggestions[:12]  # Return top 12 suggestions

# -----------------------------
# SAVE RECIPE HISTORY
# -----------------------------
def save_to_history(recipe, ingredients, meal_type, diet, servings):
    """Save generated recipe to history"""
    if 'recipe_history' not in st.session_state:
        st.session_state.recipe_history = []
    
    history_entry = {
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'recipe': recipe,
        'ingredients': ingredients,
        'meal_type': meal_type,
        'diet': diet,
        'servings': servings
    }
    
    st.session_state.recipe_history.insert(0, history_entry)
    
    # Keep only last 10 recipes
    if len(st.session_state.recipe_history) > 10:
        st.session_state.recipe_history = st.session_state.recipe_history[:10]

# -----------------------------
# MAIN APPLICATION
# -----------------------------
def main():
    st.title("🌱 EcoChef - Sustainable Recipe Generator")
    st.markdown("*Create delicious, sustainable meals while reducing your carbon footprint*")
    
    # Sidebar Configuration
    with st.sidebar:
        st.header("⚙️ Recipe Settings")
        
        meal_type = st.selectbox("Meal Type", ["Breakfast", "Lunch", "Dinner", "Snack"])
        diet = st.selectbox("Diet Preference", ["Vegetarian", "Vegan", "Non-Vegetarian"])
        cuisine = st.selectbox("Cuisine Type", ["Any", "Italian", "Mexican", "Asian", "Indian", "Mediterranean", "American"])
        servings = st.number_input("Number of Servings", min_value=1, max_value=12, value=2)
        cooking_time = st.slider("Maximum Cooking Time (minutes)", 15, 120, 45, 15)
        
        st.markdown("---")
        st.header("📊 Carbon Footprint Info")
        st.info(
            "🐄 Beef: 27kg CO2e/kg\n"
            "🐖 Pork: 7kg CO2e/kg\n"
            "🐔 Chicken: 5.7kg CO2e/kg\n"
            "🥬 Vegetables: 0.3-0.7kg CO2e/kg\n"
            "🌱 Plant-based proteins: 0.8-2kg CO2e/kg"
        )
        
        st.markdown("---")
        st.header("📜 Recipe History")
        if 'recipe_history' in st.session_state and st.session_state.recipe_history:
            for entry in st.session_state.recipe_history[:5]:
                with st.expander(f"{entry['timestamp'][:16]} - {entry['meal_type']}"):
                    st.caption(f"Ingredients: {', '.join(entry['ingredients'][:3])}...")
                    if st.button(f"Load Recipe", key=f"load_{entry['timestamp']}"):
                        st.session_state.loaded_recipe = entry['recipe']
                        st.rerun()
        else:
            st.caption("No recipes generated yet")
    
    # Main content area - 2 columns
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.subheader("📝 Your Ingredients")
        
        # Ingredient input
        ingredients_input = st.text_area(
            "Enter ingredients (comma-separated):",
            placeholder="Example: chicken breast, broccoli, garlic, olive oil, rice, soy sauce",
            height=100,
            key="ingredients_input"
        )
        
        # Action buttons
        col_add, col_clear = st.columns(2)
        with col_add:
            if st.button("➕ Add Ingredients", type="primary"):
                if ingredients_input:
                    new_ingredients = [i.strip() for i in ingredients_input.split(',') if i.strip()]
                    if 'ingredients_list' not in st.session_state:
                        st.session_state.ingredients_list = []
                    st.session_state.ingredients_list.extend(new_ingredients)
                    st.session_state.ingredients_list = list(set(st.session_state.ingredients_list))
                    st.success(f"✅ Added {len(new_ingredients)} ingredients!")
                    st.rerun()
        
        with col_clear:
            if st.button("🗑️ Clear All"):
                if 'ingredients_list' in st.session_state:
                    st.session_state.ingredients_list = []
                st.rerun()
        
        st.markdown("---")
        st.subheader("💡 Quick Add Ingredients")
        
        # Get suggestions based on selections
        suggestions = get_ingredient_suggestions(meal_type, diet, cuisine)
        
        # Display suggestions as a grid
        cols = st.columns(4)
        for idx, ingredient in enumerate(suggestions):
            with cols[idx % 4]:
                if st.button(f"+ {ingredient}", key=f"sugg_{idx}"):
                    if 'ingredients_list' not in st.session_state:
                        st.session_state.ingredients_list = []
                    if ingredient not in st.session_state.ingredients_list:
                        st.session_state.ingredients_list.append(ingredient)
                        st.rerun()
        
        st.markdown("---")
        st.subheader("✨ Generate Recipe")
        
        if st.button("🌱 Generate Sustainable Recipe", type="primary", use_container_width=True):
            if 'ingredients_list' not in st.session_state or not st.session_state.ingredients_list:
                st.warning("⚠️ Please add some ingredients first!")
            else:
                with st.spinner("🌿 Creating your sustainable recipe..."):
                    recipe = generate_recipe(
                        st.session_state.ingredients_list,
                        meal_type,
                        diet,
                        servings,
                        cuisine,
                        cooking_time
                    )
                    
                    if recipe:
                        st.session_state.generated_recipe = recipe
                        st.session_state.current_ingredients = st.session_state.ingredients_list.copy()
                        save_to_history(recipe, st.session_state.ingredients_list, meal_type, diet, servings)
                        st.success("✅ Recipe generated successfully!")
                        st.rerun()
    
    with col2:
        st.subheader("🥗 Your Ingredients List")
        
        if 'ingredients_list' in st.session_state and st.session_state.ingredients_list:
            # Calculate sustainability score
            score, avg_footprint = calculate_sustainability_score(st.session_state.ingredients_list)
            label, css_class, description = get_sustainability_label(score)
            
            # Display metrics
            st.markdown("### 📊 Sustainability Metrics")
            
            metric_col1, metric_col2 = st.columns(2)
            with metric_col1:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{score}/10</h3>
                    <p>Sustainability Score</p>
                    <p class="sustainability-{css_class}">{label}</p>
                </div>
                """, unsafe_allow_html=True)
            
            with metric_col2:
                st.markdown(f"""
                <div class="metric-card">
                    <h3>{avg_footprint:.1f}</h3>
                    <p>kg CO2e/kg avg</p>
                    <p>{description}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown(f"**{len(st.session_state.ingredients_list)} ingredients:**")
            
            # Display ingredients with remove buttons
            for idx, ingredient in enumerate(st.session_state.ingredients_list):
                col_ing, col_remove = st.columns([4, 1])
                with col_ing:
                    # Show carbon footprint for each ingredient
                    ingredient_lower = ingredient.lower()
                    footprint = CARBON_FOOTPRINT_DB.get("default", 1.0)
                    for key in CARBON_FOOTPRINT_DB:
                        if key in ingredient_lower:
                            footprint = CARBON_FOOTPRINT_DB[key]
                            break
                    
                    footprint_emoji = "🌱" if footprint <= 2 else "⚠️" if footprint <= 5 else "🔥"
                    st.markdown(f"{footprint_emoji} **{ingredient.capitalize()}** *({footprint:.1f} kg CO2e/kg)*")
                
                with col_remove:
                    if st.button("✖", key=f"remove_{idx}"):
                        st.session_state.ingredients_list.pop(idx)
                        st.rerun()
            
            # Carbon footprint chart
            if st.button("📊 Show Carbon Footprint Analysis"):
                footprint_data = []
                for ingredient in st.session_state.ingredients_list:
                    ingredient_lower = ingredient.lower()
                    footprint = CARBON_FOOTPRINT_DB.get("default", 1.0)
                    for key in CARBON_FOOTPRINT_DB:
                        if key in ingredient_lower:
                            footprint = CARBON_FOOTPRINT_DB[key]
                            break
                    footprint_data.append({'Ingredient': ingredient.capitalize(), 'CO2e (kg/kg)': footprint})
                
                df = pd.DataFrame(footprint_data)
                fig = px.bar(df, x='Ingredient', y='CO2e (kg/kg)', 
                            title="Carbon Footprint by Ingredient",
                            color='CO2e (kg/kg)',
                            color_continuous_scale='RdYlGn')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("👈 No ingredients yet. Add ingredients from the left panel!")
    
    # Display generated recipe
    if 'generated_recipe' in st.session_state:
        st.markdown("---")
        st.markdown("## 🍽️ Your Sustainable Recipe")
        
        # Recipe display with styling
        with st.container():
            st.markdown(st.session_state.generated_recipe)
            
            # Action buttons for recipe
            col_download, col_save, col_new = st.columns(3)
            
            with col_download:
                st.download_button(
                    label="📥 Download Recipe",
                    data=st.session_state.generated_recipe,
                    file_name=f"ecochef_recipe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col_save:
                if st.button("💾 Save to Favorites", use_container_width=True):
                    if 'favorites' not in st.session_state:
                        st.session_state.favorites = []
                    st.session_state.favorites.append({
                        'name': f"Recipe_{len(st.session_state.favorites)}",
                        'recipe': st.session_state.generated_recipe,
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })
                    st.success("✅ Saved to favorites!")
            
            with col_new:
                if st.button("🔄 New Recipe", use_container_width=True):
                    if 'generated_recipe' in st.session_state:
                        del st.session_state.generated_recipe
                    st.rerun()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p>🌱 EcoChef - Reducing food waste one recipe at a time</p>
        <p>Sustainability scores based on carbon footprint data from scientific research</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()