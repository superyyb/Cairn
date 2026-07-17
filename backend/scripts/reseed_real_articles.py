"""
1. Delete all articles (and orphaned tags) for superyy0721@gmail.com
2. Reset Redis rate limit
3. Seed 42 real articles via the API (triggers background AI tagging)

Run from backend directory:
  .venv/bin/python scripts/reseed_real_articles.py
"""
import sys, os, time, requests, redis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models.article, app.models.chat_session, app.models.oauth_account
import app.models.refresh_token, app.models.tag, app.models.tag_merge
from app.core.database import SessionLocal
from app.core.security import create_access_token
from app.core.config import settings
from app.models.article import Article, article_tags
from app.models.tag import Tag
from app.models.tag_merge import TagMerge
from app.models.user import User
from sqlalchemy import text

EMAIL  = "superyy0721@gmail.com"
API    = "http://localhost:8000"
USER_ID = 3

# ── 1. Delete all articles + orphaned tags for user ──────────────────────────
print("── Step 1: Cleaning up existing articles and tags ──")
db = SessionLocal()

# Delete article_tags associations for this user's articles
article_ids = [a.id for a in db.query(Article.id).filter(Article.user_id == USER_ID).all()]
if article_ids:
    db.execute(
        text("DELETE FROM article_tags WHERE article_id = ANY(:ids)"),
        {"ids": article_ids},
    )
    db.execute(
        text("DELETE FROM articles WHERE user_id = :uid"),
        {"uid": USER_ID},
    )
    print(f"  Deleted {len(article_ids)} articles")

# Delete tag_merge history
db.execute(text("DELETE FROM tag_merges"))

# Delete orphaned tags (tags with no remaining article associations)
db.execute(text("""
    DELETE FROM tags
    WHERE id NOT IN (SELECT DISTINCT tag_id FROM article_tags)
"""))

db.commit()
db.close()
print("  Tags and merge history cleaned.")

# ── 2. Reset Redis rate limit ────────────────────────────────────────────────
print("\n── Step 2: Resetting rate limit ──")
r = redis.from_url(settings.redis_url, decode_responses=True)
r.delete(f"rate:article:{USER_ID}")
print("  Rate limit reset.")

# ── 3. Get token ─────────────────────────────────────────────────────────────
token   = create_access_token(subject=USER_ID)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# ── 4. Real articles ─────────────────────────────────────────────────────────
ARTICLES = [
  {
    "url": "https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html",
    "title": "How to do distributed locking",
    "site_name": "martin.kleppmann.com",
    "byline": "Martin Kleppmann",
    "excerpt": "Kleppmann examines the Redlock algorithm and argues it is unsafe for correctness-critical systems, recommending fencing tokens instead.",
    "lang": "en", "length": 3200,
    "content": """As part of research for his book on data-intensive systems, Kleppmann examined the Redlock algorithm from Redis, which purports to implement fault-tolerant distributed locks. The author distinguishes between two primary use cases for locks. Efficiency-based locking prevents redundant work—if a lock fails and two nodes perform identical tasks, the cost impact is minor. Correctness-based locking prevents concurrent processes from corrupting shared state; failure here produces serious consequences like data loss or system inconsistency.

For efficiency purposes, Kleppmann recommends using a simple single Redis instance rather than the complex five-node Redlock setup. However, if correctness depends on the lock functioning reliably, Redlock fails to meet requirements.

The author illustrates a fundamental vulnerability: a client acquires a lock, reads a file, modifies it, and writes it back. However, this approach breaks when the client experiences a prolonged pause—such as garbage collection—causing the lease to expire while the client remains unaware. HBase's documented struggles with stop-the-world GC pauses that 'have sometimes been known to last for several minutes' exemplify this problem.

The solution involves implementing fencing tokens—monotonically increasing numbers issued with each lock acquisition. Storage servers reject write requests containing expired tokens, preventing race conditions. Redlock's first major flaw: it provides no facility for generating fencing tokens and produces random values lacking the required monotonic property.

Kleppmann demonstrates how Redlock fails under realistic conditions. If a node's clock jumps forward, its locks expire prematurely, allowing two clients to simultaneously believe they hold the lock. Similarly, process pauses allow the same race condition. Redlock fundamentally assumes a synchronous system model with bounded network delays, bounded process pauses, and bounded clock errors—assumptions real-world distributed systems frequently violate.

Kleppmann concludes that Redlock fails as both an efficiency optimization and a correctness mechanism. For efficiency-only scenarios: use single-node Redis with clear documentation. For correctness-critical systems: use proper consensus systems like ZooKeeper with enforced fencing token mechanisms.""",
  },
  {
    "url": "https://redis.io/glossary/redis-lock/",
    "title": "Redis Lock (Redlock): Distributed Locking with Redis",
    "site_name": "Redis",
    "byline": None,
    "excerpt": "Redis Lock (Redlock) coordinates exclusive access to shared resources in distributed systems using multiple Redis nodes to prevent deadlock, livelock, and split-brain conditions.",
    "lang": "en", "length": 2100,
    "content": """In a distributed system where multiple processes or threads are accessing shared resources concurrently, it becomes crucial to maintain data consistency and avoid race conditions. Redis, a popular in-memory data store, offers a technique called 'Redis Lock' or 'Redlock' to address these challenges.

Distributed locks play a critical role by providing a mechanism for coordinating access to shared resources. By employing distributed locks, processes can signal their intention to use a particular resource exclusively, ensuring that no other process can access it until the lock is released.

Challenges in distributed locking include: (a) Deadlock — two or more processes waiting for each other to release locks; (b) Livelock — processes continually trying to acquire a lock but failing; (c) Split-Brain Conditions — network partitions causing multiple isolated segments to simultaneously acquire the same lock; (d) Performance Bottlenecks — overuse of locks leading to reduced scalability.

Basic Locking with SETNX: The simplest Redis lock uses the SETNX (SET if Not eXists) command. A process generates a unique identifier (UUID) and attempts to set it as the value of a designated key. If SETNX succeeds, the lock is acquired. This basic mechanism has limitations: if the acquiring process crashes, other processes may be blocked indefinitely without automatic lock expiration.

Adding Expiration and Lock Release: Using SETEX adds TTL to the lock key, ensuring eventual expiration even if a process crashes. A Lua script checks if the lock is still owned by the releasing process before deletion, preventing accidentally releasing locks held by others.

The Redlock Algorithm: Redlock uses multiple Redis instances (nodes) for distributed locking. A client attempts to acquire a lock by sending SET commands to multiple Redis nodes, each with a unique identifier and random token. If the majority of nodes agree on the lock acquisition, the client is granted the lock. Popular implementations include Redsync (Go), Redisson (Java), and redis-py (Python).""",
  },
  {
    "url": "https://stripe.com/blog/rate-limiters",
    "title": "Scaling your API with rate limiters",
    "site_name": "Stripe Blog",
    "byline": "Paul Tarjan",
    "excerpt": "Stripe uses four complementary rate limiters and load shedders implemented with the token bucket algorithm on Redis to protect API availability.",
    "lang": "en", "length": 2800,
    "content": """Availability and reliability are prerequisites for all Stripe product features. When operating a production API, companies must handle unexpected traffic spikes while protecting service quality. Stripe's engineers employ two complementary strategies: rate limiters and load shedders.

A rate limiter controls the rate of requests a user can make. A load shedder makes a decision based on the state of the system (not the user) and sheds load when necessary. Load shedders are a last resort, used primarily during incidents.

Stripe implements four production limiters:

1. Request Rate Limiter: Restricts each user to a maximum number of requests per second. This is 'the most important one to prevent abuse.' This mechanism rejected millions of requests monthly, particularly for test mode scripts running in tight loops.

2. Concurrent Requests Limiter: Addresses resource-intensive endpoints by restricting simultaneous in-progress requests rather than throughput. If a user sends 200 requests over 10 seconds, 20 requests at once creates a very different load than 200 sequential requests. This prevents retry storms that compound server overload.

3. Fleet Usage Load Shedder: Reserves infrastructure capacity for critical operations, automatically rejecting non-essential traffic when system reserves diminish. Divides traffic into two buckets — critical (payment charges) and non-critical (list operations) — ensuring critical APIs always have capacity.

4. Worker Utilization Load Shedder: A final emergency mechanism that sheds traffic by priority during severe incidents. Uses percentage of workers busy: below 90% nothing happens; between 90-95% non-critical requests are rejected; above 95% only the most critical requests proceed.

Implementation uses the token bucket algorithm with Redis infrastructure. Critical safeguards: failing safely if rate limiting code contains bugs, providing actionable error messages (not generic 500s), maintaining kill switches for disabling limiters, and dark launching new limiters to monitor traffic impact before enforcement. Always communicate clearly to users what their limits are, and give them tools to understand their current usage.""",
  },
  {
    "url": "https://blog.cloudflare.com/counting-things-a-lot-of-different-things/",
    "title": "How we built rate limiting capable of scaling to millions of domains",
    "site_name": "Cloudflare Blog",
    "byline": "Julien Desgats",
    "excerpt": "Cloudflare built their edge rate-limiting system using a sliding window algorithm on Twemproxy/memcache clusters, achieving high accuracy with minimal memory at massive scale.",
    "lang": "en", "length": 2600,
    "content": """Rate limiting operates through a straightforward mechanism. Customers define rules matching specific HTTP requests, such as failed login attempts or expensive API calls. Every matching request gets counted per client IP address. Once the counter exceeds the threshold, subsequent requests are blocked from reaching the origin server.

Cloudflare's anycast routing architecture ensures traffic from single IP addresses consistently reaches the same point of presence. This allowed them to create isolated counting systems within each PoP, substantially reducing latency concerns. For data storage, they leveraged existing Twemproxy clusters using consistent hashing to split memcache databases across multiple servers.

For algorithms, different approaches have tradeoffs. The most naive implementation simply increments a counter reset at each sampling period start — but this permits traffic spikes to bypass the limiter. The leaky bucket algorithm balances accuracy with resource efficiency but presents challenges with atomic multi-step operations on memcached.

Cloudflare implemented a sliding window approach. Rather than completely resetting counters, they extrapolate previous counter information to approximate request rates accurately. For a 50 requests-per-minute limit, if 18 requests occurred during the current minute (started 15 seconds ago) and 42 occurred during the previous minute, the rate approximation is: 42 * ((60-15)/60) + 18 = 42 * 0.75 + 18 = 49.5 requests.

Testing on 400 million requests demonstrated effectiveness: only 0.003% of requests were incorrectly allowed or limited, with an average 6% difference between real and approximate rates. The approach offers compelling advantages: minimal memory usage (only two numbers per counter), single INCR command increments, and simple mathematical rate calculations.

They implemented asynchronous increment processing, preventing request slowdowns. When request rates exceed thresholds, stored data alerts all PoP servers to apply mitigation for that client. The rate limiter now handles several billion daily requests and has mitigated attacks reaching 400,000 requests per second to single domains.""",
  },
  {
    "url": "https://martinfowler.com/bliki/CircuitBreaker.html",
    "title": "Circuit Breaker",
    "site_name": "martinfowler.com",
    "byline": "Martin Fowler",
    "excerpt": "The Circuit Breaker pattern wraps remote calls in a protective object that monitors failures, trips open when a threshold is exceeded, and prevents cascading failures across interconnected systems.",
    "lang": "en", "length": 2200,
    "content": """Remote calls between software systems across networks present unique challenges. Unlike local function calls, remote invocations can fail or hang indefinitely, waiting for timeout responses. When multiple callers interact with an unresponsive service, resource exhaustion can trigger cascading failures. Michael Nygard's book 'Release It' popularized the Circuit Breaker pattern as a solution.

The pattern operates through three states. In the closed state, the circuit breaker executes protected calls normally. When failures accumulate beyond a threshold, it transitions to the open state, immediately returning errors without executing calls. A third half-open state allows periodic test calls to verify if the underlying service has recovered.

The basic implementation wraps a supplier function with monitoring logic that distinguishes between temporary and permanent failures. Different error types warrant different thresholds — connection failures might trigger at three occurrences while timeouts require five. Not all errors should trip the breaker; some represent expected operational failures requiring standard handling.

For systems handling substantial traffic, additional considerations emerge. Asynchronous patterns using thread pools or message queues provide better resource management than synchronous blocking calls. Queue-based approaches allow suppliers to consume requests at their own pace, preventing server overload.

Circuit breakers serve as valuable monitoring points where state changes warrant logging and alerting. Operations staff benefit from visibility into breaker status and the ability to manually trip or reset them when necessary. Clients receiving breaker failures must implement appropriate fallback strategies — queuing failed credit card authorizations for later processing or displaying cached data when fresh data retrieval fails.

Netflix's open-source Hystrix library provides sophisticated implementations combining circuit breakers with thread pool limits and latency management for distributed systems.""",
  },
  {
    "url": "https://stripe.com/blog/idempotency",
    "title": "Designing robust and predictable APIs with idempotency",
    "site_name": "Stripe Blog",
    "byline": "Brandur Leach",
    "excerpt": "Networks inevitably produce ambiguous failures; idempotency keys let clients safely retry any request and guarantee that side effects happen exactly once regardless of how many times the request is sent.",
    "lang": "en", "length": 2900,
    "content": """Networks present inherent reliability challenges. When two systems exchange messages, several failure scenarios can occur: initial connection failures before the server receives any request; operations that abort mid-execution leaving work incomplete; or servers that complete processing but disconnect before transmitting results.

These situations create fundamental uncertainty — clients cannot definitively determine whether operations succeeded. This problem represents a cornerstone of distributed systems theory.

The most straightforward approach involves designing server endpoints as idempotent operations, ensuring side effects occur exactly once regardless of repetition frequency. Clients encountering errors can safely retry requests repeatedly until achieving verifiable success.

Consider a DNS provider API: PUT https://example.com/domains/stripe.com/records/s3.stripe.com. This contains all necessary information. Clients can invoke it repeatedly without adverse consequences. HTTP PUT and DELETE verbs are idempotent per specification.

Not all operations fit inherently idempotent patterns. Charging customers — duplicate invocations cause catastrophic problems like double-charging. Idempotency keys address this: clients generate unique identifiers for specific operations, transmitting them alongside payloads. Servers correlate identifiers with internal request states. Upon detecting failures, clients retry using identical keys.

Stripe implements this via the Idempotency-Key header on mutating POST endpoints:
curl https://api.stripe.com/v1/charges -H 'Idempotency-Key: AGJ6FJMkGQIpHUTX' -d amount=2000

Network failures allow safe retries using identical keys, guaranteeing single charges despite connection problems.

Responsible failure handling requires exponential backoff — waiting progressively longer between attempts (2^n where n represents failure count) — and jitter to prevent thundering herd problems where numerous clients synchronize their retry attempts, amplifying server stress. The Stripe Ruby library implements this through automatic retries with idempotency keys using increasing backoff intervals with jitter incorporated.""",
  },
  {
    "url": "https://martinfowler.com/articles/patterns-of-distributed-systems/write-ahead-log.html",
    "title": "Write-Ahead Log",
    "site_name": "Patterns of Distributed Systems",
    "byline": "Unmesh Joshi",
    "excerpt": "The Write-Ahead Log pattern ensures durability by recording every state change in an append-only disk file before applying it to in-memory structures, enabling crash recovery.",
    "lang": "en", "length": 2000,
    "content": """The Write-Ahead Log (WAL), also known as a Commit Log, is a distributed systems pattern designed to ensure data durability and consistency.

Problem: Systems require robust durability guarantees that persist even when server failures occur. The core challenge: 'Once a server agrees to perform an action, it should do so even if it fails and restarts losing all of its in-memory state.'

Solution: Record each state modification as a command within an append-only log file stored on disk. Rather than immediately writing complex data structures to permanent storage, this approach captures all changes sequentially in a persistent file.

This mechanism provides a critical safety net. When a server crashes and loses its in-memory data, it can recover by replaying the commands stored in the write-ahead log. This ensures no committed operations are lost, even during unexpected failures.

By persisting state changes before acknowledging completion to clients, systems achieve strong durability guarantees without requiring immediate flushing of complex in-memory structures. The append-only nature also provides an audit trail of all state changes.

The PostgreSQL documentation elaborates on the performance benefits: WAL results in a significantly reduced number of disk writes, because only the WAL file needs to be flushed to disk to guarantee that a transaction is committed, rather than every data file changed by the transaction. The WAL file is written sequentially, so the cost of syncing the WAL is much less than flushing data pages. Furthermore, when the server is processing many small concurrent transactions, one fsync of the WAL file may suffice to commit many transactions.

WAL also enables on-line backup and point-in-time recovery. By archiving the WAL data, systems can revert to any time instant covered by the available WAL data — simply install a prior physical backup and replay the WAL to the desired point in time.""",
  },
  {
    "url": "https://www.scylladb.com/glossary/log-structured-merge-tree/",
    "title": "Log Structured Merge Tree (LSM Tree)",
    "site_name": "ScyllaDB",
    "byline": None,
    "excerpt": "An LSM tree buffers writes in memory (memtable), flushes to sorted SSTables on disk, and periodically merges files across levels to optimize read performance for write-heavy workloads.",
    "lang": "en", "length": 2100,
    "content": """A log-structured merge-tree (LSM tree) functions as a data structure that efficiently stores key-value pairs for retrieval in disk- or flash-based storage systems. These trees leverage both in-memory and disk-based components to optimize read and write operations, organizing data into multiple levels with progressively larger, sorted components that periodically consolidate through merging.

How LSM Trees Work:

Write Operations: New data initially enters an in-memory structure called a memtable, which typically uses a red-black tree to maintain sorted key-value pairs. This approach enables faster writes compared to direct disk storage.

Flushing to Disk: Once the memtable fills, its contents flush to disk as sorted string tables (SSTables) at Level 0. These structures contain contiguous key-value pairs and participate in the compaction process, which merges and consolidates data across levels to reduce fragmentation and eliminate overlapping entries.

Read Operations: The system first checks a Bloom filter against the memtable. If unsuccessful, it performs a sequential, multi-level search starting from Level 0 and advancing to higher, more organized levels.

Performance Advantages:
- In-memory buffering accelerates write operations
- Batched writes minimize disk I/O by accumulating changes before flushing
- Reduced overwrites enhance performance
- Compaction periodically organizes storage and removes redundancy

B-Trees vs. LSM Trees: B-trees maintain a balanced structure of nodes with multiple keys and child pointers, excelling at both reads and writes with strong range query performance. LSM trees prioritize write-heavy workloads, accepting slightly elevated read latencies in exchange for superior write throughput. B-trees suit file systems and databases requiring frequent modifications, while LSM trees better serve systems handling massive write volumes like Apache Cassandra and RocksDB.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/design-patterns-for-distributed-systems/",
    "title": "The Design Patterns for Distributed Systems Handbook",
    "site_name": "freeCodeCamp",
    "byline": "Tamerlan Gudabayev",
    "excerpt": "A comprehensive guide to essential design patterns for distributed systems: Circuit Breaker, Saga, CQRS, Two-Phase Commit, load balancing, sharding, and write-ahead logs.",
    "lang": "en", "length": 3500,
    "content": """Traditional monolithic applications face significant limitations as they grow: excessive complexity, performance degradation, technology stack inflexibility, and fragility from tightly coupled components. Major tech companies like Netflix, Google, and Facebook originally built monolithic systems but eventually restructured into multiple independent services — the foundation of modern distributed systems.

Distributed systems introduce complexity requiring solutions across seven dimensions: heterogeneity, scalability, openness, transparency, concurrency, security, and failure handling.

Circuit Breaker Pattern: A middleware between two services that monitors service health and prevents cascading failures. Operates through three states: Closed (normal communication), Open (blocking requests after consecutive failures), and Half-Open (limited retry attempts). This design enables systems to 'fail fast' and provide fallback responses, reducing load on struggling services.

Saga Pattern: Addresses distributed transaction challenges by coordinating operations across multiple services with separate databases. Two implementation approaches exist:

Orchestration uses a central service managing workflow and compensating for failures. Suits complex, dynamic workflows requiring centralized control but introduces a potential single point of failure.

Choreography eliminates the central coordinator, allowing services to react to events. Services listen for events and trigger subsequent operations. This decentralized approach prevents tight coupling and avoids single points of failure, though it complicates debugging.

Additional Key Patterns:
- CQRS separates write and read operations, optimizing each independently
- Two-Phase Commit ensures transaction consistency but sacrifices scalability
- Load Balancing distributes traffic across replicated services
- Sharding partitions data and requests across specialized nodes
- Write-ahead logs for durability, leader election for coordination""",
  },
  {
    "url": "https://www.freecodecamp.org/news/a-thorough-introduction-to-distributed-systems-3b91562c9b3c",
    "title": "A Thorough Introduction to Distributed Systems",
    "site_name": "freeCodeCamp",
    "byline": "Stanislav Kozlovski",
    "excerpt": "A foundational overview of distributed systems covering horizontal scaling, replication, sharding, the CAP theorem, and eventual consistency.",
    "lang": "en", "length": 3200,
    "content": """A distributed system comprises a group of computers working together as to appear as a single computer to the end-user. These machines maintain shared state, operate concurrently, and can fail independently without compromising overall uptime.

Systems are distributed primarily by necessity. The primary driver is horizontal scaling — adding more computers rather than upgrading existing hardware. This approach proves substantially cheaper after a certain threshold and avoids the limitations of vertical scaling.

Scaling Challenges — Primary-Replica Replication: To handle increased read traffic, systems employ primary-replica replication, creating read-only database replicas that sync asynchronously with the primary. This increases read capacity but introduces a critical problem: you might insert a new record into the database, immediately afterwards issue a read query for it and get nothing back — because replication happens asynchronously.

Sharding: As write traffic escalates, sharding distributes data across multiple smaller servers (shards), with each holding different records based on predetermined rules. Uniform data distribution is essential to avoid hot spots. The approach enables near-unlimited write scaling but creates new problems: queries using non-sharding keys become inefficient, and complex SQL joins become impractical.

The CAP Theorem: The CAP theorem, proven in 2002, establishes that distributed data stores cannot simultaneously guarantee:
- Consistency: Sequential reads and writes return expected values
- Availability: Every non-failing node responds to requests
- Partition Tolerance: Systems maintain guarantees despite network partitions

Practically, partition tolerance is non-negotiable in distributed systems. When network connections fail between nodes, they face a binary choice: become unavailable or operate with stale information.

Most applications prioritize availability over strong consistency, adopting eventual consistency — the weakest consistency model guaranteeing that eventually, all accesses to that item will return the latest updated value.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/apache-kafka-handbook/",
    "title": "The Apache Kafka Handbook – How to Get Started Using Kafka",
    "site_name": "freeCodeCamp",
    "byline": "Gerard Hynes",
    "excerpt": "Apache Kafka is an open-source event streaming platform; this handbook covers brokers, topics, partitions, producers, consumers, and consumer groups.",
    "lang": "en", "length": 3600,
    "content": """Apache Kafka is an open-source event streaming platform that can transport huge volumes of data at very low latency. Originally developed at LinkedIn to manage real-time data feeds, it's now maintained by the Apache Software Foundation, with adoption among 80% of Fortune 100 companies.

Three primary functions: publishing and subscribing to event streams, storing events in chronological order, and processing streams in real time. Pinterest handles up to 40 million events per second using Kafka.

Core Concepts:

Messages: Consist of keys, values, timestamps, compression types, and optional headers. Keys typically reference entities (users, orders, devices) and determine partition distribution, while values contain event details. Messages are generally small (under 1 MB) and formatted in JSON, Avro, or Protobuf.

Topics: Ordered event logs storing different event categories. Unlike messaging queues, reading from a topic doesn't delete messages, allowing multiple applications to consume the same data repeatedly. Topics are append-only, immutable, and durable, typically retaining messages for seven days by default.

Partitions: Divide topics across multiple cluster nodes, enabling scalability. Messages without keys distribute evenly across partitions in round-robin fashion; messages sharing identical keys consistently route to the same partition, preserving order for that key.

Offsets: Incrementing integers unique within each partition, starting at zero. They identify message position and enable consumers to resume reading from their last processed location.

Brokers: Individual Kafka servers that form a cluster when combined. Multiple brokers enhance scalability and fault tolerance, with partitions distributed across brokers for load balancing.

Replication: Protects against data loss by copying partition data across multiple brokers. A replication factor of three — one leader plus two followers — ensures data survives two broker failures. Followers maintaining leader parity are termed In-Sync Replicas (ISRs).

Consumer Groups: Allow multiple consumer instances to distribute work across topic partitions, with only one consumer per partition assigned within a group.""",
  },
  {
    "url": "https://www.mongodb.com/resources/products/capabilities/database-sharding-explained",
    "title": "Database Sharding: Concepts and Examples",
    "site_name": "MongoDB",
    "byline": None,
    "excerpt": "Sharding is a horizontal scaling technique that distributes a dataset across multiple databases; this article covers ranged, hashed, and entity-based sharding architectures.",
    "lang": "en", "length": 2500,
    "content": """Sharding is a method for distributing a single dataset across multiple databases, which can then be stored on multiple machines. This allows larger datasets to be split into smaller chunks stored in multiple data nodes, increasing total storage capacity. By distributing data across multiple machines, a sharded database can handle more requests than a single machine can.

Sharding is a form of horizontal scaling (scale-out), as additional nodes are brought on to share the load. This contrasts with vertical scaling, which refers to increasing the power of a single machine.

Do You Need Database Sharding? Consider alternatives first:
- Vertical Scaling: Simply upgrade your machine by adding RAM, CPU, or storage
- Specialized Services: Shift specific burdens to other providers
- Replication: For read-focused workloads, replication increases availability and read performance

Sharding is appropriate when your core database contains large amounts of data and requires high read and write volume.

Advantages: Increased read/write throughput, increased storage capacity, high availability through replica sets per shard.

Disadvantages: Query overhead from routing, complexity of administration, increased infrastructure costs.

Sharding Architectures:

Ranged/Dynamic Sharding: Takes a field (shard key) as input and allocates records based on predefined ranges. Requires a lookup table for all queries/writes. Effective shard keys have high cardinality (many possible values) and well-distributed frequency.

Algorithmic/Hashed Sharding: Applies a hash function to records, generating hash values that allocate records to shards. Provides more even distribution without maintaining lookup tables but can increase broadcast operations and make resharding expensive.

Entity-/Relationship-based Sharding: Keeps related data together on a single physical shard, reducing broadcast operations in relational databases.""",
  },
  {
    "url": "https://www.databricks.com/glossary/acid-transactions",
    "title": "What are ACID Transactions?",
    "site_name": "Databricks",
    "byline": None,
    "excerpt": "ACID transactions ensure database reliability through Atomicity, Consistency, Isolation, and Durability — guaranteeing operations complete entirely or not at all.",
    "lang": "en", "length": 1800,
    "content": """ACID transactions represent a fundamental concept in database management, ensuring reliable and consistent data operations. The acronym stands for four key properties:

Atomicity: Ensures that each statement within a transaction executes completely or not at all. This protection prevents data loss and corruption when operations fail mid-process, such as streaming data sources that unexpectedly disconnect. Either the complete operation succeeds, or it fails entirely — there is no partial completion.

Consistency: Maintains data integrity by restricting changes to predefined, predictable patterns. This property prevents errors or corruption from creating unintended consequences for table integrity.

Isolation: Protects concurrent operations by ensuring that simultaneous reads and writes from multiple users don't interfere with one another. Each transaction proceeds as if operating sequentially, despite actual simultaneous execution.

Durability: Guarantees that successfully completed transactions persist permanently, even during system failures or unexpected outages.

The classic banking example illustrates atomicity: money either leaves an account or it doesn't. This all-or-nothing approach prevents the system from entering inconsistent states where one account has been debited but the other hasn't been credited.

These properties provide critical protection for enterprise data operations. Organizations depend on ACID guarantees for financial systems, inventory management, and applications requiring strict data correctness. Without these safeguards, partial writes could leave databases in unrecoverable, inconsistent states.

In contrast, NoSQL databases often embrace the BASE model (Basically Available, Soft state, Eventually consistent) as an alternative, trading strict ACID guarantees for improved scalability and availability.""",
  },
  {
    "url": "https://www.postgresql.org/docs/current/mvcc-intro.html",
    "title": "Introduction to MVCC — PostgreSQL Documentation",
    "site_name": "PostgreSQL Documentation",
    "byline": None,
    "excerpt": "PostgreSQL uses Multiversion Concurrency Control (MVCC) to give each transaction an isolated snapshot, allowing reads and writes to proceed concurrently without blocking.",
    "lang": "en", "length": 1600,
    "content": """PostgreSQL provides a rich set of tools for developers to manage concurrent access to data. Internally, data consistency is maintained by using a multiversion model known as Multiversion Concurrency Control (MVCC).

Each SQL statement sees a snapshot of data (a database version) as it was some time ago, regardless of the current state of the underlying data. This prevents statements from viewing inconsistent data produced by concurrent transactions performing updates on the same data rows, providing transaction isolation for each database session.

The main advantage of using MVCC rather than traditional locking is:
- Locks acquired for querying (reading) data do not conflict with locks acquired for writing data
- Reading never blocks writing
- Writing never blocks reading

PostgreSQL maintains this guarantee even when providing the strictest level of transaction isolation through an innovative Serializable Snapshot Isolation (SSI) level.

While MVCC is the primary concurrency control mechanism, PostgreSQL also offers:
- Table-level locking facilities for applications that don't need full transaction isolation
- Row-level locking facilities for explicit management of particular points of conflict
- Advisory locks (application-defined) for acquiring locks not tied to a single transaction

WAL works in concert with MVCC. Changes to data files must be written only after those changes have been logged — after WAL records have been flushed to permanent storage. This procedure means we don't need to flush data pages to disk on every transaction commit, because in the event of a crash we can recover using the WAL log. WAL results in significantly reduced disk writes because only the WAL file needs to be flushed to guarantee transaction commit rather than every data file changed by the transaction.""",
  },
  {
    "url": "https://www.postgresql.org/docs/current/wal-intro.html",
    "title": "Write-Ahead Logging (WAL) in PostgreSQL",
    "site_name": "PostgreSQL Documentation",
    "byline": None,
    "excerpt": "WAL is PostgreSQL's method for ensuring data integrity after crashes: by recording changes before applying them, it reduces disk writes and enables point-in-time recovery.",
    "lang": "en", "length": 1700,
    "content": """Write-Ahead Logging (WAL) is a standard method for ensuring data integrity. Briefly, WAL's central concept is that changes to data files (where tables and indexes reside) must be written only after those changes have been logged — after WAL records describing the changes have been flushed to permanent storage.

If we follow this procedure, we do not need to flush data pages to disk on every transaction commit, because we know that in the event of a crash we will be able to recover the database using the log: any changes that have not been applied to the data pages can be redone from the WAL records. (This is roll-forward recovery, also known as REDO.)

Key Benefits:

Performance Optimization: WAL results in a significantly reduced number of disk writes, because only the WAL file needs to be flushed to disk to guarantee that a transaction is committed, rather than every data file changed by the transaction. The WAL file is written sequentially, so the cost of syncing the WAL is much less than flushing data pages. This is especially true for servers handling many small transactions touching different parts of the data store. Furthermore, when the server is processing many small concurrent transactions, one fsync of the WAL file may suffice to commit many transactions.

File System Considerations: Because WAL restores database file contents after a crash, journaled file systems are not necessary for reliable storage. In fact, journaling overhead can reduce performance.

Backup and Recovery: WAL makes it possible to support on-line backup and point-in-time recovery. By archiving the WAL data, we can support reverting to any time instant covered by the available WAL data: we simply install a prior physical backup of the database, and replay the WAL just as far as the desired time.""",
  },
  {
    "url": "https://discord.com/blog/how-discord-stores-trillions-of-messages",
    "title": "How Discord Stores Trillions of Messages",
    "site_name": "Discord Engineering Blog",
    "byline": "Bo Ingram",
    "excerpt": "Discord migrated from 177 Cassandra nodes to 72 ScyllaDB nodes, building a Rust-based data service with request coalescing to eliminate hot partition problems while achieving 15ms p99 read latency.",
    "lang": "en", "length": 3100,
    "content": """In 2017, Discord shared their approach to storing billions of messages using Cassandra. Nearly six years later, the platform had grown to 177 nodes managing trillions of messages. However, this growth came with significant challenges.

The Cassandra Problem: Discord's message database exhibited severe performance issues including hot partition problems, where popular channels received disproportionate traffic. Reads are more expensive than writes in Cassandra, and concurrent access to heavily-used channels created bottlenecks affecting the entire cluster. Maintenance required considerable time for garbage collection pauses, performing gossip dance operations (temporarily removing nodes for compaction), and fighting compaction backlogs.

The Solution: ScyllaDB Migration: Discord chose ScyllaDB, a C++-based Cassandra-compatible database offering better performance, faster repairs, stronger workload isolation via its shard-per-core architecture. The critical advantage was eliminating Java's garbage collector, which had historically caused stability issues.

The team built a Rust-based data migration tool that achieved speeds of 3.2 million messages per second, completing the migration in nine days rather than the initially estimated three months.

Data Services with Request Coalescing: To shield the database from traffic spikes, Discord implemented intermediary data services written in Rust. These services employ request coalescing — when multiple users request identical data simultaneously, only one database query executes, with results shared among requesters. Combined with consistent hash-based routing by channel ID, this dramatically reduced database load during viral moments.

Results: Post-migration, Discord reduced their cluster from 177 Cassandra nodes to 72 ScyllaDB nodes while improving performance. Historical message retrieval improved from 40-125ms p99 latency to 15ms. The database remained stable even during massive events like the 2022 World Cup Final.""",
  },
  {
    "url": "https://samwho.dev/load-balancing/",
    "title": "Load Balancing",
    "site_name": "samwho.dev",
    "byline": "Sam Rose",
    "excerpt": "An interactive exploration of round robin, weighted, least connections, and PEWMA load balancing algorithms — showing through simulation why 'it depends' is the only honest answer.",
    "lang": "en", "length": 2400,
    "content": """Web applications that surpass single-server capacity need strategies for increased availability and scalability. Companies deploy applications across multiple servers with a load balancer distributing incoming requests.

The simplest distribution method is round robin load balancing, which sends a request to each server in turn. This works well when servers have equal power and requests require equal processing time. However, real-world scenarios rarely feature uniform conditions: servers may have different hardware, and applications handle diverse request types with varying processing demands.

Weighted round robin assigns weights to servers based on their capacity. More powerful servers receive proportionally more requests. However, determining accurate weights requires careful load testing and human intervention, which proves difficult in practice.

Dynamic weighted round robin calculates weights automatically using latency as a proxy metric. Servers serving requests faster receive more traffic, adapting to performance changes without manual configuration.

Least connections represents a different approach entirely. The load balancer tracks outstanding requests each server has and directs new requests toward those with lowest load. This algorithm performs extremely well regardless how much variance exists and remains simple to implement.

Peak Exponentially Weighted Moving Average (PEWMA) combines techniques from multiple algorithms. It tracks latency from the last N requests with exponentially decreasing scale factors, weighting recent data more heavily. The algorithm multiplies this value by active connections to determine distribution. PEWMA shows marked improvement across the board compared to least connections, particularly at higher percentiles, but sometimes leaves servers underutilized while optimizing for latency.

Round robin achieves the best median latency but performs poorly at higher percentiles. Least connections sacrifices slightly better tail latencies to handle overload situations more gracefully. No algorithm dominates across all scenarios.""",
  },
  {
    "url": "https://use-the-index-luke.com/sql/anatomy/the-tree",
    "title": "The B-Tree Index in SQL Databases",
    "site_name": "Use The Index, Luke",
    "byline": "Markus Winand",
    "excerpt": "B-trees power SQL indexes by maintaining a perfectly balanced hierarchy enabling O(log n) lookups — even a million-row table rarely requires more than five tree levels.",
    "lang": "en", "length": 2300,
    "content": """B-trees form the foundational structure that enables databases to efficiently locate data within indexes. While index leaf nodes are stored arbitrarily on disk, a balanced search tree provides the mechanism for rapid navigation through this seemingly random arrangement.

Structure and Organization: The B-tree consists of three primary node types: leaf nodes containing actual index entries, branch nodes that facilitate navigation, and a root node at the tree's apex. The index leaf nodes are stored in an arbitrary order — the position on the disk does not correspond to the logical position according to the index order.

The tree's organization follows a logical pattern where each branch node entry corresponds to the maximum value within its referenced leaf node. This hierarchical structure continues upward through successive branch layers until all leaf nodes fall under a single root node.

Key Characteristic: Balance: A fundamental property distinguishes B-trees: they maintain uniform depth throughout. The balanced aspect means the distance between root node and leaf nodes is the same everywhere. This uniformity ensures consistent lookup performance regardless of which leaf node contains the target data.

Search Efficiency: Tree traversal begins at the root and processes entries in ascending order. The algorithm follows references downward whenever it encounters a value greater than or equal to the search term, continuing until reaching the appropriate leaf node.

Logarithmic Scalability: The number of entries per branch node forms the base of a logarithm, while tree depth represents the exponent. Real-world databases maximize this principle by storing hundreds of entries per node, meaning each new level supports approximately one hundred times more entries than the previous level. Real-world indexes containing millions of records typically maintain depths of four or five levels.

Automatic Maintenance: Databases automatically maintain B-tree indexes following every insert, update, and delete operation, preserving the tree's balanced structure. This automatic maintenance incurs overhead on write operations but ensures consistent query performance.""",
  },
  {
    "url": "https://netflixtechblog.com/fault-tolerance-in-a-high-volume-distributed-system-91ab4faae74a",
    "title": "Fault Tolerance in a High Volume, Distributed System",
    "site_name": "Netflix Technology Blog",
    "byline": "Ben Christensen",
    "excerpt": "Netflix's API fans out to dozens of systems handling over 1B calls/day; this explains how Netflix uses thread isolation, circuit breakers, semaphores, and graceful fallbacks via Hystrix.",
    "lang": "en", "length": 3000,
    "content": """Netflix's API handles over 1 billion incoming calls daily, which fan out to several billion outgoing calls across dozens of underlying systems. This massive scale makes intermittent failures inevitable. With 30 dependencies each having 99.99% uptime, the combined system would experience 2+ hours of downtime monthly. When a single dependency fails with increased latency, it can saturate all available request threads within seconds.

Netflix's fault tolerance combines multiple approaches:

Network timeouts and retries: Aggressively configured at both network and application levels, with retry logic to handle transient failures.

Separate thread pools per dependency: If one dependency becomes latent and saturates its own threads, the main Tomcat request threads remain available. This also enables parallel execution for performance gains.

Semaphores: Protect against non-network operations like in-memory cache lookups, where threading overhead proves excessive. Also guard fallback functions to prevent cascading failures.

Circuit breakers: Trip when error rates exceed thresholds (such as 50% errors within 10 seconds), rejecting requests to shed load and allow degraded dependencies to recover.

Fallback strategies: When failures occur — timeouts, thread rejection, or circuit breaker trips — the system executes fallbacks: retrieving cached data (even if stale), queuing writes for eventual consistency, reverting to default values, or returning empty responses that UIs can ignore.

Practical Configuration Example: A dependency with median 40ms latency but 99.5th percentile latency might have a network timeout at median-appropriate levels with immediate retries, a thread timeout of 300ms, and a thread pool sized to handle bursts. This ensures timeouts at the DependencyCommand layer remain rare while providing protection against unexpected delays.

Configuration flexibility: Netflix can adjust timeout values, thread pool sizes, and circuit breaker thresholds in real-time as performance characteristics evolve, without risking system-wide failures from misconfiguration.""",
  },
  {
    "url": "https://www.uber.com/blog/microservice-architecture/",
    "title": "Introducing Domain-Oriented Microservice Architecture",
    "site_name": "Uber Engineering",
    "byline": "Adam Gluck",
    "excerpt": "Uber's 2,200 microservices created severe coordination overhead; DOMA addresses this by grouping services into domains with gateways, layered dependencies, and extension mechanisms.",
    "lang": "en", "length": 2900,
    "content": """Uber's engineering team addressed a significant challenge: managing complexity across 2,200 critical microservices. The company's journey began around 2012-2013 when two monolithic services caused availability risks and deployment challenges. Breaking these apart into microservices solved those problems but created new complications at scale.

The Core Problem: Investigating root causes sometimes required examining around 50 services across 12 different teams. Deep service dependencies became difficult to trace, latency issues cascaded through multiple layers, and building simple features meant coordinating across numerous teams. Dependencies became so entangled that services required synchronized deployments despite appearing independent — creating networked monoliths.

The Solution — Domain-Oriented Microservice Architecture (DOMA): Applying established software design principles (Domain-Driven Design, Clean Architecture, SOA) to distributed systems.

DOMA's core components:

Domains: Collections of related microservices grouped by logical functionality. A domain might contain single or dozens of services.

Layer Design: Five layers organizing functionality from general to specific:
- Infrastructure Layer: Organization-wide engineering utilities
- Business Layer: General Uber-wide functionality
- Product Layer: Specific product line logic
- Presentation: Consumer-facing application features
- Edge Layer: External-facing services

Gateways: Single entry points abstracting internal domain complexity. Rather than upstream services depending on multiple internal services, they interact exclusively through gateways. This isolation enables internal reorganization without forcing upstream migrations.

Extensions: Two mechanisms allow teams to extend domain functionality without modifying core code: logic extensions use plugin patterns, data extensions leverage Protobuf's 'Any' functionality.

Results: Uber classified 2,200 microservices into approximately 70 domains, reducing onboarding touchpoints by 25-50%. One early adopter reduced feature prioritization and integration time from three days to three hours.""",
  },
  {
    "url": "https://martinfowler.com/articles/patterns-of-distributed-systems/idempotent-receiver.html",
    "title": "Idempotent Receiver",
    "site_name": "Patterns of Distributed Systems",
    "byline": "Unmesh Joshi",
    "excerpt": "The Idempotent Receiver pattern assigns clients a unique ID so servers can detect and deduplicate retried requests, returning a cached prior response without reprocessing.",
    "lang": "en", "length": 1900,
    "content": """This pattern addresses a fundamental challenge in distributed systems: handling client retries when communication failures occur.

The Core Problem: In networked environments, clients cannot reliably determine whether a server successfully processed their request or if the response was lost during transmission. When faced with this uncertainty, clients typically resend requests to ensure completion. However, if a server had already processed the request and crashed after that, servers will get duplicate requests from the client when it retries.

The Solution: Identify a client uniquely by assigning a unique ID to each client.

The server-side implementation: upon receiving a request, the server checks whether it has previously processed that specific request from the given client. If the server finds a cached response, it returns the saved result without reprocessing. This prevents duplicate processing while ensuring the client receives consistent responses.

By maintaining records of processed requests and their corresponding responses, servers can distinguish between new requests and retries. This approach guarantees idempotence — repeated identical requests produce the same outcome as a single request.

Implementation Considerations:
- Store idempotency keys with their results for a configurable TTL
- Use the client ID plus request identifier as the composite key
- Consider distributed storage for the idempotency key store in multi-server deployments
- Handle in-progress requests carefully to avoid returning partial results on retry

Relationship to Idempotency Keys: Stripe's API implements this pattern via the Idempotency-Key header. The server stores the result keyed by that header value, returning the cached result on retry. This is especially critical for non-idempotent operations like charging a customer — where executing twice would cause real-world harm.""",
  },
  {
    "url": "https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside",
    "title": "Cache-Aside Pattern",
    "site_name": "Microsoft Azure Architecture Center",
    "byline": "Microsoft",
    "excerpt": "The Cache-Aside pattern loads data on demand into a cache from a data store on cache miss and invalidates the cache entry on write, improving read performance while maintaining consistency.",
    "lang": "en", "length": 2200,
    "content": """Load data on demand into a cache from a data store. This approach improves performance and helps maintain consistency between data held in the cache and data in the underlying data store.

Context and Problem: Applications use a cache to improve performance for repeated access to information in a data store. But cached data can't always remain consistent with the data store. Applications should implement a strategy that keeps the data in the cache as up-to-date as possible while handling stale data.

Solution: The Cache-Aside pattern emulates read-through caching:
1. Application attempts to read from the cache
2. Cache miss: application retrieves from the data store
3. Application adds the item to the cache and returns it
4. On write: application writes the change to the data store, then invalidates the corresponding cache item
5. On next read: Cache-Aside retrieves the updated data and re-caches it

Problems and Considerations:

Lifetime: Use TTLs that match access patterns. Too short causes thrashing (constant cache misses). Too long risks stale data. Caching works best for relatively static or frequently read data.

Eviction: Most caches use least-recently-used (LRU) eviction when capacity is exceeded.

Priming the cache: Pre-populate the cache with likely-needed data at startup.

Consistency: The Cache-Aside pattern doesn't guarantee strong consistency between the data store and the cache. An external process can change an item in the data store at any time without updating the cache.

Local vs. Distributed caching: A local cache is private to an application instance. Different instances can have inconsistent copies. In these scenarios, use a shared or distributed caching mechanism like Redis.

When to use: When a cache doesn't provide native read-through/write-through operations; when resource demand is unpredictable and you can't pre-load everything.""",
  },
  {
    "url": "https://samwho.dev/bloom-filters/",
    "title": "Bloom Filters",
    "site_name": "samwho.dev",
    "byline": "Sam Rose",
    "excerpt": "Bloom filters are probabilistic data structures that guarantee no false-negatives while accepting rare false-positives; Google Chrome used one to check malicious URLs with 82% less storage than a full list.",
    "lang": "en", "length": 2100,
    "content": """Bloom filters represent a probabilistic data structure that operates similarly to a Set but with a crucial difference: they cannot guarantee certainty about positive matches. When bloom filters return true it doesn't mean 'yes', it means 'maybe.'

The fundamental mechanism involves an array of bits, initially all set to zero. When adding items, multiple hash functions generate values that determine which bits to set. A key advantage: bloom filters guarantee no false-negatives — they can definitively say an item wasn't added, but cannot guarantee an item was.

Practical Example: Google Chrome's use case for storing malicious link data. By accepting a minimal false-positive rate of 0.0001%, Chrome reduced storage from 20MB to 3.59MB — an 82% reduction.

The false-positive rate grows as more bits become set. The rate is calculated as x^n, where x is the percentage of set bits and n is the number of hash functions used.

Optimization requires balancing several factors. More hash functions improve accuracy but accelerate filling the bloom filter and increase computational costs. The optimal number of hash functions depends on balancing the filter's size against expected items.

A significant limitation: bloom filters cannot remove items. Setting bits to zero risks accidentally unsetting other items' indicators. Counting bloom filters offer removal capability but at substantial memory costs.

Real-world implementations include Akamai's content caching and Google's BigTable distributed database system, which employs bloom filters to determine key presence before disk access, improving read performance substantially by reducing unnecessary storage queries.

Bloom filters exemplify deliberate trade-offs in software engineering, where accepting minor inaccuracies yields substantial practical benefits.""",
  },
  {
    "url": "https://redis.io/docs/latest/develop/data-types/probabilistic/bloom-filter/",
    "title": "Bloom Filters in Redis",
    "site_name": "Redis Documentation",
    "byline": None,
    "excerpt": "Redis provides a native Bloom filter type with configurable error rates and auto-scaling, used for fraud detection, ad deduplication, and username uniqueness checks.",
    "lang": "en", "length": 1800,
    "content": """A Bloom filter is a probabilistic data structure in Redis that enables you to check if an element is present in a set using a very small memory space of a fixed size.

Instead of storing all the items in a set, a Bloom Filter stores only the items' hashed representations, sacrificing some precision. The trade-off: Bloom Filters are very space-efficient and fast. A Bloom filter can guarantee the absence of an item from a set, but it can only give an estimation about its presence.

Use Cases:

Financial fraud detection: 'Has the user paid from this location before?' Use one Bloom filter per user, checked for every transaction. Provides fast response and decreases possibility for transaction to break in case of network partitions.

Ad placement: 'Has the user already seen this ad?' Use a Bloom filter per user storing all viewed ads. The recommendation engine suggests a new product and checks the Bloom filter before showing.

Username uniqueness: 'Has this username already been used?' Check the Bloom filter before the main database.

Example:
BF.RESERVE bikes:models 0.001 1000000
BF.ADD bikes:models "Smoky Mountain Striker"
BF.EXISTS bikes:models "Smoky Mountain Striker" => 1

Filter Parameters:
- False positives rate (error_rate): Decimal between 0 and 1. For 0.1% false positive rate, set to 0.001.
- Expected capacity: Number of items you expect in total. Undersizing causes sub-filter stacking.
- Scaling (EXPANSION): When capacity is reached, a new sub-filter is created. Default expansion is 2.

Memory: 1% error rate requires 7 hash functions and 9.585 bits per item. 0.1% error rate requires 10 hash functions and 14.378 bits per item.

Bloom vs. Cuckoo filters: Bloom filters typically exhibit better performance and scalability when inserting. Cuckoo filters are quicker on check operations and allow deletions.""",
  },
  {
    "url": "https://samwho.dev/hashing/",
    "title": "Hashing",
    "site_name": "samwho.dev",
    "byline": "Sam Rose",
    "excerpt": "Hash functions map arbitrary input to a bounded number; good functions minimize collisions through even distribution, and modern implementations add randomized seeds to prevent HashDoS attacks.",
    "lang": "en", "length": 2300,
    "content": """A hash function accepts input (typically a string) and produces a number within a guaranteed range. The same input always yields identical output. A dummy function returning only 0 would be useless — evaluating hash quality requires understanding collisions (when different inputs produce identical outputs). A good hash function minimizes collision frequency through even distribution across the output range.

The avalanche effect measures how output bits change when input bits flip. Quality functions show approximately 50% bit changes from single input bit modifications.

Hash maps demonstrate practical hash function importance. These data structures store key-value pairs, using hash functions to determine storage locations called buckets. A simple implementation uses a list of lists: the hash function identifies which bucket stores a given key-value pair. With three buckets, the bucket method hashes the key, then uses modulo to select a bucket.

With a poor hash function returning 0 always, all pairs compress into one bucket, requiring full bucket searches. Quality functions reduce searching to roughly 1/N effort, where N equals bucket count.

Real-world testing with 100 million IP addresses: murmur3 produced 1.157% collisions versus stringSum's 99.999%. Testing 466,550 English words: murmur3 at 0.005% collisions against stringSum's 99.5%.

HashDoS Attack: murmur3 faces manufactured collision risks. An attacker can brute-force hash collisions — finding 141 trillion random strings producing identical hashes took only 25 minutes computationally. This threatens HTTP servers using maps for headers — malicious actors can craft requests causing collisions, significantly degrading performance. This 'HashDoS' attack was prevalent in the mid-2000s.

Modern Mitigation: Modern hash functions employ randomization through seeds (sometimes called salts). Murmur3 accepts a seed parameter, randomizing output unpredictably. Programming languages typically generate random seeds at startup, making collision prediction impossible for attackers.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/binary-search-trees-bst-explained-with-examples/",
    "title": "Binary Search Trees (BST) Explained with Examples",
    "site_name": "freeCodeCamp",
    "byline": None,
    "excerpt": "A binary search tree maintains sorted order with average O(log n) lookup, insertion, and deletion; unbalanced trees degrade to O(n), motivating self-balancing variants like AVL and red-black trees.",
    "lang": "en", "length": 2400,
    "content": """A binary search tree (BST) is a specialized data structure where: nodes have a maximum of two children, and the values of its left descendent nodes are less than that of the current node, which in turn is less than the right descendent nodes.

Performance: On average, operations like lookup, insertion, and deletion achieve O(log n) time complexity — each lookup, insertion or deletion takes time proportional to the logarithm of the number of items stored. However, unbalanced trees can degrade to O(n) in worst-case scenarios, which is why self-balancing variants like AVL and red-black trees exist.

Core Operations:

Search: Begins at the root, comparing values and navigating left for smaller values or right for larger ones. Supports both breadth-first search (BFS) and depth-first search (DFS).

Insertion: Follows similar logic to search, finding the appropriate location and adding the new node.

Deletion: Involves three scenarios: removing leaf nodes directly; reconnecting single-child nodes to their grandparent; or replacing two-child nodes with their inorder successor — the smallest value in the right subtree.

Traversals:
- In-order (left-root-right): Visits nodes in ascending sorted order
- Pre-order (root-left-right): Useful for copying the tree
- Post-order (left-right-root): Useful for deleting the tree

Tree Metrics: Height represents the maximum distance from root to leaf. Calculating height recursively: if a node is null, return 0; otherwise return max(height(left), height(right)) + 1.

Augmented BSTs: BSTs can store additional metadata at each node to solve problems like finding the ith smallest element in O(log n) time.""",
  },
  {
    "url": "https://www.geeksforgeeks.org/skip-list/",
    "title": "Skip List — Efficient Search, Insert and Delete",
    "site_name": "GeeksforGeeks",
    "byline": None,
    "excerpt": "A skip list is a probabilistic data structure layering a linked list with express-lane shortcuts, achieving average O(log n) search, insertion, and deletion.",
    "lang": "en", "length": 2000,
    "content": """A skip list is a probabilistic data structure designed to enable faster search, insertion, and deletion in sorted lists. It addresses the O(n) worst-case search time inherent to linear linked list traversal.

Core Concept: The structure works by organizing elements across multiple layers. The bottom layer is a regular linked list, while the layers above contain 'skipping' links for fast navigation. This layered approach mimics an express lane system — upper layers serve as shortcuts, while lower layers contain complete sequential data.

How It Works: When searching for an element, traversal begins at the top layer and proceeds until finding a node whose successor exceeds the target value. The algorithm then descends to lower layers for more granular searching.

Time Complexity Improvements: With two layers and sqrt(n) nodes on the express layer, search complexity reduces to O(sqrt(n)). By adding additional layers, average-case operations achieve O(log n) complexity — comparable to balanced binary search trees but with simpler implementation.

Implementation Mechanism: Skip lists use coin flipping — a probabilistic method that randomly determines how many layers each newly inserted element occupies, ensuring balanced layer distribution without explicit rebalancing.

Advantages:
- Straightforward implementation relative to hash tables and BSTs
- Reduced worst-case likelihood as the list grows
- O(log n) average-case performance
- Used in Redis sorted sets and LevelDB

Limitations:
- Higher memory requirements than balanced trees
- Inability to perform reverse searches
- Poor cache locality compared to arrays""",
  },
  {
    "url": "https://www.geeksforgeeks.org/lru-cache-implementation/",
    "title": "LRU Cache Implementation",
    "site_name": "GeeksforGeeks",
    "byline": None,
    "excerpt": "LRU (Least Recently Used) cache eviction removes the item accessed longest ago; the optimal O(1) implementation combines a hash map with a doubly linked list.",
    "lang": "en", "length": 2100,
    "content": """Least Recently Used (LRU) represents a cache eviction strategy that monitors data usage patterns. When storage capacity is reached, the system removes the item accessed longest ago.

Key Operations:
- LRU Cache(capacity c): Initializes cache with fixed capacity
- get(key): Returns associated value or -1 if absent. Accessed items become marked as most recently used
- put(key, value): Adds new pairs or updates existing ones. Exceeding capacity triggers removal of the least recently used item

Working Example: With capacity-2 cache executing [put(1,1), put(2,2), get(1), put(3,3), get(2)]:
- put(1,1): Cache {1:1}
- put(2,2): Cache {1:1, 2:2}
- get(1): Returns 1, moves key 1 to most recently used. Cache order: 2, 1
- put(3,3): Cache full, removes key 2 (LRU), adds 3. Cache {1:1, 3:3}
- get(2): Returns -1 (evicted)

Implementation Approaches:
- Array-Based: Stores pairs with timestamps, both operations O(n)
- Hashing plus Heap: O(log n) performance
- HashMap with Doubly Linked List (Optimal): O(1) get() and put()

Optimal Solution: Combines hash map with doubly linked list. New entries insert at the list's head (most recently used). Accessing items moves them to the head. When capacity is exceeded, the tail node (least recently used) gets removed, with corresponding hash map entry deleted.

Time Complexity: O(1) for both put() and get()
Space Complexity: O(c) where c is cache capacity

Real-World Applications: Database systems for faster query results, OS page management to minimize page faults, network infrastructure, compiler optimization, and text prediction.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/hash-tables/",
    "title": "Hash Table Explained: What it Is and How to Implement It",
    "site_name": "freeCodeCamp",
    "byline": None,
    "excerpt": "A hash table maps keys to values using a hash function; collision handling via chaining or open addressing keeps average O(1) lookup regardless of table size.",
    "lang": "en", "length": 2200,
    "content": """A hash table, alternatively called a hash map, is a data structure that maps keys to values using a hash function that determines where data should be stored or retrieved within the table structure.

Key characteristics: values are not stored in a sorted order, and there is a necessity to handle potential collisions through chaining — creating linked lists for keys mapping to identical indices.

Implementation Basics: Hash tables distribute key-value pairs across array buckets using the formula: index = f(key, array_size). This involves two steps: calculating a hash value, then applying modulo arithmetic to obtain an index within array bounds.

Practical Example — Character Frequency Counting: For string 'ababcd', a naive approach iterating through 26 letters produces O(26*N) complexity. Using hashing instead achieves O(N) efficiency by mapping each character to an array index directly.

Collision Handling: Since hash table capacity typically exceeds processed data size, collisions prove inevitable. Two primary strategies:

1. Chaining: Each hash table entry contains a linked list. Multiple values mapping to the same key become list elements. Worst-case lookup degrades to O(n) when all keys hash to the same bucket.

2. Open Addressing: When a key slot is occupied, the algorithm searches for the next empty position (linear probing, quadratic probing, or double hashing). This avoids linked list overhead but requires careful load factor management.

Load Factor: The ratio of stored entries to total capacity. A load factor above 0.7 typically triggers resizing (rehashing). Average O(1) lookup is maintained when the load factor remains low.

Applications: Implemented in virtually every programming language's standard library — Python dict, Java HashMap, C++ unordered_map. Used in database indexing, caches, symbol tables in compilers, and deduplication.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/implementing-a-linked-list-in-javascript/",
    "title": "How to Implement a Linked List in JavaScript",
    "site_name": "freeCodeCamp",
    "byline": "Sarah Chima Atuonwu",
    "excerpt": "Linked lists store elements in distributed memory locations connected via pointers, offering flexible insertion and deletion but requiring sequential traversal for search.",
    "lang": "en", "length": 2000,
    "content": """A linked list functions as a linear data structure comparable to an array, but with a key distinction: elements are not stored in a particular memory location or index. Instead, each element — called a node — contains data and a reference (pointer) to the subsequent node.

Nodes have two components: the stored data and a pointer to the next element. The list's entry point is called the head, which references the first node. When the list is empty, the head points to null. The final node also points to null.

Advantages and Disadvantages:

Strengths: Nodes can be efficiently added or removed without restructuring the entire data structure, providing flexibility that arrays lack (no shifting of elements required).

Weaknesses: Search operations are slower since sequential access is required rather than random access. Additionally, linked lists consume more memory due to pointer storage overhead.

Three Variations:
- Singly linked lists: one next pointer
- Doubly linked lists: pointers to both previous and next nodes (enables backwards traversal)
- Circular linked lists: the final node references an earlier node, creating a loop

JavaScript Implementation:

class ListNode {
  constructor(data) {
    this.data = data;
    this.next = null;
  }
}

class LinkedList {
  constructor(head = null) {
    this.head = head;
  }
  size() {
    let count = 0;
    let node = this.head;
    while (node) { count++; node = node.next; }
    return count;
  }
}

Applications: Linked lists are used as the underlying structure for stacks, queues, and hash table chaining (collision handling).""",
  },
  {
    "url": "https://www.learncpp.com/cpp-tutorial/introduction-to-smart-pointers-move-semantics/",
    "title": "Introduction to smart pointers and move semantics",
    "site_name": "LearnCpp.com",
    "byline": "Alex",
    "excerpt": "This tutorial explains the memory management problem that motivates smart pointers, demonstrates RAII, and shows why std::auto_ptr's move-via-copy design was flawed — setting the stage for C++11 move semantics.",
    "lang": "en", "length": 2600,
    "content": """This tutorial addresses a fundamental problem in C++: the difficulty of managing dynamically allocated memory. The article begins by demonstrating how easy it is to accidentally leak memory when using raw pointers, particularly when functions exit early through returns or exceptions.

The core issue is that pointers lack built-in cleanup mechanisms. The solution leverages a key principle: classes automatically execute destructors when objects go out of scope. This foundation enables the RAII (Resource Acquisition Is Initialization) pattern.

A smart pointer class wraps a raw pointer and handles its deallocation automatically. The template class example Auto_ptr1 demonstrates this: when the smart pointer object is destroyed, its destructor automatically deletes the held pointer, guaranteeing cleanup regardless of how the function terminates — even via early return or exception.

The Critical Flaw: Because no explicit copy constructor or assignment operator was defined, C++ generates default versions using shallow copying. This creates situations where multiple smart pointer objects point to the same resource. When one object is destroyed, it deletes the shared resource, leaving other objects with dangling pointers.

Move Semantics Solution: Rather than copying pointers, move semantics transfer ownership from source to destination. The improved Auto_ptr2 class demonstrates this: when assignment occurs, ownership transfers completely — the source pointer becomes null, preventing duplicate deletions.

Historical Context — std::auto_ptr: The standard library's first attempt at standardized smart pointers attempted move semantics through traditional copy operations. This proved problematic because C++ had no formal mechanism to distinguish between copying and moving. The language couldn't prevent pass-by-value scenarios from unexpectedly transferring ownership.

Modern C++ Approach: C++11 formally introduced move semantics as a language feature, enabling proper distinction between copying and moving operations. The standard library now offers: std::unique_ptr (single ownership), std::shared_ptr (shared ownership via reference counting), and std::weak_ptr (non-owning reference).""",
  },
  {
    "url": "https://www.internalpointers.com/post/beginner-s-look-smart-pointers-modern-c",
    "title": "A Beginner's Look at Smart Pointers in Modern C++",
    "site_name": "Internal Pointers",
    "byline": "Triangles",
    "excerpt": "Smart pointers implement RAII to automatically free dynamically allocated memory; unique_ptr gives exclusive ownership, shared_ptr enables reference-counted shared ownership, and weak_ptr breaks circular references.",
    "lang": "en", "length": 2400,
    "content": """Traditional pointers require manual memory management. Developers must remember to deallocate every dynamically allocated object using delete, or face memory leaks. Arrays present additional complexity, requiring delete[] instead of delete. Beyond mechanical challenges, raw pointers create ambiguity regarding ownership — when a function returns a pointer, there's no way to determine who bears responsibility for cleanup.

Smart pointers function as wrapper classes around raw pointers, overloading the -> and * operators to maintain familiar syntax. When a smart pointer exits scope, its destructor automatically deallocates the managed memory. This implements the Resource Acquisition Is Initialization (RAII) pattern.

std::unique_ptr: Provides exclusive ownership of a dynamically allocated resource. No other smart pointers can reference the same object. Only one unique_ptr can own a resource — copying is prohibited through deletion of the copy constructor. When the pointer exits scope, memory automatically deallocates without requiring manual intervention.

std::shared_ptr: Enables shared ownership through reference counting. Multiple shared pointers can reference identical resources. An internal counter tracks references, and deallocation occurs only when the final pointer is destroyed.

Circular References: When two objects reference each other through shared pointers, neither destructor triggers, creating memory leaks. This is solved with weak_ptr.

std::weak_ptr: A non-owning reference to shared pointers that doesn't increment the reference counter. Must be converted to shared pointer via lock() before use. The expired() method checks whether the referenced object still exists. Weak pointers solve circular reference problems — by replacing one shared pointer in a circular relationship with a weak pointer, the circular dependency breaks.

Performance: Smart pointers introduce minimal overhead. shared_ptr's reference counting adds slight cost, but this rarely impacts application performance significantly. Use make_unique and make_shared over raw new for exception safety.""",
  },
  {
    "url": "https://www.cppstories.com/2021/smart-ptr-ref-card/",
    "title": "C++ Smart Pointers Reference Card",
    "site_name": "C++ Stories",
    "byline": "Bartlomiej Filipek",
    "excerpt": "A reference card covering unique_ptr, shared_ptr, and weak_ptr — creation, ownership semantics, custom deleters, function parameter passing, and C++20 atomic smart pointers.",
    "lang": "en", "length": 2500,
    "content": """Smart pointers, available since C++11, form a foundation for secure Modern C++ code. Thanks to RAII (Resource Acquisition Is Initialization), they allow you to work with pointers to allocate memory or other managed objects efficiently.

All three primary smart pointer types reside in the <memory> header. Both unique_ptr and shared_ptr overload the * and -> operators, enabling dereferencing similar to raw pointers. The .get() method provides access to the underlying raw pointer when needed. Legacy auto_ptr is deprecated since C++11 and removed in C++17.

std::unique_ptr: Exclusive ownership — only one pointer can manage an object at any time. The pointer destroys the underlying object when it goes out of scope. Movable but not copyable — this prevents the same resource from being deleted multiple times. Typically occupies a single native pointer's memory footprint.

Creation (prefer make_unique with auto):
auto pObj = make_unique<MyType>(...);

Custom Deleters: Developers can define custom deletion logic through callable objects. The deleter type becomes part of the unique_ptr type signature itself.

std::shared_ptr: Multiple instances can simultaneously manage a single object through reference counting. Deletes the managed object only when the last reference disappears. Both copyable and movable. Typically requires two native pointers: one for the object, another for the control block.

Preferred creation via make_shared() co-locates the control block adjacent to the object, improving memory locality.

Critical concern: Circular references — two pointers referencing each other create memory leaks.

std::weak_ptr: Non-owning references to objects managed by shared_ptr. Doesn't increment the reference counter. Use lock() to get a shared_ptr to access the actual object. Primary use: caching systems and breaking circular reference cycles.

C++20 Additions: Atomic smart pointers for thread-safe shared ownership. make_unique_for_overwrite() and make_shared_for_overwrite() skip value initialization, potentially up to 20x faster for large arrays.""",
  },
  {
    "url": "https://www.learncpp.com/cpp-tutorial/template-classes/",
    "title": "Template Classes in C++",
    "site_name": "LearnCpp.com",
    "byline": "Alex",
    "excerpt": "Template classes generalize container code to work across multiple data types without duplication; the key challenge is that template definitions cannot be split across .h and .cpp files in the usual way.",
    "lang": "en", "length": 2200,
    "content": """The tutorial explains how template classes generalize code for container implementations across multiple data types. The author contrasts two nearly identical classes — IntArray and DoubleArray — that differ only in their contained data type. Templates provide an elegant solution.

The templated Array class demonstrates this approach: 'template <typename T>' precedes the class definition, with T replacing specific types. Member functions defined outside the class require their own template declarations.

Usage: instantiate with Array<int> or Array<double> as needed. The compiler generates separate copies for each type upon demand, only compiling what's actually used.

The File-Splitting Challenge: A significant challenge emerges when splitting template definitions across files. Compilers instantiate templates only where they're used; placing declarations in headers and implementations in separate .cpp files causes linker errors because the template never gets instantiated.

The recommended solution is keeping all template code in headers. Alternative approaches:
- Using .inl (inline) files included at header-end
- Maintaining a separate templates.cpp file with explicit instantiations: 'template class Array<int>;'

Class Template Argument Deduction (CTAD) in C++17: Allows the compiler to deduce template arguments from constructor arguments, so you can write Array arr{5}; instead of Array<int> arr{5};.

Non-type Template Parameters: Templates can also accept values (not just types) as template parameters. A template like template<int size> class Buffer stores a compile-time-fixed array internally, avoiding dynamic allocation entirely.""",
  },
  {
    "url": "https://www.cppstories.com/2021/concepts-intro/",
    "title": "C++20 Concepts — A Quick Introduction",
    "site_name": "C++ Stories",
    "byline": "Bartlomiej Filipek",
    "excerpt": "C++20 concepts establish compile-time constraints on template parameters, improving code clarity and producing dramatically more readable error messages when constraints are violated.",
    "lang": "en", "length": 2600,
    "content": """C++20 introduces concepts as a transformative feature for template programming. They establish compile-time constraints on template parameters, enhancing code clarity, reducing compilation duration, and generating more intelligible compiler error messages.

A concept represents a set of constraints on template parameters evaluated at compile time. Developers can apply these constraints to both class and function templates to regulate function overloads and partial specialization.

The feature relies on two new language keywords: requires and concept. The Standard Library provides predefined concepts.

Simple Example:
template <class T>
concept integral = std::is_integral_v<T>;

This definition leverages the familiar std::is_integral_v type trait to produce boolean outcomes.

More Complex Definition:
template <typename T>
concept ILabel = requires(T v)
{
    {v.buildHtml()} -> std::convertible_to<std::string>;
};

This enforces that type T possesses a member function named buildHtml() returning something convertible to std::string.

Compiler Error Improvements: A significant advantage emerges when constraints are violated. Attempting to instantiate the average function with strings generates a clear error message indicating that const char* fails to satisfy the integral or floating-point requirements. Concepts explicitly state constraint violations instead of producing lengthy, cryptic template instantiation failure messages.

Predefined Concepts: C++20 provides comprehensive standard concepts: core language concepts (integral, floating_point, constructible_from), comparison concepts (equality_comparable, totally_ordered), object-focused concepts (movable, copyable, semiregular), and callable concepts (invocable, predicate).

Requires Expression: The requires expression provides advanced constraint specification. It permits developers to define sophisticated interface requirements such as member function presence, operator support, and return type constraints.""",
  },
  {
    "url": "https://www.cppstories.com/2022/20-smaller-cpp20-features/",
    "title": "20 Smaller yet Handy C++20 Features",
    "site_name": "C++ Stories",
    "byline": "Bartlomiej Filipek",
    "excerpt": "A tour of 20 practical C++20 improvements beyond the big four — including constexpr expansions, designated initializers, source_location, contains(), and safe integral comparison functions.",
    "lang": "en", "length": 2800,
    "content": """C++20 introduced approximately 70 language changes and 80 library features alongside major additions like Modules, Coroutines, Concepts, and Ranges. Beyond these headline features, the standard offers many practical smaller improvements.

Language Features:

Abbreviated function templates: Using auto parameters with concept constraints. Generic lambdas gained explicit template syntax support, enabling declarations like []<typename T>(vector<T> const& vec).

constexpr Expansions: Developers can now use dynamic memory allocation, try-catch blocks, and virtual function calls within constant expressions, allowing std::vector and std::string usage at compile time.

using enum: Introduces enumerator names into scope, reducing verbosity in switch statements.

consteval keyword: Creates immediate functions that must always produce compile-time constants, offering safer alternatives to function-like macros.

Standard Library Features:

Mathematical constants through <numbers> header: compile-time access to pi, e, and other mathematical values.

String operations: starts_with() and ends_with() for prefix and suffix checking.

Associative containers: contains() member functions, replacing the verbose find-and-compare pattern.

Consistent container erasure: erase() and erase_if() functions simplify element removal across various container types.

std::source_location: Provides compile-time source code information — filename, line numbers, function names — without relying on preprocessor macros.

std::cmp_*() functions: Enabling safe integral comparisons between signed and unsigned types, preventing unexpected type conversion results.

Performance optimizations: std::bind_front() for partial function application, heterogeneous lookup support for unordered containers, make_unique_for_overwrite() enabling default initialization without unnecessary zeroing.""",
  },
  {
    "url": "https://www.cppstories.com/2021/filter-cpp-containers/",
    "title": "15 Different Ways to Filter Containers in Modern C++",
    "site_name": "C++ Stories",
    "byline": "Bartlomiej Filipek",
    "excerpt": "A progression through 15 implementations of a container filter — from raw loops through std::copy_if, remove-erase idiom, C++20 ranges, and C++23 ranges::to — illustrating the evolution of idiomatic modern C++.",
    "lang": "en", "length": 2700,
    "content": """This comprehensive guide explores multiple approaches to implementing a filter function in C++, progressing from basic techniques through modern C++23 features. The fundamental challenge: take a container and create a new container with elements matching a specified predicate.

Foundational Approaches:

Raw Loops (C++11): Straightforward range-based for loop with push_back. Leverages automatic return type deduction and move semantics.

std::copy_if: More idiomatic C++ utilizing the standard library algorithm with back_inserter. Communicates intent more clearly through naming.

Remove-Erase Idiom: Copies the container first, then removes unmatched elements using std::remove_if. Requires an initial full copy.

Modern C++20 Features:

std::erase_if: Cleaner alternative to the remove-erase idiom, introduced in C++20.

C++20 Ranges: std::ranges::copy_if with back_inserter provides a simpler interface.

Concept-Based Constraints: Using std::predicate ensures callables accept exactly one argument, preventing accidental misuse.

C++23 Innovations:

views::filter Pipeline: vec | std::views::filter(p) | ranges::to<std::vector>() automatically constructs containers from filtered ranges. This is the most concise approach for ranges-aware code.

std::generator for Lazy Evaluation: C++23 coroutine-based std::generator enables lazy filtering without intermediate allocations, processing elements on-demand — beneficial for streaming or large datasets.

The evolution from raw loops through standard algorithms to ranges demonstrates how C++ continually improves expressiveness while maintaining performance characteristics.""",
  },
  {
    "url": "https://www.fluentcpp.com/2017/01/05/the-importance-of-knowing-stl-algorithms/",
    "title": "The Importance of Knowing STL Algorithms",
    "site_name": "Fluent C++",
    "byline": "Jonathan Boccara",
    "excerpt": "STL algorithms communicate intent more clearly than hand-written loops, provide error-free implementations, and have optimal algorithmic complexity — knowing them is as important as knowing the language's control structures.",
    "lang": "en", "length": 2300,
    "content": """Boccara argues that understanding STL algorithms is essential for writing expressive, maintainable C++ code. He contrasts traditional for-loop implementations with algorithm-based approaches to demonstrate improved readability.

Algorithms vs. For Loops: The article illustrates how std::copy with std::back_inserter communicates intent more clearly than manual iteration. A verbose loop copying employees to a register obscures the operation's purpose, while the algorithm version makes the action explicit through its naming.

std::copy and std::back_inserter: std::copy requires three iterators: input range boundaries and an output iterator. The std::back_inserter adapter automatically handles container resizing by calling push_back, eliminating manual capacity management.

Advantages of Algorithms:
- Expressiveness: Algorithms reveal 'what' operations perform rather than 'how' they're implemented
- Error Prevention: They handle edge cases like off-by-one errors and empty collections automatically
- Quality: Professional implementations tested extensively provide reliable, optimized code
- Optimal Complexity: Algorithms provide best-case performance (e.g., O(n) set operations vs. naive O(n^2) approaches)
- Decoupling: STL design separates algorithms from data structures, enabling independent evolution

Pitfalls to Avoid:

Overusing std::for_each: This algorithm suits operations performing side effects only. For counting, predicates, or comparisons, specialized algorithms like std::count, std::any_of, and std::all_of communicate intent more effectively.

Overlooking Specialized Algorithms: Many developers dismiss unfamiliar algorithms as unnecessarily complex. However, operations like std::set_difference solve real problems elegantly. This algorithm clarifies set operations on sorted collections, replacing confusing manual logic with self-documenting code.

Boccara concludes that mastering STL algorithms represents a worthwhile investment, likening them to fundamental language constructs like if and for. The STL algorithm library is part of the C++ language itself — not knowing it means using only part of what C++ provides.""",
  },
  {
    "url": "https://devblogs.microsoft.com/cppblog/how-we-used-cpp20-to-eliminate-an-entire-class-of-runtime-bugs/",
    "title": "How we used C++20 to eliminate an entire class of runtime bugs",
    "site_name": "Microsoft C++ Team Blog",
    "byline": "Cameron DaCamara",
    "excerpt": "The MSVC team leveraged C++20's consteval to achieve compile-time validation of format specifiers in their diagnostic system, eliminating ~120 pre-existing runtime bug instances.",
    "lang": "en", "length": 2400,
    "content": """The MSVC team leveraged C++20's consteval keyword to solve a long-standing problem with format-specifier validation in their diagnostic error reporting system.

The Problem: The compiler's error infrastructure uses format-specifiers like %1$T and %2$S to display information to users. These specifiers were not type-checked at compile-time, leading to runtime errors when incorrect argument types were passed, arguments were missing entirely, or diagnostic messages were refactored without updating all call sites.

The Three Goals: (1) Validate argument types at compile-time; (2) Minimize changes to existing code; (3) Preserve runtime behavior.

The Solution: While variadic templates and improved constexpr in C++14/17 helped, the breakthrough came with consteval. This keyword guarantees compile-time evaluation and enabled a technique inspired by the fmtlib library.

Using consteval constructors with user-defined types, the team created compile-time checkers that validate format strings and arguments without requiring modifications to call sites. When consteval functions fail at compile-time, compilation simply stops — providing clear, immediate feedback to developers.

Results: The implementation identified approximately 120 instances where diagnostic calls had incorrect argument counts or types. This approach effectively eliminated an entire class of potential runtime bugs while maintaining code readability.

Broader Implications for C++20: consteval differs from constexpr in a critical way — consteval functions MUST be evaluated at compile time, with no runtime fallback. This makes it ideal for validation scenarios where you want to guarantee that certain checks happen before the program ever runs. Combined with user-defined literal types and template metaprogramming, consteval enables a new category of zero-cost abstractions that catch bugs at compile time that previously could only be found at runtime or through extensive testing.""",
  },
  {
    "url": "https://www.freecodecamp.org/news/nosql-databases-5f6639ed9574/",
    "title": "The Basics of NoSQL Databases — and Why We Need Them",
    "site_name": "freeCodeCamp",
    "byline": "Nandhini Saravanan",
    "excerpt": "Explains the limitations of relational databases that led to NoSQL, covers the CAP theorem and BASE model, and surveys four categories of NoSQL databases with real-world use cases.",
    "lang": "en", "length": 2600,
    "content": """Traditional Relational Database Management Systems (RDBMS) organize information into tables with defined schemas, using SQL for querying. However, contemporary applications generate massive volumes of diverse, unstructured data that RDBMS struggles to accommodate.

Limitations of RDBMS: Schema Rigidity — modifying table relationships or adding new columns requires restructuring the entire schema. ACID Property Inflexibility — RDBMS enforces strict ACID properties requiring complete transaction success, perfect consistency, transaction independence, and permanent data preservation.

The CAP Theorem (Brewer's Theorem): Establishes that distributed data stores cannot simultaneously guarantee three attributes: Consistency, Availability, and Partition tolerance. Organizations must prioritize two of the three.

BASE Model: NoSQL databases embrace the BASE model instead: Basically Available (guaranteed responses, even failures), Soft state (system conditions change over time), and Eventual consistency (systems become consistent after halting input changes).

Four Primary NoSQL Categories:

Key-Value Stores (Redis, Riak): Utilize hash tables mapping unique keys to data pointers, enabling high-performance retrieval through simple get, put, and delete operations. Pinterest uses Redis for managing user relationships and board information.

Wide Column Stores (Cassandra, HBase): Organize data within column families — containers holding rows with variable column counts. Spotify leverages Cassandra for storing user profile attributes.

Document Databases (MongoDB): Store semi-structured data using JSON, XML, or BSON formats. Unlike relational systems, document stores don't support joins, instead mapping related documents directly. SEGA uses MongoDB to manage 11 million in-game accounts.

Graph Databases (Neo4j): Represent entities as nodes and associations as relationships. Pre-determined relationships enable faster traversal compared to relational systems requiring multiple operations for complex queries.""",
  },
  {
    "url": "https://www.cppstories.com/2019/02/2lines3featuresoverload.html/",
    "title": "2 Lines Of Code and 3 C++17 Features — The Overload Pattern",
    "site_name": "C++ Stories",
    "byline": "Bartlomiej Filipek",
    "excerpt": "The overload pattern is two lines of template code combining pack expansions, class template argument deduction, and relaxed aggregate initialization to create elegant in-place visitors for std::variant.",
    "lang": "en", "length": 2300,
    "content": """This article examines a powerful yet compact design pattern for working with std::variant in modern C++. The pattern demonstrates how three C++17 language features combine to create an elegant solution for variant visitation.

The Core Pattern (two lines):
template<class... Ts> struct overload : Ts... { using Ts::operator()...; };
template<class... Ts> overload(Ts...) -> overload<Ts...>;

This enables developers to provide separate lambdas in-place for visitation without requiring separate visitor classes.

The Three C++17 Features:

1. Pack Expansions in Using Declarations: The new syntax supports variadic templates through pack expansion in using-declarations. Writing using Ts::operator()...; elegantly replaces what previously required manual expansion across multiple template specializations.

2. Custom Template Argument Deduction Rules: C++17 introduced deduction guides for class templates. The guide allows the compiler to automatically deduce template parameters, eliminating the need for helper functions like make_overloader.

3. Extension to Aggregate Initialization: C++17 expanded aggregate initialization rules to permit initialization of derived types. Previously, you'd need an explicit constructor to pass arguments to base classes.

Practical Example:
std::variant<int, float, std::string> value { "Hello" };
std::visit(overload {
    [](const int& i) { std::cout << "int: " << i; },
    [](const float& f) { std::cout << "float: " << f; },
    [](const std::string& s) { std::cout << "string: " << s; }
}, value);

Evolution in C++20 and C++23: C++20 simplified the pattern further — class template argument deduction was extended to automatically handle aggregates, eliminating the explicit deduction guide. In C++23, consteval improvements enable compile-time checking for missing type handlers.

The pattern exemplifies how C++ language features compound to create elegant abstractions.""",
  },
]

# ── 5. Seed via API ───────────────────────────────────────────────────────────
print(f"\n── Step 3: Seeding {len(ARTICLES)} real articles via API ──")
ok = fail = 0

for i, art in enumerate(ARTICLES, 1):
    # Reset rate limit every 49 articles to avoid hitting the 50/day limit
    if i > 1 and (i - 1) % 49 == 0:
        r.delete(f"rate:article:{USER_ID}")
        print(f"  [Rate limit reset at article {i}]")

    try:
        res = requests.post(f"{API}/api/articles", json=art, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            data = res.json()
            status = "NEW" if data.get("is_new") else "DUP"
            print(f"[{i:02d}] {status} — {art['title'][:65]}")
            ok += 1
        else:
            print(f"[{i:02d}] FAIL {res.status_code} — {art['title'][:65]}: {res.text[:80]}")
            fail += 1
    except Exception as e:
        print(f"[{i:02d}] ERROR — {art['title'][:65]}: {e}")
        fail += 1
    time.sleep(0.3)

print(f"\n[DONE] {ok} seeded, {fail} failed out of {len(ARTICLES)} total.")
print("\nBackground AI jobs (summary + tag generation) are now running.")
print("Check your library in ~2 minutes to see tags appear.")
