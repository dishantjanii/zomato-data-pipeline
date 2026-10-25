import os
import pandas as pd
import numpy as np
import streamlit as st
import snowflake.connector
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

EMBEDDING_MODEL="gemini-embedding-2"
CHAT_MODEL="gemini-3.8-flash"
NEW_REVIEWS=500
TOP_K=5
CHACHE_FILE="review_embeddings.parquet"
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def read_reviews_from_snowflake():
    conn=snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
    )

    query=f"""
            SELECT REVIEW_ID,CITY,RATING,COMMENT
            FROM ZOMATO.STAGING.STG_REVIEWS
            SAMPLE({NEW_REVIEWS} ROWS);
    """

    df= conn.cursor().execute(query).fetch_pandas_all()
    conn.close()
    df.columns=[col.lower() for col in df.columns]
    return df
    

def embed(texts):
    # Gemini embeddings expect a single content piece; we embed each text individually
    embeddings = []
    for txt in texts:
        resp = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=txt,
            task_type="retrieval_query"
        )
        embeddings.append(resp["embedding"])
    return embeddings


@st.cache_data(persist=True,show_spinner="")
def load_reviews():
    """Load reviews with embeddings, using cache if available."""
    if os.path.exists(CHACHE_FILE):
        df = pd.read_parquet(CHACHE_FILE)
        return df
    df = read_reviews_from_snowflake()
    df['embedding'] = embed(df['comment'].tolist())
    df.to_parquet(CHACHE_FILE)
    return df
st.title("Zomato AI Assistant")
st.caption(f"Searching  {NEW_REVIEWS} review, answering with {CHAT_MODEL} model")

def cosine_similarity(vec_a,vec_b):
    return np.dot(vec_a,vec_b)/(np.linalg.norm(vec_a)*np.linalg.norm(vec_b))

def find_similar_reviews(question,df):
    question_vector = embed([question])[0]
    scores = []

    for review_vector in df['embedding']:
        scores.append(cosine_similarity(question_vector,review_vector))
    
    df=df.copy()
    df['score'] = scores
    return df.nlargest(TOP_K,'score')

def ask_llm(question,top_reviews):
    context = ""
    for _, row in top_reviews.iterrows():
        context+= f"_{row['city']},{row['rating']} {row['comment']}\n"

    SYSTEM_PROMPT=(
        "Answer ONLY using the customer reviews provided."
        "Be concise. If the reviews don't covert if, say so "

    )   
    user_prompt = f"Questions: {question}\nReviews:\n{context}"

    model = genai.GenerativeModel(CHAT_MODEL)
    response = model.generate_content(
        [SYSTEM_PROMPT, user_prompt],
        generation_config=genai.GenerationConfig(temperature=0.2)
    )
    return response.text   

review_df = load_reviews()



question = st.text_input("Ask a question about your reviews:",
                        placeholder="e.g. what are the most common compalaints about delivery"
)

if question:
    top_reviews = find_similar_reviews(question,review_df)
    answer=ask_llm(question,top_reviews)

    st.markdown("**Answer:**")
    st.write(answer)

    with st.expander("Reviews used to build this answer"):
        st.dataframe(top_reviews[['city','rating','comment']],hide_index = True)


