from pathlib import Path
from urllib.parse import quote

from app.schemas.questionnaire import DietQuestionnaire

# The dish catalogue is the set of photos: dish name = file name without the extension.
IMAGE_DIR = Path(__file__).resolve().parent / "images"
IMAGE_URL_PREFIX = "/static/meals"
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def available_dishes() -> dict[str, str]:
    """Dish name -> file name. Read on every call, so a newly added photo is available right away."""
    return {p.stem: p.name for p in sorted(IMAGE_DIR.iterdir()) if p.suffix.lower() in EXTENSIONS}


def image_url(file_name: str) -> str:
    return f"{IMAGE_URL_PREFIX}/{quote(file_name)}"


# What each dish contains, judged conservatively from the typical recipe (pancakes, bread, oats, pasta -> gluten;
# porridge, pudding, shake -> dairy). Photos without an entry are offered only to users with no restrictions.
CONTAINS: dict[str, set[str]] = {
    "Avocado with tuna and dill": {"fish"},
    "Buckwheat pancakes with vegetables": {"gluten", "egg", "dairy", "vegetables"},
    "Buckwheat porridge with kiwi and roasted sunflower seeds": {"dairy"},
    "Cherry tomato, arugula, and walnut salad with toast": {"gluten", "nuts", "vegetables"},
    "Chia pudding with strawberries": {"dairy"},
    "Chicken skewers": {"meat"},
    "Chicken stewed in carrots and tomatoes": {"meat", "vegetables"},
    "Cocoa oatmeal with cranberries and apple": {"gluten", "dairy"},
    "Cod with sauerkraut and potatoes": {"fish", "vegetables"},
    "Cottage cheese with pear and almonds": {"dairy", "nuts"},
    "Cucumber spaghetti with groats": {"gluten", "vegetables"},
    "Exotic smoothie with kale": {"vegetables"},
    "Fruit salad with curd": {"dairy"},
    "Fruit with chickpeas": set(),
    "Millet muffin with vegetables": {"gluten", "egg", "vegetables"},
    "Oatmeal pancakes with strawberries": {"gluten", "egg", "dairy"},
    "Pasta with broccoli and feta cheese": {"gluten", "dairy", "vegetables"},
    "Roasted vegetables with feta cheese": {"dairy", "vegetables"},
    "Sandwiches with avocado and bean spread": {"gluten"},
    "Stracciatella oatmeal": {"gluten", "dairy"},
    "Strawberry shake with apricots": {"dairy"},
    "Strawberry-millet pudding": {"dairy"},
    "Stuffed zucchini in tomato sauce": {"meat", "red_meat", "dairy", "vegetables"},
    "Toast with mozzarella cheese and fig": {"gluten", "dairy"},
    "Turkey and vegetable omelet with toast": {"meat", "egg", "gluten", "vegetables"},
    "Yogurt with topping": {"dairy", "nuts", "gluten"},
    "Zucchini fritters": {"egg", "gluten", "vegetables"},
    "Zucchini spread with bread": {"gluten", "vegetables"},
}
DIET_EXCLUDES = {
    "omnivore": set(),
    "pescatarian": {"meat"},
    "vegetarian": {"meat", "fish"},
    "vegan": {"meat", "fish", "egg", "dairy"},
}
ALLERGY_EXCLUDES = {"gluten": "gluten", "lactose": "dairy", "nuts": "nuts", "eggs": "egg"}


def allowed_dishes(questionnaire: DietQuestionnaire) -> dict[str, str]:
    """Dishes compatible with the diet type, allergies and dislikes; the LLM can only choose from these."""
    q = questionnaire
    excluded = (
        DIET_EXCLUDES[q.diet_type] | {ALLERGY_EXCLUDES[a] for a in q.allergies_and_intolerances} | set(q.disliked_foods)
    )
    return {
        name: file
        for name, file in available_dishes().items()
        if not excluded or name in CONTAINS and not excluded & CONTAINS[name]
    }
