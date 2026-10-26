import os
import json
import snowflake.connector
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

MODEL = "gemini-1.5-flash"
SAMPLE_N = 5
TOPICS = ["food quality","delivery","pricing","service","packaging","other"]

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')


SYSTEM_PROMPT = f"""
you classify customer reviews for food delivery app.

for the review you are given,return:
- sentiment_label: positive,negative,or neutral
-sentiment_score: a number between -1.0 and 1.0
-topic: one of {TOPICS}
-key_issue: a short phrase of 6 words or less that describes the main issue in the review, if any. if there is no issue, return null


Reply as JSON in this exact format:
{{
    "sentiment_label":"<sentiment_label>",
    "sentiment_score":<sentiment_score>,
    "topic":"<topic>",
    "key_issue":"<key_issue>"

}}

"""


def get_connection():
    return snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

def create_output_table(cursor):
    cursor.execute("CREATE SCHEMA IF NOT EXISTS ZOMATO.AI")
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS ZOMATO.AI.REVIEW_ENRICHED(
                REVIEW_ID STRING,
                SENTIMENT_LABEL STRING,
                SENTIMENT_SCORE FLOAT,
                TOPIC STRING,
                KEY_ISSUE STRING,
                MODEL STRING,
                ENRICHED_AT TIMESTAMP_LTZ DEFAULT CURRENT_TIMESTAMP()
            )
    ;

    
    
""")

def get_reviews_to_enrich(cursor):
    cursor.execute(f"""
        SELECT 
            REVIEW_ID,
            COMMENT
        FROM ZOMATO.RAW.REVIEWS
        WHERE REVIEW_ID  NOT IN (SELECT REVIEW_ID FROM ZOMATO.AI.REVIEW_ENRICHED)
        ORDER BY REVIEW_ID
        LIMIT {SAMPLE_N}
    """)

    return cursor.fetchall()

def classify_review(comment):
    try:
        response = model.generate_content(
            [SYSTEM_PROMPT, comment],
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,
                response_mime_type='application/json'
            )
        )
        answer = response.text.strip()
        return json.loads(answer)
    except Exception as e:
        raise e


def save_results(cursor, results):
    cursor.executemany("""
        INSERT INTO ZOMATO.AI.REVIEW_ENRICHED(
            REVIEW_ID,
            SENTIMENT_LABEL,
            SENTIMENT_SCORE,
            TOPIC,
            KEY_ISSUE,
            MODEL
        )

        VALUES(%(REVIEW_ID)s,%(SENTIMENT_LABEL)s,%(SENTIMENT_SCORE)s,%(TOPIC)s,%(KEY_ISSUE)s,%(MODEL)s)

    """, results)


def main():
    conn = get_connection()
    cursor = conn.cursor()

    create_output_table(cursor)
    reviews = get_reviews_to_enrich(cursor)
    if len(reviews) == 0:
        print("No reviews to enrich,exiting")
        return

    results = []

    for review_id, comment in reviews:
        print(f"classifying {review_id} : {comment}")
        try:
            labels = classify_review(comment)
            print(f"labels for review {review_id}:{labels}")
            results.append(
                {
                    "REVIEW_ID": review_id,
                    "SENTIMENT_LABEL": labels["sentiment_label"],
                    "SENTIMENT_SCORE": labels["sentiment_score"],
                    "TOPIC": labels["topic"],
                    "KEY_ISSUE": labels["key_issue"],
                    "MODEL": MODEL
                }
            )
        except Exception as e:
            print(f"Error classifying review {review_id}: {str(e)}")

    save_results(cursor, results)
    print(f"successfully classified {len(results)} reviews")
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
