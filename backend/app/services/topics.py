import random

TOPICS = [
    "Travel & Adventure",
    "Food & Cooking",
    "Movies & TV Shows",
    "Music & Concerts",
    "Technology & Gadgets",
    "Sports & Fitness",
    "Books & Literature",
    "Career & Work Life",
    "Hobbies & Interests",
    "Science & Space",
    "Environment & Nature",
    "Art & Photography",
    "Fashion & Style",
    "Health & Wellness",
    "History & Culture",
    "Gaming & Esports",
    "Family & Relationships",
    "Politics & Society",
    "Animals & Pets",
    "Dreams & Goals",
    "Comedy & Memes",
    "Languages & Learning",
    "Weekend Plans",
    "Childhood Memories",
]


def get_random_topic() -> str:
    return random.choice(TOPICS)
