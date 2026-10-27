[README_Zomato_AI_Data_Engineering.md](https://github.com/user-attachments/files/34024646/README_Zomato_AI_Data_Engineering.md)
<div align="center">

# 🍽️ Zomato AI Data Engineering Platform

### An end-to-end batch data pipeline — from raw food-delivery data to AI-powered analytics

<p>
  <img src="https://img.shields.io/badge/Pipeline-Batch-36BCF7?style=for-the-badge" alt="Batch pipeline" />
  <img src="https://img.shields.io/badge/Warehouse-Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white" alt="Snowflake" />
  <img src="https://img.shields.io/badge/Transform-dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white" alt="dbt" />
</p>

<p>
  <b>Amazon S3 · Snowflake · dbt · Apache Airflow · Gemini · Streamlit</b>
</p>

</div>

---

## 📌 Project overview

This project builds a complete batch data platform around Zomato-style food-delivery data. It moves raw CSV files into an Amazon S3 data lake, loads them into Snowflake, transforms them into analytics-ready models with dbt, and orchestrates the workflow with Apache Airflow.

An AI layer extends the warehouse with review enrichment, retrieval-augmented generation (RAG), and natural-language-to-SQL querying. Streamlit provides interfaces for the AI applications.

**End-to-end flow**

```text
Food-delivery CSVs
        │
        ▼
Amazon S3 — raw/<table>/
        │  Snowflake storage integration + IAM role
        ▼
Snowflake — ZOMATO.RAW (Bronze)
        │  COPY INTO
        ▼
dbt — ZOMATO.STAGING (Silver)
        │  clean, type, standardize
        ▼
dbt — ZOMATO.MARTS (Gold)
        │
        ├──────────────► Business analytics marts
        │                 Revenue, restaurants, delivery SLA, reviews
        │
        └──────────────► AI workflow
                           Gemini AI review enrichment
                                  │
                                  ▼
                           ZOMATO.AI / dbt AI mart
                                  │
                     ┌────────────┴────────────┐
                     ▼                         ▼
                Review RAG                Text-to-SQL
                     └────────────┬────────────┘
                                  ▼
                            Streamlit apps

Apache Airflow orchestrates the scheduled load → transform → enrich → AI-mart workflow.
```




## 🧱 Architecture and data flow

The platform is organized into layers so ingestion, transformation, orchestration, and AI workloads have clear responsibilities.

| Layer | Technology / location | Responsibility |
|---|---|---|
| **Source data** | CSV files in `data/` | Four dimension datasets — restaurants, users, food, and menu — plus three generated fact datasets |
| **Data lake** | Amazon S3 | Stores each source file under `raw/<table>/` |
| **Bronze / RAW** | Snowflake `ZOMATO.RAW` | Loads source-shaped tables using `COPY INTO` |
| **Silver / STAGING** | Snowflake `ZOMATO.STAGING` | dbt staging views clean, cast, standardize, and rename source fields |
| **Gold / MARTS** | Snowflake `ZOMATO.MARTS` | Dimensions, incremental fact tables, and business-facing aggregate marts |
| **Historical tracking** | Snowflake snapshots | Supports an SCD Type 2 snapshot |
| **AI data** | Snowflake `ZOMATO.AI` | Stores LLM-enriched review data for downstream modeling |
| **Orchestration** | Apache Airflow 3 in Docker | Runs the daily pipeline DAG and coordinates task dependencies |
| **AI applications** | Gemini AI + Streamlit | Review enrichment, review RAG, and natural-language text-to-SQL |

### Pipeline orchestration

The Airflow DAG, [`zomato_batch`](airflow/dags/zomato_batch.py), coordinates the main workflow:

```text
┌──────────────────┐
│    reload_raw    │  Load source data from S3 into Snowflake RAW
└────────┬─────────┘
         ▼
┌──────────────────┐
│  dbt_build_core  │  Build core dbt models and run tests
└────────┬─────────┘
         ▼
┌──────────────────┐
│  enrich_reviews  │  Enrich review text with OpenAI
└────────┬─────────┘
         ▼
┌──────────────────┐
│   dbt_build_ai   │  Build AI-related dbt models / marts
└──────────────────┘
```

The DAG is configured as a daily batch workflow. Credentials are supplied through environment variables and Airflow connections rather than being hard-coded into the pipeline.

---

## 📦 Dataset and scale

The project uses seven CSV datasets:

| Dataset | Type | Approximate scale / purpose |
|---|---|---|
| `restaurants` | Dimension | Restaurant attributes |
| `users` | Dimension | Customer attributes |
| `food` | Dimension | Food item attributes |
| `menu` | Dimension | Menu data |
| `orders` | Fact | **10 million** order records |
| `order_items` | Fact | **~23 million** order-item records |
| `reviews` | Fact / text | **300,000** free-text reviews |

The data directory is approximately **2.3 GB** and is intentionally excluded from the repository. Download the dataset from the [Google Drive project folder](https://drive.google.com/drive/folders/1FEnGWMHhHzzTUCZOw1-YnH2v3DMuM-rs?usp=sharing), then place the CSV files under `data/`.

---

## 🛠️ Technology stack

- **Language and data processing:** Python, Pandas
- **Cloud storage:** Amazon S3
- **Cloud data warehouse:** Snowflake
- **Transformations and data quality:** dbt Core / `dbt-snowflake`
- **Orchestration:** Apache Airflow 3, Docker, Docker Compose
- **AI / LLM:** OpenAI `gemini-3.5-flash`, `gemini-embedding-2`
- **Applications:** Streamlit
- **Infrastructure and access:** AWS IAM policy, IAM role, Snowflake storage integration

---

## 🔄 Transformation design: Medallion architecture

### 1. Bronze — `ZOMATO.RAW`

Raw tables mirror the source CSV structure. Snowflake loads files from the external S3 stage using `COPY INTO`.

### 2. Silver — `ZOMATO.STAGING`

dbt staging views standardize source data before it reaches business models. Examples include:

- Converting placeholder values such as `--` to `NULL`.
- Parsing price strings such as `₹ 200` into numeric values.
- Lowercasing email addresses.
- Applying consistent data types and column names.
- Deriving fields such as `is_delivered`.

### 3. Gold — `ZOMATO.MARTS`

Gold models are designed for analysis and reporting:

- **Dimensions:** `dim_restaurants`, `dim_customer` with age segments, `dim_food`, and a generated `dim_date` calendar.
- **Incremental facts:** `fct_orders` and `fact_order_items` use dbt incremental materialization with a `MERGE` strategy.
- **Business marts:** daily city revenue, restaurant performance, delivery service-level analysis, and review insights.
- **Historical tracking:** an SCD Type 2 snapshot.

The incremental fact models are intended to process new data on subsequent runs instead of rebuilding the full 10M+ order datasets each time.

### Data quality

The dbt project includes:

- `unique`
- `not_null`
- `relationships`
- `accepted_values`
- A singular reconciliation test

`dbt build` runs models and tests in dependency order.

---

## 🤖 AI capabilities

### 1. LLM-powered review enrichment

**File:** [`ai/enrich_reviews.py`](ai/enrich_reviews.py)

The enrichment step sends review text to OpenAI `gemini-3.5-flash` and requests structured JSON containing fields such as sentiment and topic. The enriched records are written to `ZOMATO.AI.REVIEW_ENRICHED`, where dbt can model them into review-insight marts.

The script is described as idempotent and supports a `SAMPLE_N` cap to control how many reviews are processed and help manage API costs.

### 2. Retrieval-augmented generation (RAG)

**File:** [`ai/rag_chat.py`](ai/rag_chat.py)

The review-chat application uses embeddings to retrieve reviews relevant to a user's question, then generates an answer grounded in those retrieved reviews and provides sources.

### 3. Natural-language text-to-SQL

**File:** [`ai/text_to_sql.py`](ai/text_to_sql.py)

The text-to-SQL application supplies the Gold marts' schema to the LLM so it can generate Snowflake SQL from a question written in plain English. A SELECT-only guard validates the generated query before execution using the `DBT_ROLE`.

---

## 🗂️ Repository structure

```text
.
├── airflow/
│   ├── Dockerfile                    # Airflow image and project dependencies
│   ├── docker-compose.yaml           # Airflow services and PostgreSQL
│   ├── example.env                   # Environment-variable template
│   └── dags/
│       └── zomato_batch.py           # Main four-task batch DAG
│
├── zomato/                           # dbt project
│   ├── models/
│   │   ├── staging/                  # Silver staging views, sources, tests
│   │   └── marts/                    # Gold dimensions, facts, business marts
│   └── macros/                       # Custom schema-name macro
│
├── ai/
│   ├── enrich_reviews.py             # Gemini AI review enrichment
│   ├── rag_chat.py                   # Streamlit review RAG application
│   ├── text_to_sql.py                # Streamlit text-to-SQL application
│   └── example.env                   # AI credentials template
│
├── snowflake/
│   ├── 01_setup.sql                  # Warehouse, database, schemas, role
│   ├── 02_storage_integration.sql    # S3 storage integration
│   ├── 03_stage_and_formats.sql      # External stage and CSV format
│   ├── 04_raw_tables.sql             # Bronze table definitions
│   └── 05_copy_into.sql              # Load data from the stage
│
├── aws/
│   └── iam/                          # S3 read policy and Snowflake role trust policies
│
├── docs/
│   └── architecture.png              # Architecture diagram
│
└── data/                             # Local CSVs; not committed to Git
```

> The tree above highlights the main project files described in this README. Local datasets, logs, and dbt `target/` artifacts are not committed.

---

## 🚀 Setup and execution

This project requires AWS/S3 access, a Snowflake account, and OpenAI credentials for AI features. Cloud resources and credentials must be configured for your own environment before running the pipeline.

### Step 1 — Get the data

1. Download the CSV files from the [Google Drive project folder](https://drive.google.com/drive/folders/1FEnGWMHhHzzTUCZOw1-YnH2v3DMuM-rs?usp=sharing).
2. Place them under `data/`.
3. Upload the seven CSVs to your S3 bucket using this layout:

```text
s3://<BUCKET>/raw/restaurants/
s3://<BUCKET>/raw/users/
s3://<BUCKET>/raw/food/
s3://<BUCKET>/raw/menu/
s3://<BUCKET>/raw/orders/
s3://<BUCKET>/raw/order_items/
s3://<BUCKET>/raw/reviews/
```

### Step 2 — Configure AWS and Snowflake

1. Review the IAM policy and role trust documents in [`aws/iam/`](aws/iam/).
2. In Snowflake Snowsight, run the SQL setup files in order: `snowflake/01_setup.sql` through `snowflake/05_copy_into.sql`.
3. Configure the S3 storage integration using the role ARN.
4. Run `DESC INTEGRATION` and use the returned `STORAGE_AWS_IAM_USER_ARN` and `STORAGE_AWS_EXTERNAL_ID` in the IAM role trust policy.

**Important:** The trust policy's `Principal` must use Snowflake's IAM user ARN, not `:root`. Avoid re-running `CREATE OR REPLACE` on the storage integration after configuring the trust policy: doing so can regenerate the external ID and break the trust relationship.

### Step 3 — Build the dbt models

From the dbt project directory, configure the Snowflake environment variables:

```bash
cd zomato

export SNOWFLAKE_ACCOUNT="<account>"
export SNOWFLAKE_USER="<user>"
export SNOWFLAKE_PASSWORD="<password>"

dbt debug
dbt build --exclude tag:ai
```

Use your project's expected Snowflake account identifier and authentication settings. Do not commit credentials to Git.

### Step 4 — Start Airflow with Docker

```bash
cd airflow
cp example.env .env
```

Edit `.env` and provide the required `SNOWFLAKE_*`, `GEMINI_API_KEY`, and `SAMPLE_N` values. Then build and start the services:

```bash
docker compose build
docker compose up -d
```

Open `http://localhost:8080`, unpause `zomato_batch`, and trigger the DAG.

### Step 5 — Run the AI applications

Set the OpenAI API key in your environment:

```bash
export OPENAI_API_KEY="<your-openai-api-key>"
```

Run review enrichment:

```bash
python ai/enrich_reviews.py
```

Launch the Streamlit applications:

```bash
streamlit run ai/rag_chat.py
streamlit run ai/text_to_sql.py
```

> **Execution note:** These commands reflect the repository's documented workflow. Confirm that paths, dependencies, credentials, Airflow connections, and environment variables match your local configuration before running them.

---

## 🔐 Security and cost considerations

- Keep AWS credentials, Snowflake credentials, and OpenAI API keys out of source control.
- Use the S3 read-only IAM policy and the storage integration instead of storing AWS keys in Snowflake configuration.
- Keep text-to-SQL execution restricted; the project describes a SELECT-only guard and execution under `DBT_ROLE`.
- Use `SAMPLE_N` when testing review enrichment to control API usage.
- Review generated SQL and permissions carefully before using the application with production data.


## 🎯 What this project demonstrates

- Building a batch ingestion path from Amazon S3 into Snowflake.
- Applying Bronze, Silver, and Gold layers with dbt.
- Modeling dimensions, incremental fact tables, and business marts.
- Adding automated data-quality checks to transformation workflows.
- Orchestrating dependent tasks with Apache Airflow.
- Enriching text data with an LLM and exposing review RAG and text-to-SQL applications.
- Handling cloud access and credentials through IAM, storage integrations, environment variables, and Airflow connections.

---

<div align="center">

**Built to explore the intersection of Data Engineering, Cloud Warehousing, and Applied AI.**

</div>
