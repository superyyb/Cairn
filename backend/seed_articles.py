"""
种子脚本：清空文章表，插入 30 篇测试文章，并生成 AI 摘要 + 标签 + 向量。
运行前确认 USER_ID 正确。
"""
import logging
from app.core.database import SessionLocal
from app.models.article import Article
from app.models.tag import Tag
from app.core.utils import hash_url
from app.services.ai_service import analyze_article, embed_article

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

USER_ID = 2  # alice@example.com

ARTICLES = [
    # ===== Kubernetes / Containers =====
    {
        "url": "https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/",
        "title": "Kubernetes Scheduler: How Pods Get Assigned to Nodes",
        "content": """The Kubernetes scheduler is a control plane component that assigns Pods to Nodes.
The scheduler determines which Nodes are valid placements for each Pod in the scheduling queue
according to constraints and available resources. It then ranks each valid Node and binds the
Pod to a suitable Node. Multiple different schedulers may be used within a cluster. The scheduler
watches for newly created Pods that have no Node assigned. For every Pod the scheduler discovers,
the scheduler becomes responsible for finding the best Node for that Pod to run on.
Scheduling decisions consider individual and collective resource requirements, hardware/software/policy
constraints, affinity and anti-affinity specifications, data locality, inter-workload interference,
and deadlines. Node affinity allows you to constrain which nodes your Pod can be scheduled on based
on node labels. Pod affinity and anti-affinity allow you to constrain which nodes your Pod can be
scheduled on based on the labels of Pods already running on that node.""",
        "excerpt": "Learn how Kubernetes assigns Pods to Nodes using scheduling policies and constraints.",
        "site_name": "Kubernetes Docs",
    },
    {
        "url": "https://docs.docker.com/network/drivers/",
        "title": "Docker Networking: Bridge, Host, and Overlay Drivers",
        "content": """Docker's networking subsystem is pluggable using drivers. Several drivers exist by default
and provide core networking functionality. Bridge networks are the default for standalone containers.
When you start Docker, a default bridge network is created automatically and newly started containers
connect to it unless otherwise specified. Host networking removes network isolation between the
container and the Docker host and uses the host's networking directly. Overlay networks connect
multiple Docker daemons together and enable swarm services to communicate with each other.
Macvlan networks allow you to assign a MAC address to a container, making it appear as a physical
device on your network. The Docker daemon routes traffic to containers based on their MAC addresses.
None disables all networking for a container. Network plugins allow you to integrate Docker with
specialized network stacks. Understanding these drivers is essential for designing robust
containerized applications in production.""",
        "excerpt": "A deep dive into Docker networking drivers: bridge, host, overlay, and macvlan.",
        "site_name": "Docker Docs",
    },
    {
        "url": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
        "title": "Kubernetes Deployments: Rolling Updates and Rollbacks",
        "content": """A Deployment provides declarative updates for Pods and ReplicaSets. You describe a desired
state in a Deployment, and the Deployment Controller changes the actual state to the desired state
at a controlled rate. You can define Deployments to create new ReplicaSets, or remove existing
Deployments and adopt all their resources with new Deployments. Rolling updates allow Deployments
to update with zero downtime by incrementally replacing old Pods with new ones. The Deployment
controller ensures that only a certain number of Pods are down while they are being updated. By
default, it ensures that at least 75% of the desired number of Pods are up. If you update a
Deployment while an existing rollout is in progress, the Deployment creates a new ReplicaSet and
starts scaling it up, while rolling back the older ReplicaSet. Rollbacks allow you to revert to
any previous version of a Deployment. Each time a new Deployment is observed, a new revision is
created in order to roll back.""",
        "excerpt": "Master Kubernetes Deployments: rolling updates, rollbacks, and scaling strategies.",
        "site_name": "Kubernetes Docs",
    },

    # ===== Backend / Python =====
    {
        "url": "https://fastapi.tiangolo.com/async/",
        "title": "FastAPI Async and Await: Concurrency Model Explained",
        "content": """FastAPI is based on Starlette and uses Python's asyncio for concurrent request handling.
When you declare a path operation function with async def, FastAPI runs it in an async event loop.
This means it can handle many concurrent requests without threads. When you use regular def instead
of async def, FastAPI runs it in an external thread pool to avoid blocking the event loop. The key
is understanding when to use each: async def for I/O bound operations like database queries and
HTTP requests, def for CPU bound operations. Awaiting coroutines allows the event loop to switch
to other tasks while waiting for I/O. Using blocking calls inside async functions will block the
entire event loop and destroy your concurrency. FastAPI integrates well with async ORMs like
SQLModel and databases with async drivers. Understanding Python's asyncio event loop is fundamental
to writing high-performance FastAPI applications. BackgroundTasks allow deferring work after
returning a response, decoupling slow operations from the request lifecycle.""",
        "excerpt": "Understanding FastAPI's concurrency model: async/await, event loops, and background tasks.",
        "site_name": "FastAPI Docs",
    },
    {
        "url": "https://realpython.com/python-type-checking/",
        "title": "Python Type Hints: From Basics to Advanced Patterns",
        "content": """Type hints were introduced in Python 3.5 via PEP 484. They allow you to annotate function
arguments and return values with types, enabling static analysis tools like mypy and pyright to
catch bugs before runtime. Basic type hints include int, str, float, bool, and None. The typing
module provides generics like List, Dict, Optional, and Union. Python 3.10 introduced the | union
syntax, making Optional[str] equivalent to str | None. TypeVar enables generic functions that
preserve type information. Protocol allows structural subtyping, similar to Go interfaces. Literal
types restrict values to specific constants. TypedDict defines dictionaries with specific key types.
Pydantic uses type hints at runtime for data validation and serialization. Mypy performs static
type checking and can catch a large class of bugs before they reach production. Type narrowing
with isinstance checks helps mypy understand runtime types. Good type coverage dramatically
reduces debugging time and improves code maintainability.""",
        "excerpt": "A comprehensive guide to Python type hints, from basic annotations to advanced generics.",
        "site_name": "Real Python",
    },
    {
        "url": "https://docs.sqlalchemy.org/en/20/orm/session_basics.html",
        "title": "SQLAlchemy 2.0 Session Management and Unit of Work Pattern",
        "content": """SQLAlchemy's Session implements the Unit of Work pattern, tracking all changes to ORM
objects and flushing them to the database in a single transaction. The Session acts as a holding
zone for all the objects you have loaded or associated with it during its lifespan. Objects can be
in one of four states: transient (no association with any Session), pending (added to Session but
not yet flushed), persistent (has a database identity), or detached (previously associated but the
Session was closed). The with Session(engine) as session context manager ensures proper cleanup.
Lazy loading is the default where relationships are loaded on access. Eager loading with joinedload
and selectinload avoids N+1 queries. Session.expire_on_commit refreshes objects after commit so
subsequent access triggers a new SELECT. For web applications, the scoped_session provides a
thread-local Session. Always close sessions explicitly or use context managers to return connections
to the pool. Connection pooling is handled automatically by the Engine.""",
        "excerpt": "Deep dive into SQLAlchemy 2.0 sessions, Unit of Work pattern, and connection pooling.",
        "site_name": "SQLAlchemy Docs",
    },

    # ===== Databases =====
    {
        "url": "https://www.postgresql.org/docs/current/indexes.html",
        "title": "PostgreSQL Index Types: B-tree, GIN, GiST, and BRIN",
        "content": """PostgreSQL supports several index types: B-tree, Hash, GiST, SP-GiST, GIN, and BRIN.
B-tree indexes are the default and work for most use cases including equality and range queries.
They maintain sorted data and support operators like <, >, <=, >=, and =. GIN (Generalized Inverted
Index) is designed for data types that contain multiple component values like arrays and JSONB.
GIN indexes are ideal for full-text search and array containment queries. GiST (Generalized Search
Tree) is useful for geometric data types and full-text search. BRIN (Block Range INdex) is very
small and fast to build, ideal for naturally ordered large tables like time-series data. Partial
indexes cover only a subset of rows, reducing size and improving performance for filtered queries.
Expression indexes index the result of a function or expression rather than a column value directly.
Covering indexes store additional columns to avoid table lookups. The EXPLAIN ANALYZE command shows
whether your query uses an index and how efficiently.""",
        "excerpt": "PostgreSQL index types explained: when to use B-tree, GIN, GiST, and BRIN indexes.",
        "site_name": "PostgreSQL Docs",
    },
    {
        "url": "https://redis.io/docs/manual/patterns/",
        "title": "Redis Caching Patterns: Cache-Aside, Write-Through, and TTL Strategies",
        "content": """Redis is an in-memory data structure store used as a cache, message broker, and database.
The cache-aside pattern (lazy loading) is the most common: the application checks the cache first,
on a miss fetches from the database and populates the cache. Write-through caches update the cache
synchronously when writing to the database, ensuring consistency at the cost of write latency.
Write-behind (write-back) caches write asynchronously, improving write performance but risking
data loss. TTL (Time To Live) is critical for cache freshness: short TTLs reduce stale data but
increase cache misses. Cache stampede occurs when many requests simultaneously miss the cache and
hit the database. Probabilistic early expiration and locking patterns mitigate this. Redis data
structures like Hashes, Sets, and Sorted Sets enable sophisticated caching patterns beyond simple
key-value storage. Redis Cluster provides horizontal scaling. Sentinel provides high availability
with automatic failover. Choosing appropriate eviction policies like LRU and LFU depends on
your access patterns.""",
        "excerpt": "Redis caching strategies: cache-aside, write-through, TTL management, and avoiding cache stampede.",
        "site_name": "Redis Docs",
    },

    # ===== AI / ML / RAG =====
    {
        "url": "https://www.pinecone.io/learn/retrieval-augmented-generation/",
        "title": "Retrieval Augmented Generation (RAG): Architecture and Best Practices",
        "content": """Retrieval Augmented Generation (RAG) combines a retrieval system with a generative language
model to produce accurate, grounded responses. Instead of relying on the model's parametric memory,
RAG retrieves relevant documents from a knowledge base and includes them in the prompt context.
The pipeline consists of indexing (chunking documents and storing embeddings), retrieval (finding
top-k relevant chunks via vector similarity), and generation (passing context to the LLM). Chunking
strategy significantly impacts quality: too small loses context, too large dilutes relevance.
Hybrid retrieval combines dense vector search with sparse BM25 keyword search for better coverage.
Re-ranking with a cross-encoder model improves precision after initial retrieval. Metadata filtering
narrows the search space before vector comparison. Evaluation metrics include faithfulness (is the
answer grounded in the retrieved context?), answer relevance, and context precision. RAG reduces
hallucinations compared to standalone LLMs by anchoring responses to retrieved facts.""",
        "excerpt": "RAG architecture explained: indexing, retrieval, generation, chunking strategies, and evaluation.",
        "site_name": "Pinecone Learn",
    },
    {
        "url": "https://platform.openai.com/docs/guides/embeddings",
        "title": "OpenAI Embeddings: text-embedding-3 Models and Use Cases",
        "content": """OpenAI's embedding models convert text into dense vector representations that capture
semantic meaning. The text-embedding-3-small model produces 1536-dimensional vectors and offers
excellent performance at low cost. text-embedding-3-large produces 3072 dimensions for higher
accuracy tasks. Embeddings enable semantic search where results are ranked by meaning rather than
keyword overlap. Cosine similarity is the standard metric for comparing embeddings: values range
from -1 to 1, with 1 meaning identical and 0 meaning unrelated. Embeddings are also useful for
clustering similar documents, anomaly detection, and classification. The models handle multiple
languages, enabling cross-lingual semantic search. When building a RAG system, embed both the
stored documents and incoming queries using the same model. Dimensionality reduction with PCA
or UMAP enables visualization of embedding spaces. Batching requests reduces API latency for
bulk embedding generation. Always normalize embeddings before computing cosine similarity for
consistent results.""",
        "excerpt": "Guide to OpenAI embedding models: choosing dimensions, use cases, and building semantic search.",
        "site_name": "OpenAI Docs",
    },
    {
        "url": "https://www.anthropic.com/research/prompting",
        "title": "Prompt Engineering: Chain-of-Thought, Few-Shot, and System Prompts",
        "content": """Prompt engineering is the practice of designing inputs to language models to achieve desired
outputs reliably. Chain-of-thought prompting encourages the model to show its reasoning step by
step, dramatically improving performance on complex reasoning tasks. Few-shot examples in the
prompt demonstrate the desired format and behavior. Zero-shot prompting relies on the model's
pretrained knowledge without examples. System prompts establish the model's role, constraints, and
output format. Structured output prompting with JSON schemas ensures parseable responses. Temperature
controls randomness: lower values produce more deterministic outputs, higher values increase
creativity. The ReAct pattern combines reasoning and acting, useful for tool-using agents. Prompt
compression techniques like summarization and selective inclusion manage context window limits.
Constitutional AI principles embedded in system prompts improve safety and alignment. Testing
prompts with diverse inputs and evaluating outputs systematically is essential for production
reliability. Prompt versioning and A/B testing help optimize performance over time.""",
        "excerpt": "Prompt engineering techniques: chain-of-thought, few-shot learning, system prompts, and ReAct.",
        "site_name": "Anthropic Research",
    },
    {
        "url": "https://qdrant.tech/articles/what-is-a-vector-database/",
        "title": "Vector Databases: How HNSW and IVF Indexes Enable Fast ANN Search",
        "content": """Vector databases are specialized systems for storing and querying high-dimensional embedding
vectors. Unlike traditional databases optimized for exact matches, vector databases support
approximate nearest neighbor (ANN) search. HNSW (Hierarchical Navigable Small World) builds a
multi-layer graph where each layer is a subgraph with long-range connections enabling fast
navigation. Search starts at the top layer and greedily descends to find the nearest neighbors.
IVFFlat (Inverted File with Flat) partitions vectors into clusters using k-means and searches
only the nearest clusters. The tradeoff is between search accuracy (recall) and speed. Products
like Pinecone, Weaviate, Qdrant, and Milvus offer managed vector search with filtering. pgvector
is a PostgreSQL extension adding vector types and indexes, ideal for applications already using
Postgres. Choosing between a dedicated vector database and pgvector depends on scale: pgvector
handles millions of vectors well, dedicated databases scale to billions.""",
        "excerpt": "How vector databases work: HNSW, IVF indexes, ANN search, and when to use pgvector vs dedicated DBs.",
        "site_name": "Qdrant Blog",
    },

    # ===== Frontend / React =====
    {
        "url": "https://react.dev/reference/react/useEffect",
        "title": "React useEffect: Data Fetching, Subscriptions, and Cleanup",
        "content": """useEffect is React's mechanism for synchronizing components with external systems. It runs
after every render by default. The dependency array controls when effects re-run: an empty array
means run only once after mount, a specific dependency means run whenever that value changes.
The cleanup function returned from useEffect runs before the next effect and on unmount, preventing
memory leaks. Common use cases include fetching data, subscribing to events, and setting up timers.
The strict mode double-invocation in development helps surface effects that don't clean up properly.
Avoid async functions directly in useEffect; instead define async functions inside or use a wrapper.
React 18's concurrent features may cause effects to run more than once in development. The
useLayoutEffect hook runs synchronously after DOM mutations, useful for reading layout. Custom
hooks extract reusable effect logic. The new React docs recommend using effects sparingly and
prefer event handlers for user-initiated actions. AbortController cancels in-flight fetch requests
during cleanup.""",
        "excerpt": "Complete guide to React useEffect: dependencies, cleanup, data fetching, and common pitfalls.",
        "site_name": "React Docs",
    },
    {
        "url": "https://nextjs.org/docs/app/building-your-application/rendering/server-components",
        "title": "Next.js Server Components: Streaming, Suspense, and the App Router",
        "content": """React Server Components (RSC) run on the server and send HTML to the client without shipping
their JavaScript. This reduces bundle size and enables direct database access without API routes.
The Next.js App Router uses Server Components by default. Client Components are opted into with
the 'use client' directive and are needed for interactivity and browser APIs. The component tree
can mix Server and Client Components: Server Components can import Client Components but not vice
versa. Streaming with Suspense enables progressive rendering, sending HTML chunks as they're ready
rather than waiting for the entire page. Loading UI with loading.tsx automatically wraps page
segments in Suspense. Server Actions allow form submissions and mutations to call server-side code
directly from Client Components. Caching in the App Router operates at multiple levels: request
memoization, Data Cache, Full Route Cache, and Router Cache. Understanding these layers is critical
for correct data freshness behavior.""",
        "excerpt": "Next.js App Router deep dive: Server Components, streaming, Suspense, and caching layers.",
        "site_name": "Next.js Docs",
    },
    {
        "url": "https://www.typescriptlang.org/docs/handbook/2/types-from-types.html",
        "title": "TypeScript Advanced Types: Mapped Types, Conditional Types, and Inference",
        "content": """TypeScript's type system enables powerful type transformations. Mapped types iterate over
union types to create new object types: { [K in keyof T]: T[K] } creates a mapped version of T.
Readonly<T> and Partial<T> are built-in mapped types. Conditional types use extends to select types:
T extends U ? X : Y. The infer keyword extracts type components within conditional types, enabling
patterns like ReturnType<T> which extracts a function's return type. Template literal types combine
string literals: `${Uppercase<T>}` produces uppercase variants. Discriminated unions use a common
literal type property to narrow types exhaustively. The satisfies operator validates without widening
the type. Variadic tuple types enable strongly typed rest parameters. TypeScript's structural typing
means any type with compatible shape is assignable. Declaration merging allows augmenting existing
types and modules. Type guards with is and asserts predicates enable runtime type narrowing with
compile-time benefits.""",
        "excerpt": "TypeScript advanced type system: mapped types, conditional types, infer, and template literals.",
        "site_name": "TypeScript Handbook",
    },

    # ===== DevOps / Cloud =====
    {
        "url": "https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions",
        "title": "GitHub Actions: CI/CD Workflows, Runners, and Secrets Management",
        "content": """GitHub Actions automates software workflows directly in your GitHub repository. Workflows
are defined in YAML files in the .github/workflows directory. A workflow consists of jobs that run
in parallel by default. Each job runs on a runner (GitHub-hosted or self-hosted) and contains steps.
Steps can run shell commands or use actions from the marketplace. Triggers include push, pull_request,
schedule, and workflow_dispatch for manual runs. Secrets are encrypted environment variables stored
in repository or organization settings, accessed via secrets context. Environments add deployment
protection rules and approvals. Reusable workflows reduce duplication across repositories. Matrix
strategy runs jobs across multiple configurations simultaneously, useful for testing across Node
versions or operating systems. Cache action reduces build times by caching dependencies between runs.
Artifacts allow passing files between jobs or downloading build outputs. OIDC tokens enable
passwordless authentication to cloud providers like AWS and GCP.""",
        "excerpt": "GitHub Actions complete guide: workflows, jobs, secrets, matrix builds, and OIDC authentication.",
        "site_name": "GitHub Docs",
    },
    {
        "url": "https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html",
        "title": "AWS S3 Storage Classes: Optimizing Cost and Performance",
        "content": """Amazon S3 offers multiple storage classes designed for different access patterns and cost
requirements. S3 Standard is for frequently accessed data with millisecond latency. S3 Intelligent-
Tiering automatically moves objects between access tiers based on changing access patterns, ideal
when access patterns are unknown. S3 Standard-IA (Infrequent Access) is for data accessed less
frequently but requires rapid access when needed, at a lower storage cost with a retrieval fee.
S3 Glacier Instant Retrieval is for long-lived archive data accessed once a quarter with millisecond
retrieval. S3 Glacier Flexible Retrieval offers retrieval in minutes to hours at lower cost. S3
Glacier Deep Archive is the lowest cost class for long-term retention with 12-hour retrieval. S3
Lifecycle policies automatically transition objects between classes based on age. Replication
copies objects across regions for compliance and disaster recovery. Server-side encryption with
SSE-S3, SSE-KMS, or SSE-C protects data at rest.""",
        "excerpt": "AWS S3 storage classes explained: Standard, Intelligent-Tiering, Glacier, and lifecycle policies.",
        "site_name": "AWS Docs",
    },
    {
        "url": "https://prometheus.io/docs/introduction/overview/",
        "title": "Prometheus Monitoring: Metrics, Labels, and PromQL Queries",
        "content": """Prometheus is an open-source systems monitoring and alerting toolkit. It collects metrics
by scraping HTTP endpoints that expose metrics in the Prometheus text format. The data model uses
time series identified by metric name and key-value label pairs. Counter metrics only increase and
reset on restart, suitable for request counts. Gauges represent values that go up and down like
memory usage. Histograms sample observations and count them in configurable buckets, enabling
percentile calculations. Summaries calculate quantiles over a sliding time window. PromQL is
Prometheus's query language for selecting and aggregating time series. Rate() calculates per-second
rate for counters. Histogram_quantile() estimates percentiles from histograms. AlertManager handles
alerts, routing them to receivers like Slack, PagerDuty, and email. Grafana integrates with
Prometheus for visualization. Service discovery automatically finds scrape targets in dynamic
environments like Kubernetes.""",
        "excerpt": "Prometheus monitoring: metric types, PromQL queries, alerting, and Kubernetes integration.",
        "site_name": "Prometheus Docs",
    },

    # ===== Distributed Systems =====
    {
        "url": "https://martinfowler.com/articles/patterns-of-distributed-systems/raft.html",
        "title": "Raft Consensus Algorithm: Leader Election and Log Replication",
        "content": """Raft is a consensus algorithm designed to be more understandable than Paxos while providing
equivalent guarantees. A Raft cluster has one leader and multiple followers. The leader handles all
client requests and replicates log entries to followers. Leader election uses randomized timeouts:
if a follower doesn't hear from a leader within its timeout, it becomes a candidate and requests
votes. A candidate wins if it receives votes from a majority. Log replication ensures all nodes
have consistent state: the leader sends AppendEntries RPCs to followers, which acknowledge when
they've written to their log. An entry is committed once a majority acknowledges it. Safety is
guaranteed: committed entries are never lost. etcd, used by Kubernetes for cluster state, implements
Raft. CockroachDB and TiKV also use Raft for replication. Understanding Raft helps reason about
distributed database consistency guarantees. The CAP theorem states that distributed systems can
only guarantee two of: Consistency, Availability, and Partition tolerance.""",
        "excerpt": "Raft consensus algorithm: leader election, log replication, safety guarantees, and real-world usage.",
        "site_name": "Martin Fowler",
    },
    {
        "url": "https://www.confluent.io/learn/apache-kafka/",
        "title": "Apache Kafka: Event Streaming, Partitions, and Consumer Groups",
        "content": """Apache Kafka is a distributed event streaming platform. Producers write records to topics,
which are divided into partitions for parallelism and scalability. Each partition is an ordered,
immutable sequence of records. Consumers in a consumer group split partitions among themselves for
parallel processing. Each record has a key, value, and timestamp. Kafka retains records for a
configurable period, enabling replay. The Kafka ecosystem includes Kafka Streams for stream
processing, Kafka Connect for integrations, and ksqlDB for SQL queries over streams. Replication
factor determines how many brokers store each partition for fault tolerance. The leader partition
handles all reads and writes; followers replicate from the leader. ZooKeeper historically managed
cluster metadata, replaced by KRaft mode in recent versions. Kafka's log-structured storage enables
high throughput by sequential disk writes. At-least-once, at-most-once, and exactly-once delivery
semantics have different performance and complexity tradeoffs.""",
        "excerpt": "Apache Kafka architecture: topics, partitions, consumer groups, replication, and delivery semantics.",
        "site_name": "Confluent",
    },

    # ===== Security =====
    {
        "url": "https://owasp.org/www-project-top-ten/",
        "title": "OWASP Top 10: Injection, XSS, IDOR, and Modern Web Security",
        "content": """The OWASP Top 10 is the standard awareness document for web application security. SQL
injection occurs when user input is included in queries without proper sanitization, allowing
attackers to manipulate the database. Parameterized queries and ORMs prevent injection. Cross-Site
Scripting (XSS) injects malicious scripts into web pages viewed by other users. Content Security
Policy headers and output encoding mitigate XSS. Insecure Direct Object References (IDOR) expose
internal implementation objects without access control, enabling unauthorized access. Broken
Authentication stems from weak session management, credential stuffing vulnerabilities, and missing
MFA. Security Misconfiguration is the most common issue: default credentials, unnecessary features
enabled, and missing security headers. Cryptographic failures include using weak algorithms,
storing passwords in plaintext, and transmitting data without TLS. Vulnerable and outdated components
introduce known CVEs. Server-Side Request Forgery (SSRF) tricks servers into making requests to
internal resources.""",
        "excerpt": "OWASP Top 10 web security risks: SQL injection, XSS, IDOR, SSRF, and how to prevent them.",
        "site_name": "OWASP",
    },
    {
        "url": "https://jwt.io/introduction",
        "title": "JWT Authentication: Structure, Signing Algorithms, and Security Pitfalls",
        "content": """JSON Web Tokens (JWT) are a compact, URL-safe means of representing claims between parties.
A JWT consists of three Base64URL-encoded parts separated by dots: header, payload, and signature.
The header specifies the token type and signing algorithm. The payload contains claims like sub
(subject), exp (expiration), and iat (issued at). The signature verifies the token hasn't been
tampered with. HS256 uses a shared secret for symmetric signing; RS256 uses a private key to sign
and public key to verify, enabling stateless verification without the signing key. The 'none'
algorithm vulnerability allows attackers to bypass signature verification on misconfigured servers.
Always validate exp, iss, and aud claims. Store tokens in httpOnly cookies to prevent XSS theft;
localStorage is vulnerable. Short expiration with refresh token rotation limits the window of token
theft. JWKs (JSON Web Key Sets) enable key rotation without downtime. Opaque tokens traded for JWTs
at an authorization server (OAuth2 token introspection) is an alternative pattern.""",
        "excerpt": "JWT deep dive: structure, HS256 vs RS256, security pitfalls, storage strategies, and refresh tokens.",
        "site_name": "JWT.io",
    },

    # ===== Chinese Articles =====
    {
        "url": "https://tech.meituan.com/2022/01/20/transaction-isolation-level.html",
        "title": "数据库事务隔离级别详解：脏读、幻读与串行化",
        "content": """数据库事务的隔离级别是 ACID 特性中隔离性的具体实现。SQL 标准定义了四个隔离级别：
读未提交（Read Uncommitted）允许读取未提交的数据，会产生脏读。读已提交（Read Committed）只能读取
已提交的数据，避免脏读但可能产生不可重复读，即同一事务中两次读取同一行可能得到不同结果。可重复读
（Repeatable Read）保证同一事务中多次读取同一行结果一致，MySQL InnoDB 的默认级别，通过 MVCC
（多版本并发控制）实现。但在标准定义中，可重复读仍可能出现幻读，即同一查询返回不同数量的行。MySQL
InnoDB 通过间隙锁（Gap Lock）解决了可重复读下的幻读问题。串行化（Serializable）是最严格的隔离级别，
所有事务串行执行，完全避免并发问题但性能最差。MVCC 通过保存数据的多个版本实现非阻塞读，读操作不加锁，
写操作加行锁。理解隔离级别对于设计高并发系统和排查数据一致性问题至关重要。""",
        "excerpt": "深入讲解数据库四种事务隔离级别，以及脏读、幻读、不可重复读的原理与解决方案。",
        "site_name": "美团技术博客",
    },
    {
        "url": "https://tech.bytedance.com/articles/distributed-consistency",
        "title": "分布式系统一致性协议：从 Paxos 到 Raft 再到 EPaxos",
        "content": """分布式系统中的一致性问题是核心挑战之一。CAP 定理指出，分布式系统无法同时保证一致性
（Consistency）、可用性（Availability）和分区容错性（Partition tolerance）三者兼得。Paxos 算法由
Leslie Lamport 提出，是第一个被证明正确的分布式共识算法，但其复杂性使得工程实现困难重重。Raft 算法
以可理解性为设计目标，将共识问题分解为领导者选举、日志复制和安全性三个相对独立的子问题。etcd 和
CockroachDB 都基于 Raft 实现。Multi-Paxos 允许多轮 Paxos 在同一个领导者下高效运行，减少消息轮次。
EPaxos（Egalitarian Paxos）进一步优化，允许任何副本在没有冲突时直接提交，提高吞吐量。Zab 协议是
ZooKeeper 使用的原子广播协议，与 Paxos 类似但专为主备架构设计。理解这些协议的本质有助于在工程中
做出正确的架构选择，权衡一致性与可用性。""",
        "excerpt": "深入分析分布式共识协议：Paxos、Raft、Multi-Paxos 和 EPaxos 的原理与工程实践。",
        "site_name": "字节跳动技术博客",
    },
    {
        "url": "https://www.zhihu.com/column/python-async",
        "title": "Python 异步编程详解：asyncio、协程与事件循环",
        "content": """Python 的异步编程模型基于 asyncio 库和协程（coroutine）。协程是可以暂停和恢复执行的函数，
使用 async def 定义，await 表达式用于暂停协程等待异步操作完成。事件循环（Event Loop）是异步编程的核心，
负责调度和执行协程。asyncio.run() 创建并运行事件循环，是推荐的入口点。Task 是协程的包装，允许并发调度
多个协程。asyncio.gather() 并发运行多个协程并等待所有完成。asyncio.create_task() 创建任务后立即调度，
不需要等待。asyncio.sleep() 是异步版本的 time.sleep()，让出控制权给事件循环。异步上下文管理器和
异步迭代器扩展了 async/await 语法。aiohttp 是异步 HTTP 客户端，aiomysql 和 asyncpg 是异步数据库驱动。
理解 GIL（全局解释器锁）对于理解为何 asyncio 适合 I/O 密集型而非 CPU 密集型任务至关重要。multiprocessing
模块可以绕过 GIL 利用多核。""",
        "excerpt": "Python asyncio 完整指南：协程、事件循环、Task、gather 和异步上下文管理器的原理与实践。",
        "site_name": "知乎专栏",
    },
    {
        "url": "https://blog.csdn.net/redis-performance-optimization",
        "title": "Redis 性能优化实战：内存管理、持久化与集群方案",
        "content": """Redis 是单线程的内存数据库，其高性能来源于内存操作和高效的 I/O 多路复用。内存管理是 Redis
运维的核心挑战。maxmemory 配置限制 Redis 最大使用内存，达到上限后根据 maxmemory-policy 决策：
allkeys-lru 驱逐最近最少使用的键，volatile-lru 只驱逐设置了过期时间的键，allkeys-random 随机驱逐。
使用 OBJECT ENCODING 可以查看每个键的内部编码。小整数（0-9999）被共享对象复用节省内存。ziplist 编码
在元素数量少且值较小时自动使用，比普通列表更节省内存。持久化有 RDB（快照）和 AOF（追加日志）两种方式：
RDB 适合备份，AOF 提供更好的数据安全性。Redis Cluster 通过哈希槽（hash slot）实现数据分片，16384 个
槽分配到各节点。主从复制和哨兵（Sentinel）提供高可用。Pipeline 将多个命令批量发送，减少网络往返次数，
显著提升吞吐量。""",
        "excerpt": "Redis 性能优化全攻略：内存淘汰策略、RDB/AOF 持久化、集群分片和 Pipeline 批处理。",
        "site_name": "CSDN 博客",
    },
    {
        "url": "https://juejin.cn/post/frontend-performance",
        "title": "前端性能优化实践：Core Web Vitals、懒加载与 Bundle 分析",
        "content": """前端性能优化是提升用户体验的关键。Google 的 Core Web Vitals 指标包括：LCP（最大内容绘制）
衡量加载性能，应在 2.5 秒内完成；FID（首次输入延迟）衡量交互性，应小于 100ms；CLS（累积布局偏移）
衡量视觉稳定性，应小于 0.1。图片优化是性能提升最显著的手段：使用 WebP 格式减小体积，img 标签的
loading="lazy" 实现懒加载，srcset 和 sizes 提供响应式图片。JavaScript Bundle 优化包括：代码分割
（Code Splitting）通过动态 import() 按需加载，Tree Shaking 去除未使用的代码，使用 webpack-bundle-
analyzer 可视化分析包体积。关键渲染路径优化：CSS 放在 head 避免渲染阻塞，JS 使用 defer 或 async
属性，内联关键 CSS。Service Worker 实现离线缓存和资源预加载。HTTP/2 多路复用减少连接开销。使用
CDN 分发静态资源，配合强缓存策略（Cache-Control: max-age）最大化缓存命中。""",
        "excerpt": "前端性能优化完整指南：Core Web Vitals、图片优化、Bundle 分析和关键渲染路径优化。",
        "site_name": "掘金",
    },
    {
        "url": "https://tech.taobao.com/microservice-gateway",
        "title": "微服务网关设计：限流、熔断与服务发现",
        "content": """微服务架构中，API 网关是所有外部请求的入口，承担路由、认证、限流、熔断等横切关注点。
限流（Rate Limiting）保护后端服务不被过载：令牌桶算法允许突发流量，漏桶算法平滑输出，滑动窗口算法
精确控制时间窗口内的请求数。熔断器（Circuit Breaker）模式防止故障蔓延：关闭状态正常通过请求，开启
状态直接返回错误，半开状态允许少量请求探测服务是否恢复。Hystrix（Netflix）和 Resilience4j 是流行的
熔断器实现。服务发现允许服务动态注册和查找：客户端发现（Eureka）由客户端查询注册中心；服务端发现
（Kubernetes Service）由负载均衡器处理。Nginx 和 Kong 是流行的 API 网关，Envoy 是云原生代理。
gRPC 网关将 HTTP/1.1 请求转换为 gRPC 调用。JWT 验证在网关层统一处理，避免每个服务重复验证。
分布式追踪（OpenTelemetry）在网关注入 Trace ID，实现全链路追踪。""",
        "excerpt": "微服务 API 网关核心设计：令牌桶限流、熔断器模式、服务发现与分布式追踪实践。",
        "site_name": "淘宝技术",
    },

    # ===== Systems / Rust / Go =====
    {
        "url": "https://doc.rust-lang.org/book/ch04-00-understanding-ownership.html",
        "title": "Rust Ownership Model: Borrowing, Lifetimes, and Memory Safety",
        "content": """Rust's ownership system is its most unique feature, enabling memory safety without a garbage
collector. Every value in Rust has a single owner, and when the owner goes out of scope, the value
is dropped. References allow borrowing a value without taking ownership. The borrow checker enforces
two rules: you can have either one mutable reference or any number of immutable references, but not
both simultaneously. This prevents data races at compile time. Lifetimes are annotations that tell
the borrow checker how long references are valid. The compiler infers lifetimes in most cases
through lifetime elision rules. String slices (&str) are references to a portion of a String.
The Clone trait makes deep copies; Copy trait makes stack-allocated types copyable implicitly.
Box<T> allocates heap memory; Rc<T> enables multiple ownership through reference counting; Arc<T>
is the thread-safe version. The Drop trait customizes cleanup logic. Move semantics transfer
ownership by default, unlike C++ where copies happen implicitly.""",
        "excerpt": "Rust ownership explained: borrowing rules, lifetimes, smart pointers, and compile-time memory safety.",
        "site_name": "The Rust Book",
    },
    {
        "url": "https://go.dev/blog/concurrency-patterns",
        "title": "Go Concurrency Patterns: Goroutines, Channels, and the Select Statement",
        "content": """Go's concurrency model is built around goroutines and channels, inspired by Tony Hoare's CSP.
Goroutines are lightweight threads managed by the Go runtime, with initial stacks of only 2KB that
grow as needed. The go keyword launches a goroutine. Channels are typed conduits for communication
between goroutines. Unbuffered channels synchronize sender and receiver; buffered channels allow
sending without immediate blocking up to the buffer capacity. The select statement waits on multiple
channel operations, choosing whichever is ready. The done channel pattern signals cancellation.
The context package provides cancellation propagation across goroutines and API boundaries. sync.WaitGroup
waits for a collection of goroutines to finish. sync.Mutex protects shared state. sync.Once ensures
initialization happens exactly once. The worker pool pattern limits concurrent goroutines. Race
conditions are detected with go run -race. Goroutine leaks occur when goroutines block forever;
always ensure goroutines can terminate.""",
        "excerpt": "Go concurrency patterns: goroutines, channels, select, context cancellation, and worker pools.",
        "site_name": "Go Blog",
    },

    # ===== Additional Topics =====
    {
        "url": "https://web.dev/articles/http-cache",
        "title": "HTTP Caching: Cache-Control, ETags, and Stale-While-Revalidate",
        "content": """HTTP caching reduces server load and improves performance by storing responses locally.
Cache-Control is the primary mechanism with directives like max-age (seconds until stale), no-cache
(must revalidate before use), no-store (never cache), and private (browser-only). ETags are unique
identifiers for resource versions; the browser sends If-None-Match on subsequent requests, and the
server returns 304 Not Modified if unchanged. Last-Modified / If-Modified-Since provides time-based
validation. Stale-while-revalidate serves a stale response immediately while refreshing in the
background, balancing freshness and performance. Immutable directive tells browsers the resource
will never change, avoiding revalidation requests entirely. Service Workers intercept network
requests and implement custom caching strategies. CDN caching adds a network-level cache between
users and origin servers. Cache invalidation is famously hard: URL fingerprinting (content hashing)
enables long cache TTLs by changing URLs when content changes.""",
        "excerpt": "HTTP caching complete guide: Cache-Control, ETags, stale-while-revalidate, and CDN strategies.",
        "site_name": "web.dev",
    },
    {
        "url": "https://graphql.org/learn/",
        "title": "GraphQL vs REST: Queries, Mutations, Subscriptions, and N+1 Problem",
        "content": """GraphQL is a query language for APIs that allows clients to request exactly the data they
need. Unlike REST where each endpoint returns a fixed structure, GraphQL clients specify the shape
of the response. Queries fetch data; mutations modify data; subscriptions push real-time updates.
The schema defines types and their relationships, serving as a contract between client and server.
Resolvers implement data fetching for each field. The N+1 problem occurs when fetching a list and
then making individual queries for each item's relations; DataLoader batches and caches requests
to solve this. GraphQL eliminates over-fetching (REST returning unused fields) and under-fetching
(requiring multiple REST calls). Fragments allow reusable field selections. Directives like @include
and @skip conditionally include fields. Persisted queries cache approved query strings for security
and performance. Federation enables composing multiple GraphQL services into a unified graph.
Tools like Apollo Client manage client-side caching and state.""",
        "excerpt": "GraphQL fundamentals: schema, resolvers, N+1 problem with DataLoader, federation, and REST comparison.",
        "site_name": "GraphQL.org",
    },
]


def clear_articles(db):
    db.execute(__import__('sqlalchemy').text("DELETE FROM article_tags"))
    db.execute(__import__('sqlalchemy').text("DELETE FROM articles"))
    db.commit()
    logger.info(f"🗑️  Cleared all articles")


def seed():
    db = SessionLocal()
    try:
        clear_articles(db)

        logger.info(f"📝 Seeding {len(ARTICLES)} articles...\n")
        success = 0

        for i, data in enumerate(ARTICLES, 1):
            url_str = data["url"]
            url_hash = hash_url(url_str)

            article = Article(
                user_id=USER_ID,
                url=url_str,
                url_hash=url_hash,
                title=data["title"],
                content=data["content"],
                excerpt=data.get("excerpt"),
                site_name=data.get("site_name"),
            )
            db.add(article)
            db.flush()  # 获取 id

            # AI 分析
            existing_tags = [t.name for t in db.query(Tag).all()]
            analysis = analyze_article(article.title, article.content, existing_tags)

            if analysis:
                article.ai_summary = analysis.summary
                for tag_name in analysis.tags:
                    tag = db.query(Tag).filter(Tag.name == tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.add(tag)
                        db.flush()
                    article.tags.append(tag)

            # 向量化
            embedding = __import__('app.services.ai_service', fromlist=['embed_article']).embed_article(article)
            if embedding:
                article.embedding = embedding

            db.commit()
            tags_str = ", ".join(analysis.tags) if analysis else "no tags"
            logger.info(f"[{i:02d}/{len(ARTICLES)}] ✅ {article.title[:55]}")
            logger.info(f"        tags: {tags_str}\n")
            success += 1

        logger.info(f"🎉 Done! {success}/{len(ARTICLES)} articles seeded.")

    except Exception as e:
        logger.exception(f"Seed error: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
