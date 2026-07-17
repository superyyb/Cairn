"""
Seed 100 articles for tag generation testing.
Run from backend directory with the venv active:
  .venv/bin/python scripts/seed_articles.py
"""
import sys, os, time, requests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import create_access_token
from app.core.database import SessionLocal
import app.models.article, app.models.chat_session, app.models.oauth_account
import app.models.refresh_token, app.models.tag, app.models.tag_merge
from app.models.user import User

EMAIL   = "superyy0721@gmail.com"
API     = "http://localhost:8000"

# ── 1. Get user & token ──────────────────────────────────────────────────────
db   = SessionLocal()
user = db.query(User).filter(User.email == EMAIL).first()
db.close()

if not user:
    print(f"[ERROR] User {EMAIL} not found. Sign in with Google first to create the account.")
    sys.exit(1)

token   = create_access_token(subject=user.id)
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print(f"[OK] Found user id={user.id}, token created.")

# ── 2. Article definitions ───────────────────────────────────────────────────
ARTICLES = [

  # ── System Design: Locking ─────────────────────────────────────────────────
  {
    "url": "https://engineering.example.com/optimistic-vs-pessimistic-locking",
    "title": "Optimistic vs Pessimistic Locking: When to Use Each",
    "site_name": "Engineering Blog",
    "content": """Optimistic locking assumes conflicts are rare and allows concurrent reads without locks, validating at commit time using a version field or timestamp. If a conflict is detected, the transaction is retried. This approach shines in read-heavy workloads where writes are infrequent, avoiding the overhead of holding locks during long-running operations.

Pessimistic locking, by contrast, acquires a lock as soon as a resource is accessed, blocking all other transactions until the lock is released. It's appropriate when conflicts are likely or when the cost of a retry is high — for example, in financial systems where double-spending must be prevented at the database level.

A common mistake is applying pessimistic locking to read-heavy APIs. This causes unnecessary contention and dramatically reduces throughput. The right heuristic: if P(conflict) is low, use optimistic; if data integrity is critical and conflicts are frequent, use pessimistic.

In Postgres, `SELECT FOR UPDATE` implements pessimistic locking, while optimistic locking is typically implemented at the application layer with a `version` integer column and a conditional `UPDATE WHERE version = ?` check.""",
    "excerpt": "A deep dive into optimistic and pessimistic locking strategies, with guidance on when to use each in production systems.",
    "byline": "Staff Engineer, Platform",
    "length": 850,
  },
  {
    "url": "https://engineering.example.com/distributed-locks-redis",
    "title": "Implementing Distributed Locks with Redis: Redlock and Pitfalls",
    "site_name": "Engineering Blog",
    "content": """Distributed locks are necessary when multiple processes across different machines must coordinate access to a shared resource. Redis is a popular choice due to its atomic operations and low latency. The simplest approach uses `SET key value NX PX ttl` — set only if not exists, with a TTL to prevent deadlocks.

The Redlock algorithm, proposed by Antirez, extends this to a cluster of 5 independent Redis nodes. A lock is considered acquired only if it succeeds on a majority (3+) of nodes within a validity time window. This prevents a single node failure from causing split-brain scenarios.

However, Redlock has well-known criticisms from Martin Kleppmann: it relies on timing assumptions that break under GC pauses, clock drift, or network delays. In systems requiring strict safety guarantees (e.g., payment processing), fencing tokens — monotonically increasing numbers attached to lock grants — are the correct approach.

For less critical coordination tasks (rate limiting, job deduplication), simple Redis-based locks with short TTLs are pragmatic and effective.""",
    "excerpt": "How to implement distributed locks using Redis, the Redlock algorithm, fencing tokens, and when not to use them.",
    "byline": "Infrastructure Engineer",
    "length": 920,
  },
  {
    "url": "https://engineering.example.com/database-row-locking",
    "title": "Row-Level Locking in PostgreSQL: Internals and Best Practices",
    "site_name": "Engineering Blog",
    "content": """PostgreSQL implements row-level locking through its multi-version concurrency control (MVCC) system combined with explicit lock modes. When a transaction modifies a row, it creates a new version (tuple) rather than overwriting in place, allowing readers to see a consistent snapshot without blocking.

Explicit row locks are acquired with `SELECT FOR UPDATE`, `SELECT FOR NO KEY UPDATE`, `SELECT FOR SHARE`, and `SELECT FOR KEY SHARE`. The hierarchy determines compatibility — two `FOR SHARE` locks on the same row are compatible, while `FOR UPDATE` conflicts with everything.

A common source of deadlocks in PostgreSQL is acquiring row locks in inconsistent order. For example, Transaction A locks row 1 then row 2, while Transaction B locks row 2 then row 1. PostgreSQL detects the cycle and aborts one transaction. The fix is always to acquire locks in a deterministic order (e.g., sorted by primary key).

Advisory locks offer another mechanism: `pg_try_advisory_lock(key)` acquires an application-defined lock identified by a 64-bit integer, completely outside the table locking mechanism. These are ideal for coordinating background jobs.""",
    "excerpt": "Deep dive into PostgreSQL row-level locking, MVCC, lock modes compatibility, deadlock prevention, and advisory locks.",
    "byline": "Database Engineering",
    "length": 980,
  },

  # ── System Design: Concurrency ─────────────────────────────────────────────
  {
    "url": "https://concurrency.example.com/mutex-semaphore-monitor",
    "title": "Mutex, Semaphore, and Monitor: Core Concurrency Primitives Explained",
    "site_name": "Concurrency Deep Dives",
    "content": """A mutex (mutual exclusion) is a binary lock — only one thread can hold it at a time. It's used to protect a critical section from concurrent access. The thread that acquires the mutex must release it; no other thread can do so on its behalf.

A semaphore generalizes the mutex with a counter. A counting semaphore allows up to N threads to hold it simultaneously. Binary semaphores (count = 1) behave like mutexes but with a crucial difference: any thread can release a semaphore, not just the one that acquired it — making them useful for signaling between threads.

A monitor is a higher-level abstraction combining a mutex with one or more condition variables. Java's `synchronized` keyword and C++'s `std::condition_variable` implement monitor semantics. The `wait()` operation atomically releases the mutex and suspends the thread; `notify()` wakes a waiting thread and it re-acquires the mutex before proceeding.

Choosing between them: use a mutex for simple mutual exclusion, a semaphore for resource counting or signaling, and a monitor when threads need to wait for a condition to become true while holding a lock.""",
    "excerpt": "Clear explanation of mutex, semaphore, and monitor concurrency primitives with use cases and when to choose each.",
    "byline": "Systems Programmer",
    "length": 870,
  },
  {
    "url": "https://concurrency.example.com/lock-free-data-structures",
    "title": "Lock-Free Data Structures: CAS, ABA Problem, and Practical Use",
    "site_name": "Concurrency Deep Dives",
    "content": """Lock-free data structures allow multiple threads to operate concurrently without mutual exclusion, using atomic CPU instructions instead. The fundamental primitive is Compare-And-Swap (CAS): atomically compare a memory location to an expected value and, if equal, replace it with a new value.

A lock-free stack uses CAS on the head pointer. Push: read head, create new node pointing to head, CAS head from old to new. If CAS fails (another thread modified head), retry. This is a standard spin-retry loop.

The ABA problem is a subtle bug: thread T1 reads value A, T2 changes A→B→A, T1's CAS succeeds even though the list changed. Solutions include tagged pointers (embed a version counter in the pointer) or hazard pointers (mark pointers in use before dereferencing).

Java's `java.util.concurrent` package provides production-grade lock-free structures: `ConcurrentLinkedQueue`, `AtomicReference`, and `LongAdder`. C++ provides `std::atomic<T>` with explicit memory ordering (`memory_order_acquire`, `memory_order_release`, `memory_order_seq_cst`).""",
    "excerpt": "How lock-free data structures work using CAS, the ABA problem, tagged pointers, and practical examples in Java and C++.",
    "byline": "Performance Engineering",
    "length": 950,
  },
  {
    "url": "https://concurrency.example.com/thread-pool-design",
    "title": "Thread Pool Internals: Work Stealing, Queue Design, and Sizing",
    "site_name": "Concurrency Deep Dives",
    "content": """A thread pool maintains a fixed number of worker threads that pull tasks from a shared queue, avoiding the overhead of thread creation/destruction per task. The core components are: the task queue (typically a bounded `BlockingQueue`), the worker threads, and rejection policies for when the queue is full.

Work-stealing pools (like Java's `ForkJoinPool`) give each thread its own deque. Threads push/pop from their own deque's tail (LIFO for cache locality). When idle, threads steal from other threads' deque heads (FIFO), balancing load without centralized coordination.

Queue sizing matters: too small and tasks are rejected under load; too large and memory pressure builds up. `LinkedBlockingQueue` is unbounded (dangerous); `ArrayBlockingQueue` is bounded. A common pattern is a bounded queue with a `CallerRunsPolicy` rejection handler — the submitting thread executes the task itself, naturally providing backpressure.

Thread count heuristics: CPU-bound tasks → N_cpu threads; I/O-bound tasks → N_cpu * (1 + wait_time / compute_time). Profiling actual blocked time is more reliable than formulas.""",
    "excerpt": "Deep dive into thread pool internals: work stealing, queue design, sizing heuristics, and backpressure strategies.",
    "byline": "JVM Internals",
    "length": 910,
  },

  # ── System Design: Race Conditions ─────────────────────────────────────────
  {
    "url": "https://systems.example.com/race-condition-patterns",
    "title": "Race Condition Patterns: TOCTOU, Double-Checked Locking, and Fixes",
    "site_name": "Systems Engineering",
    "content": """A race condition occurs when the program's output depends on the relative ordering of uncontrolled events. The Time-Of-Check to Time-Of-Use (TOCTOU) race is classic: check if a file exists, then open it — between check and open, another process deletes the file. Fix: use atomic syscalls like `O_CREAT | O_EXCL` to combine check and create.

Double-checked locking is a notorious pattern for lazy initialization: check if an object is null without a lock, then check again inside a lock before creating. In Java without `volatile`, this is broken because the JIT can reorder the write to the reference with initialization. With `volatile`, it works; with `std::atomic` in C++, it requires `memory_order_acquire`/`memory_order_release`.

Database race conditions manifest as lost updates: two transactions read balance=100, both subtract 50, both write 50 — net result 50 instead of 0. Fixes: pessimistic lock (`SELECT FOR UPDATE`), optimistic locking (version column), or atomic update (`UPDATE SET balance = balance - 50 WHERE balance >= 50`).

Detection tools: ThreadSanitizer (TSan) instruments memory accesses to detect races at runtime; Helgrind (Valgrind) detects lock order violations; Java's `FindBugs` / `SpotBugs` detect common patterns statically.""",
    "excerpt": "Common race condition patterns including TOCTOU, double-checked locking, database lost updates, and detection tools.",
    "byline": "Security & Reliability",
    "length": 900,
  },
  {
    "url": "https://systems.example.com/memory-visibility-happens-before",
    "title": "Memory Visibility and Happens-Before: The Foundation of Concurrent Correctness",
    "site_name": "Systems Engineering",
    "content": """Modern CPUs and compilers reorder instructions for performance. Without explicit synchronization, thread A writing a value is not guaranteed to be visible to thread B — even if A wrote before B read in wall-clock time. The happens-before relationship defines when writes are visible.

In Java, the Java Memory Model defines happens-before through: volatile writes happen-before reads of the same variable; a monitor unlock happens-before a subsequent lock; `Thread.start()` happens-before any action in the started thread.

In C++11+, `std::atomic` operations with `memory_order_seq_cst` (the default) establish a single total order across all atomic operations in all threads. Weaker orderings (`relaxed`, `acquire`, `release`) allow more reordering for performance — `release` on a write pairs with `acquire` on a read to establish happens-before between specific operations.

Practical rule: if two threads access the same variable and at least one writes, there must be a happens-before relationship (via lock, atomic, or fence) or it's a data race — undefined behavior in C++, unpredictable in Java.""",
    "excerpt": "How memory visibility works in concurrent systems, happens-before relationships, Java Memory Model, and C++ memory ordering.",
    "byline": "Compiler & Runtime Research",
    "length": 930,
  },

  # ── System Design: Deadlocks ───────────────────────────────────────────────
  {
    "url": "https://systems.example.com/deadlock-detection-prevention",
    "title": "Deadlock Detection, Prevention, and Avoidance: A Practical Guide",
    "site_name": "Systems Engineering",
    "content": """Deadlock requires four conditions simultaneously (Coffman conditions): mutual exclusion (resources can't be shared), hold-and-wait (process holds resources while waiting for more), no preemption (resources can't be forcibly taken), and circular wait (circular chain of processes, each waiting for the next).

Prevention eliminates one condition. Lock ordering prevents circular wait: always acquire locks in a consistent global order. In practice this means sorting lock objects by identity hash code or database row ID before acquiring.

Detection uses a resource allocation graph — if a cycle exists, deadlock is present. Databases run periodic deadlock detectors; PostgreSQL detects cycles and kills the youngest transaction (configurable via `deadlock_timeout`, default 1 second).

Avoidance (Banker's algorithm) requires knowing maximum resource needs in advance — impractical for most systems. Timeout-based detection is the pragmatic alternative: if a lock isn't acquired within N ms, abort and retry with exponential backoff and jitter to prevent livelock.""",
    "excerpt": "Practical guide to deadlock detection, prevention with lock ordering, database deadlock handling, and timeout-based avoidance.",
    "byline": "Database Reliability",
    "length": 875,
  },

  # ── System Design: Database ────────────────────────────────────────────────
  {
    "url": "https://db.example.com/acid-properties-deep-dive",
    "title": "ACID Properties Deep Dive: Atomicity, Isolation Levels, and Trade-offs",
    "site_name": "Database Engineering",
    "content": """ACID — Atomicity, Consistency, Isolation, Durability — defines the guarantees of database transactions. Atomicity means all operations in a transaction succeed or all are rolled back; there's no partial commit. WAL (Write-Ahead Logging) implements this by recording changes before applying them.

Isolation levels define what anomalies are permitted. Read Uncommitted allows dirty reads; Read Committed prevents dirty reads but allows non-repeatable reads; Repeatable Read prevents those but allows phantom reads; Serializable eliminates all anomalies. PostgreSQL's default is Read Committed; MySQL's InnoDB default is Repeatable Read.

Serializable Snapshot Isolation (SSI) achieves true serializability without locking by detecting write-write and read-write conflicts between concurrent transactions and aborting one. PostgreSQL implemented SSI in version 9.1, making it the only major RDBMS with a non-locking serializable mode.

Durability is guaranteed by flushing the WAL to disk before acknowledging a commit. `fsync=off` in Postgres disables this for performance at the cost of data loss on crash — never use in production.""",
    "excerpt": "Deep dive into ACID transaction properties, isolation levels, anomalies, PostgreSQL SSI, and durability guarantees.",
    "byline": "Database Internals",
    "length": 960,
  },
  {
    "url": "https://db.example.com/cap-theorem-practical",
    "title": "CAP Theorem in Practice: Beyond the Trilemma",
    "site_name": "Database Engineering",
    "content": """The CAP theorem states that a distributed system can provide at most two of three guarantees: Consistency (every read reflects the latest write), Availability (every request receives a response), and Partition tolerance (the system continues operating during network partitions).

Since network partitions are inevitable in distributed systems, the real choice is between CP (consistency during partitions, potentially refusing requests) and AP (availability during partitions, potentially returning stale data). HBase and Zookeeper are CP; Cassandra and DynamoDB are AP.

CAP has important nuances. "Consistency" in CAP means linearizability, not ACID consistency. "Availability" requires every non-failing node to respond — a system that rejects requests during partitions is CP, not CA. There is no CA distributed system.

PACELC extends CAP to capture the latency-consistency trade-off during normal operation (not just partitions): even when the network is healthy, you trade consistency for lower latency. This explains why eventually-consistent systems like DynamoDB are faster — they don't wait for all replicas to acknowledge writes.""",
    "excerpt": "Practical understanding of CAP theorem, CP vs AP systems, common misconceptions, and the PACELC extension.",
    "byline": "Distributed Systems",
    "length": 910,
  },
  {
    "url": "https://db.example.com/database-indexing-btree-hash",
    "title": "Database Indexing Internals: B-Tree, Hash, and GIN Indexes",
    "site_name": "Database Engineering",
    "content": """B-Tree indexes are PostgreSQL's default and support equality, range queries, and sorting. The tree stays balanced through splits and merges, maintaining O(log n) lookup. Pages are 8KB; a million-row table needs only 3-4 levels of B-Tree, meaning 3-4 disk reads for any lookup.

Hash indexes store a hash of the indexed column, supporting only equality comparisons (`WHERE col = val`). They're smaller than B-Trees and offer O(1) average lookup, but don't support range queries, sorting, or partial matches. Prior to PostgreSQL 10, hash indexes weren't WAL-logged and needed to be rebuilt after crashes.

GIN (Generalized Inverted Index) indexes are used for composite values: arrays, JSONB, and full-text search. A GIN index maps each element to the set of rows containing it — ideal for `@>` (contains) and `@@` (text search match) operators. They're large and slow to build but fast to query.

Partial indexes (`CREATE INDEX ON orders(status) WHERE status = 'pending'`) index only rows matching a condition, dramatically reducing size and maintenance overhead when queries consistently filter on a high-selectivity predicate.""",
    "excerpt": "How B-Tree, Hash, and GIN database indexes work internally, with guidance on when to use each type.",
    "byline": "Query Performance",
    "length": 945,
  },
  {
    "url": "https://db.example.com/database-sharding-strategies",
    "title": "Database Sharding: Range, Hash, and Directory-Based Strategies",
    "site_name": "Database Engineering",
    "content": """Sharding horizontally partitions data across multiple database instances. Range sharding assigns rows to shards by key ranges (user IDs 1-1M on shard 1, 1M-2M on shard 2). It's simple and supports range queries across shards, but creates hotspots when access patterns are skewed to recent data (e.g., time-series IDs).

Hash sharding applies a hash function to the shard key and assigns rows to shards by hash(key) % N. It distributes load evenly but destroys range query performance — a query for users 1-100 must hit all shards. Consistent hashing mitigates resharding cost by only reassigning key(s)/N keys when adding a shard.

Directory-based sharding maintains a lookup table mapping keys to shards, allowing arbitrary placement and easy rebalancing. The lookup table itself becomes a bottleneck and single point of failure unless replicated and cached aggressively.

Cross-shard joins and transactions are the primary pain point. Designing shard keys to co-locate frequently joined entities (e.g., shard by tenant ID so all tenant data lives on one shard) eliminates most cross-shard operations.""",
    "excerpt": "Database sharding strategies: range, hash, consistent hashing, and directory-based sharding with trade-offs.",
    "byline": "Data Platform",
    "length": 930,
  },
  {
    "url": "https://db.example.com/sql-vs-nosql-decision",
    "title": "SQL vs NoSQL: A Decision Framework Beyond the Hype",
    "site_name": "Database Engineering",
    "content": """The SQL vs NoSQL question is often framed as a performance debate, but the real differentiator is the data model. Relational databases excel when data has complex relationships, schemas are stable, and transactional consistency is required. NoSQL databases optimize for specific access patterns at the cost of flexibility.

Document databases (MongoDB, Firestore) store self-contained JSON documents. They excel when data is naturally hierarchical and accessed as a unit — a user profile with embedded addresses. They struggle with cross-document consistency and ad-hoc querying across fields.

Wide-column stores (Cassandra, HBase) are optimized for time-series and high-write workloads. Cassandra's partition key determines data placement; choosing it correctly is critical — a poorly chosen key creates hotspot partitions. Reads are fast if you query by partition key; arbitrary queries require expensive table scans.

The common mistake: choosing NoSQL for "scale" before understanding access patterns. PostgreSQL with proper indexing, connection pooling, and read replicas handles most workloads that require ACID guarantees, often simpler than operating a distributed NoSQL cluster.""",
    "excerpt": "A practical decision framework for choosing between SQL and NoSQL databases based on data model and access patterns.",
    "byline": "Architecture Review",
    "length": 915,
  },

  # ── System Design: Unique Constraints & Idempotency ────────────────────────
  {
    "url": "https://systems.example.com/idempotency-api-design",
    "title": "Idempotency in API Design: Idempotency Keys, Deduplication, and Retries",
    "site_name": "Systems Engineering",
    "content": """An operation is idempotent if applying it multiple times produces the same result as applying it once. GET, PUT, and DELETE are idempotent by definition; POST is not. In distributed systems where retries are common (network timeouts, 5xx errors), APIs must be designed for idempotency.

The idempotency key pattern: clients generate a unique key (UUID) per logical operation and send it as a header (`Idempotency-Key: uuid`). The server stores the key and result; subsequent requests with the same key return the cached result without re-executing. Stripe's API uses this for payment processing.

Implementation: insert the idempotency key into a deduplications table with a `UNIQUE` constraint before processing. If the insert fails with a duplicate key error, return the previously stored result. Use a database transaction to atomically insert the key and execute the operation.

Expiry policy: idempotency keys should expire after a reasonable window (24 hours, 7 days). After expiry, the same key is treated as a new request. This balances storage cost against the realistic retry window.""",
    "excerpt": "How to implement API idempotency using idempotency keys, deduplication tables, and retry-safe patterns.",
    "byline": "API Platform Team",
    "length": 900,
  },
  {
    "url": "https://systems.example.com/unique-constraints-enforcement",
    "title": "Enforcing Uniqueness at Scale: DB Constraints, Application Locks, and Trade-offs",
    "site_name": "Systems Engineering",
    "content": """Uniqueness constraints are trivial in a single-process, single-database system — a `UNIQUE` index handles everything. The challenge emerges at scale with multiple application servers, database replicas, and distributed caches.

Database-level unique indexes are the gold standard for uniqueness guarantees. PostgreSQL's `CREATE UNIQUE INDEX` creates a B-Tree index that rejects duplicate values atomically within a transaction. For composite uniqueness (e.g., unique per user per day), create a multi-column unique index.

Application-level deduplication (check-then-insert) is a TOCTOU race: two concurrent requests both check, both find no duplicate, both insert — one fails with a constraint violation. The fix is to let the database handle it and catch `IntegrityError` / `UniqueViolation` at the application layer.

For global uniqueness across shards, options include: routing all writes for a key to one shard (defeating the purpose of sharding), using a distributed ID service (Snowflake, UUID v7), or using a centralized uniqueness check with Redis `SET NX` before writing to the shard.""",
    "excerpt": "Strategies for enforcing uniqueness in distributed systems: database constraints, application-level deduplication, and sharding.",
    "byline": "Backend Platform",
    "length": 940,
  },

  # ── System Design: Caching ─────────────────────────────────────────────────
  {
    "url": "https://caching.example.com/cache-invalidation-strategies",
    "title": "Cache Invalidation Strategies: TTL, Event-Driven, and Write-Through",
    "site_name": "Caching Systems",
    "content": """Phil Karlton's quip — "there are only two hard things in computer science: cache invalidation and naming things" — remains relevant. Cache invalidation is hard because cached data can diverge from the source of truth, and stale reads have real consequences.

TTL-based invalidation sets a time-to-live on cache entries. Simple and self-healing, but requires tolerating stale data for up to TTL duration. Good for content that changes infrequently (product catalog, config) and where brief staleness is acceptable.

Write-through caching updates the cache synchronously on every write. The cache always reflects the latest state. Expensive writes (latency doubles) and cache churn on rarely-read data are the trade-offs. Write-around (write to DB, skip cache, let reads populate it lazily) avoids the churn.

Event-driven invalidation publishes cache invalidation events on writes (via Kafka, Redis Pub/Sub, or CDC from Postgres WAL). Other services consume the events and invalidate relevant keys. More complex but enables near-real-time consistency without TTL bloat.""",
    "excerpt": "Cache invalidation strategies: TTL, write-through, write-around, and event-driven invalidation with trade-offs.",
    "byline": "Infrastructure Platform",
    "length": 905,
  },
  {
    "url": "https://caching.example.com/redis-data-structures",
    "title": "Redis Data Structures for System Design: Sorted Sets, HyperLogLog, and Streams",
    "site_name": "Caching Systems",
    "content": """Redis is often treated as a key-value store, but its rich data structures enable elegant solutions to common system design problems. Strings with atomic `INCR`/`DECR` implement counters and rate limiters. Lists support message queues and activity feeds with O(1) push/pop.

Sorted sets (ZSet) store members with scores, enabling O(log N) rank queries. Use cases: leaderboards (`ZRANGEBYSCORE`), priority queues, sliding window rate limiting (score = timestamp, `ZREMRANGEBYSCORE` to expire old entries).

HyperLogLog is a probabilistic data structure for counting unique elements with ~0.81% error, using only 12KB of memory regardless of cardinality. `PFADD` adds elements; `PFCOUNT` returns the approximate unique count. Ideal for daily active users, unique page views.

Redis Streams (`XADD`, `XREAD`) implement durable append-only logs with consumer groups. Unlike Pub/Sub (fire-and-forget), Streams persist messages, support multiple consumer groups reading independently, and track acknowledgment — making them suitable for reliable event processing pipelines.""",
    "excerpt": "Redis data structures for system design: sorted sets for leaderboards, HyperLogLog for cardinality, and Streams for event processing.",
    "byline": "Redis Architecture",
    "length": 935,
  },
  {
    "url": "https://caching.example.com/cache-stampede-prevention",
    "title": "Cache Stampede: Causes, Detection, and Prevention with Probabilistic Early Expiry",
    "site_name": "Caching Systems",
    "content": """A cache stampede (thundering herd) occurs when a popular cache key expires and many concurrent requests simultaneously miss the cache, all hitting the database in parallel. The resulting database overload can cascade into a full outage.

The simplest prevention is request coalescing (cache locking): the first request to miss sets a lock, fetches from the database, and populates the cache; other requests wait for the lock. Disadvantage: waiting threads consume connections and memory.

Probabilistic early expiration (XFetch algorithm) avoids locks entirely. Each cache read probabilistically decides to recompute before the TTL expires, with probability increasing as expiration approaches. The formula: `recompute if current_time - delta * beta * log(rand()) >= expiry`. The background recompute updates the cache before it fully expires, preventing stampedes.

Background refresh: a separate process monitors TTLs and refreshes entries before they expire, decoupled from request serving. Works well for predictable, high-value cache keys (e.g., home feed, trending content).""",
    "excerpt": "How to prevent cache stampedes using request coalescing, probabilistic early expiration (XFetch), and background refresh.",
    "byline": "Reliability Engineering",
    "length": 920,
  },

  # ── System Design: Message Queues ─────────────────────────────────────────
  {
    "url": "https://messaging.example.com/kafka-internals",
    "title": "Kafka Internals: Partitions, Consumer Groups, and Exactly-Once Semantics",
    "site_name": "Messaging Systems",
    "content": """Kafka's core abstraction is the append-only log. Topics are divided into partitions, each an ordered, immutable sequence of messages stored on disk. Producers append to partition tails; consumers read sequentially from offsets. This design achieves high throughput by batching writes and leveraging sequential I/O.

Consumer groups enable parallel processing: each partition is consumed by exactly one consumer in a group. Adding consumers up to the partition count increases parallelism; beyond that, consumers are idle. Rebalancing (reassigning partitions when group membership changes) briefly pauses consumption.

Delivery semantics: at-most-once (commit before processing — messages can be lost), at-least-once (commit after processing — messages can be duplicated), exactly-once. Kafka's exactly-once is implemented via idempotent producers (sequence numbers prevent broker-side deduplication) and transactional APIs (atomic publish + offset commit across partitions).

Offset management: auto-commit (`enable.auto.commit=true`) is convenient but risks data loss (offset committed before processing completes) or duplicates (crash after processing before commit). Manual offset commit with `commitSync()` after processing gives at-least-once guarantee.""",
    "excerpt": "Kafka internals: partitions, consumer groups, rebalancing, delivery semantics, and exactly-once processing.",
    "byline": "Streaming Platform",
    "length": 960,
  },
  {
    "url": "https://messaging.example.com/outbox-pattern",
    "title": "The Transactional Outbox Pattern: Reliable Event Publishing Without Two-Phase Commit",
    "site_name": "Messaging Systems",
    "content": """The transactional outbox pattern solves the dual-write problem: atomically updating the database AND publishing an event to a message broker. Without it, a crash between the DB write and broker publish leaves the system in an inconsistent state.

The pattern: include an `outbox` table in the same database as business data. Within the same transaction, write the business entity AND insert a row into the outbox. A separate relay process (or CDC-based) reads unprocessed outbox rows and publishes them to the broker, then marks them as sent.

Debezium implements this via Change Data Capture (CDC): it reads Postgres's WAL (write-ahead log) and publishes changes to Kafka. The database transaction IS the unit of atomicity — no separate outbox table needed. Debezium's at-least-once delivery requires idempotent consumers.

Ordering guarantee: outbox rows processed in insertion order per partition key preserve event ordering for a given entity. Cross-entity ordering requires a single partition, sacrificing parallelism.""",
    "excerpt": "The transactional outbox pattern for reliable event publishing, CDC with Debezium, and ordering guarantees.",
    "byline": "Event-Driven Architecture",
    "length": 925,
  },

  # ── System Design: Rate Limiting ───────────────────────────────────────────
  {
    "url": "https://systems.example.com/rate-limiting-algorithms",
    "title": "Rate Limiting Algorithms: Token Bucket, Leaky Bucket, and Sliding Window",
    "site_name": "Systems Engineering",
    "content": """Rate limiting protects services from overload and abuse. The token bucket algorithm maintains a bucket filled at a constant rate with tokens; each request consumes a token. Requests are allowed while tokens exist; excess requests are rejected or queued. It accommodates bursts up to the bucket size.

The leaky bucket processes requests at a constant rate regardless of burst. Requests queue in a FIFO bucket; overflow is dropped. It smooths bursty traffic but doesn't allow short bursts — less flexible than token bucket for APIs with occasional spikes.

Fixed window counting counts requests per time window (e.g., 100 req/minute). Simple but suffers boundary bursts: 100 requests at 0:59 and 100 at 1:01 allows 200 in 2 seconds. Sliding window log (store timestamp of each request, count within window) fixes this but is memory-intensive.

Sliding window counter is the practical compromise: counter for current window + (1 - elapsed fraction) * previous window counter. Approximate but memory-efficient. Implemented in Redis with two counters and atomic Lua scripts for consistency across distributed rate limiters.""",
    "excerpt": "Rate limiting algorithms: token bucket, leaky bucket, fixed window, sliding window counter — trade-offs and Redis implementation.",
    "byline": "API Gateway Team",
    "length": 935,
  },

  # ── System Design: Consistent Hashing ─────────────────────────────────────
  {
    "url": "https://systems.example.com/consistent-hashing",
    "title": "Consistent Hashing: Virtual Nodes, Load Balancing, and Rendezvous Hashing",
    "site_name": "Systems Engineering",
    "content": """Naive modular hashing (`key % N`) requires remapping all keys when N changes — catastrophic for a cache cluster where adding a node invalidates N/(N+1) of cached data. Consistent hashing minimizes remapping: only K/N keys are remapped on average when a node is added.

The ring: nodes are placed at hash(node_id) positions on a 0–2^32 circle. A key maps to the first node clockwise from hash(key). Adding a node only affects keys between the new node and its predecessor.

Virtual nodes (vnodes) address non-uniform load distribution. Each physical node gets V virtual positions on the ring (typically 100-200). When a node is removed, its V vnodes distribute evenly across remaining nodes. Amazon DynamoDB and Apache Cassandra use virtual nodes.

Rendezvous hashing (HRW) is an alternative: for each candidate node, compute score = hash(key, node); assign to the highest-scoring node. No ring needed, and it distributes load uniformly without virtual nodes. Used in Nginx upstream hashing and CDN routing.""",
    "excerpt": "Consistent hashing internals: ring placement, virtual nodes, load distribution, and rendezvous hashing alternative.",
    "byline": "Distributed Systems",
    "length": 920,
  },

  # ── System Design: Distributed Transactions ────────────────────────────────
  {
    "url": "https://systems.example.com/saga-pattern",
    "title": "The Saga Pattern: Choreography vs Orchestration for Distributed Transactions",
    "site_name": "Systems Engineering",
    "content": """Two-phase commit (2PC) achieves distributed ACID transactions but requires a coordinator that can block all participants during failure. The Saga pattern provides an alternative: decompose a transaction into a sequence of local transactions, each publishing events, with compensating transactions for rollback.

Choreography-based sagas: each service listens for events and publishes its own events, with no central coordinator. Decoupled and resilient, but hard to reason about; adding a new step requires modifying multiple services; tracking overall progress is difficult.

Orchestration-based sagas: a saga orchestrator sends commands to each service and listens for replies. The orchestrator encodes the business flow explicitly, making it easier to monitor and debug. Coupling to the orchestrator is the trade-off.

Compensating transactions must be idempotent and must succeed eventually — a compensation that can fail creates a saga that can get stuck. Implement compensations as best-effort (e.g., issue a refund, not reverse a ledger entry) and ensure they're retried until successful.""",
    "excerpt": "Saga pattern for distributed transactions: choreography vs orchestration, compensating transactions, and failure handling.",
    "byline": "Microservices Architecture",
    "length": 940,
  },

  # ── System Design: Circuit Breaker & Resilience ────────────────────────────
  {
    "url": "https://systems.example.com/circuit-breaker-pattern",
    "title": "Circuit Breaker Pattern: States, Configuration, and Half-Open Recovery",
    "site_name": "Systems Engineering",
    "content": """The circuit breaker pattern prevents cascading failures by stopping calls to a failing service. Like an electrical circuit breaker, it has three states: Closed (normal operation, calls pass through), Open (calls fail fast without hitting the downstream service), and Half-Open (a probe request tests if recovery occurred).

State transitions: Closed → Open when failures exceed a threshold (e.g., 50% error rate over 10 calls). Open → Half-Open after a configurable timeout (e.g., 30 seconds). Half-Open → Closed if the probe succeeds; Half-Open → Open if it fails.

Configuration: `failureRateThreshold` (minimum failure rate to trip), `minimumNumberOfCalls` (sample window), `waitDurationInOpenState` (how long to stay open). Resilience4j and Hystrix are the canonical Java implementations; Go's `sony/gobreaker` is widely used.

Beyond failures: circuit breakers can also trip on slow calls exceeding a latency percentile threshold. This prevents a slow downstream from holding threads/connections, which would cause upstream memory pressure even without explicit errors.""",
    "excerpt": "Circuit breaker pattern: three states, transition thresholds, slow-call detection, and configuration with Resilience4j.",
    "byline": "Reliability Platform",
    "length": 905,
  },

  # ── System Design: Connection Pool ─────────────────────────────────────────
  {
    "url": "https://db.example.com/connection-pooling",
    "title": "Database Connection Pooling: PgBouncer, Sizing, and Common Mistakes",
    "site_name": "Database Engineering",
    "content": """Database connections are expensive: PostgreSQL spawns a process per connection, consuming ~5-10MB of RAM each. A web app with 100 instances × 10 connections/instance = 1000 connections — easily exceeding PostgreSQL's default `max_connections = 100` and overwhelming the database.

PgBouncer is a lightweight connection pooler that sits between app and database. In session mode, a database connection is held for the life of a client connection — minimal benefit. In transaction mode, a connection is held only for the duration of a transaction — dramatically reduces required connections but breaks session-level features (prepared statements, advisory locks).

Pool sizing: the formula `N_connections = core_count * 2 + effective_spindle_count` (from the HikariCP docs) is a starting point. But actual optimal size requires load testing — too few connections and requests queue; too many and connection overhead degrades throughput.

Common mistake: setting `max_pool_size` equal to `max_connections`. This leaves no headroom for admin connections and replication. Reserve ~10% of `max_connections` for maintenance.""",
    "excerpt": "Database connection pooling with PgBouncer, pool sizing strategies, transaction vs session mode, and common mistakes.",
    "byline": "Database Infrastructure",
    "length": 930,
  },

  # ── Data Structures: Arrays ───────────────────────────────────────────────
  {
    "url": "https://dsa.example.com/dynamic-array-amortized",
    "title": "Dynamic Arrays and Amortized Analysis: Why Doubling is O(1) Amortized",
    "site_name": "Data Structures & Algorithms",
    "content": """A dynamic array (std::vector in C++, ArrayList in Java) maintains a fixed-capacity array and resizes by copying when full. The key design decision is the growth factor. Doubling (capacity *= 2) achieves O(1) amortized append; growing by a fixed amount gives O(n) amortized.

Amortized analysis distributes the cost of occasional expensive operations across cheap ones. With doubling, a resize occurs at sizes 1, 2, 4, 8, ..., n. Total copy operations: n/2 + n/4 + ... + 1 = n-1 = O(n). Spread across n appends: O(1) per append on average.

Memory fragmentation and locality: dynamic arrays store elements contiguously, enabling cache-friendly sequential access. Random-access is O(1). Insertion or deletion in the middle is O(n) due to shifting. For frequent middle insertions, a linked list or deque is preferable.

C++ std::vector uses a growth factor between 1.5 (MSVC) and 2 (GCC/Clang). Factor 1.5 wastes less memory at the cost of more frequent resizes. Java's ArrayList uses 1.5x. Python's list uses ~1.125x for small lists, larger for big ones — empirically tuned.""",
    "excerpt": "Dynamic array internals, amortized O(1) append analysis, growth factors in C++/Java/Python, and locality benefits.",
    "byline": "Algorithm Analysis",
    "length": 900,
  },

  # ── Data Structures: Linked Lists ────────────────────────────────────────
  {
    "url": "https://dsa.example.com/linked-list-variants",
    "title": "Linked List Variants: Skip Lists, XOR Lists, and Intrusive Lists",
    "site_name": "Data Structures & Algorithms",
    "content": """Beyond singly and doubly linked lists, several variants trade memory or simplicity for specific performance characteristics. The XOR linked list stores `prev XOR next` instead of two pointers, halving pointer storage at the cost of readability and debuggability (cannot be inspected by standard debuggers).

Skip lists are a probabilistic alternative to balanced BSTs for ordered sets. They add forward pointers skipping multiple nodes, enabling O(log n) search, insertion, and deletion with simpler implementation than red-black trees. Redis's sorted sets (ZSET) use skip lists. MemSQL (SingleStore) uses skip lists for its lock-free index.

Intrusive linked lists embed the list pointers inside the data structure itself rather than in a wrapper node. The Linux kernel's `list_head` is the canonical example: `container_of` retrieves the enclosing structure from a pointer to the embedded `list_head`. Benefits: no heap allocation per node, cache-friendlier traversal.

Circular linked lists connect the tail to the head, enabling O(1) access to both ends without storing a tail pointer separately. Used in round-robin schedulers, music playlist loops.""",
    "excerpt": "Linked list variants: XOR lists, skip lists (used in Redis), intrusive lists (Linux kernel), and circular lists.",
    "byline": "Systems Data Structures",
    "length": 890,
  },

  # ── Data Structures: Trees ───────────────────────────────────────────────
  {
    "url": "https://dsa.example.com/red-black-tree-internals",
    "title": "Red-Black Tree Internals: Invariants, Rotations, and Why Databases Use B-Trees Instead",
    "site_name": "Data Structures & Algorithms",
    "content": """Red-black trees are self-balancing BSTs maintaining five invariants: every node is red or black; the root is black; leaves (NIL) are black; red nodes have black children; all paths from a node to its NIL leaves have the same number of black nodes. These ensure the tree height is at most 2*log(n+1).

Insertions always color the new node red (preserving black-height), then fix violations through recoloring and rotations. There are five insertion cases based on the uncle node's color and position. Deletion is more complex: removing a black node may violate black-height, requiring up to O(log n) rotations to restore invariants.

C++ STL's `std::map` and `std::set` use red-black trees; Java's `TreeMap` and `TreeSet` use the same. Both provide O(log n) search, insert, delete with guaranteed worst-case (unlike hash maps).

Databases prefer B-Trees: disk-optimized B-Trees store hundreds of keys per node (matching disk page size), dramatically reducing I/O. A red-black tree on disk requires one I/O per node; a B-Tree with branching factor 500 indexes a million rows in 4 levels (4 I/Os).""",
    "excerpt": "Red-black tree invariants, rotation mechanics, and why B-Trees are preferred for database indexes over red-black trees.",
    "byline": "Algorithm Design",
    "length": 955,
  },
  {
    "url": "https://dsa.example.com/avl-tree-rotations",
    "title": "AVL Trees: Balance Factor, Rotations, and Comparison with Red-Black Trees",
    "site_name": "Data Structures & Algorithms",
    "content": """AVL trees maintain a stricter balance invariant than red-black trees: the height difference between left and right subtrees of any node must be at most 1 (balance factor ∈ {-1, 0, 1}). This results in a tree height of at most 1.44*log(n), strictly shorter than a red-black tree's 2*log(n+1).

The four rotation cases: Left-Left (single right rotation on the unbalanced node), Right-Right (single left rotation), Left-Right (left rotation on left child, then right rotation on node), Right-Left (right rotation on right child, then left rotation on node).

AVL trees have faster lookups than red-black trees due to stricter balance, but require more rotations on insertions and deletions. For read-heavy workloads, AVL trees are preferable; for write-heavy workloads, red-black trees amortize better.

Practical use: AVL trees appear in database systems (OpenBSD's `rb_tree` uses AVL), memory allocators, and interval trees. Most language standard libraries (C++ STL, Java TreeMap) choose red-black trees for their lower constant factors in insertion.""",
    "excerpt": "AVL tree balance invariants, four rotation cases, height guarantees, and when to choose AVL vs red-black trees.",
    "byline": "Algorithm Design",
    "length": 915,
  },
  {
    "url": "https://dsa.example.com/trie-prefix-tree",
    "title": "Tries and Compressed Tries: Autocomplete, IP Routing, and Memory Optimization",
    "site_name": "Data Structures & Algorithms",
    "content": """A trie (prefix tree) stores strings by their characters, with each path from root to leaf representing a complete string. Lookup is O(m) where m is the key length — independent of the number of keys. Common use cases: autocomplete, spell-checking, IP routing tables.

A standard trie with 26 children per node wastes memory for sparse alphabets. Patricia tries (compact/compressed tries) merge single-child chains into edge labels, reducing node count dramatically. Radix trees (a generalized Patricia trie) store variable-length labels, used in Linux's IPv4 routing table.

For autocomplete, the trie stores words at terminal nodes. Finding all words with a given prefix is a DFS from the prefix node: O(p + W) where p is prefix length and W is total characters in matching words. Priority queues at each node enable top-K completion efficiently.

Aho-Corasick automaton adds failure links to a trie, enabling multi-pattern string matching in O(n + m + z) where n is text length, m is total pattern length, and z is match count. Used in intrusion detection, grep -F.""",
    "excerpt": "Trie data structure, compressed tries, radix trees, Aho-Corasick for multi-pattern matching, and autocomplete implementation.",
    "byline": "String Algorithms",
    "length": 935,
  },

  # ── Data Structures: Heaps ───────────────────────────────────────────────
  {
    "url": "https://dsa.example.com/heap-internals-priority-queue",
    "title": "Binary Heap Internals: Heapify, d-ary Heaps, and Fibonacci Heaps",
    "site_name": "Data Structures & Algorithms",
    "content": """A binary heap is a complete binary tree stored in an array, satisfying the heap property: every parent ≥ (max-heap) or ≤ (min-heap) its children. For node at index i: parent is at (i-1)/2, children at 2i+1 and 2i+2. This array representation eliminates pointer overhead.

Heapify (build-heap) converts an unsorted array into a heap in O(n) — not O(n log n) as one might expect. Key insight: heapify starts from the last internal node (n/2 - 1) and sifts down each; leaves need no work, and most internal nodes are near the bottom requiring few swaps.

D-ary heaps generalize to d children per node. Higher d reduces tree height (log_d n) and decreases extract-min cost, at the expense of more comparisons per sift-down. D=4 is a common sweet spot; cache-line-aware implementations use d matching elements per cache line.

Fibonacci heaps achieve O(1) amortized insert and decrease-key (vs O(log n) for binary heaps), making them theoretically optimal for Dijkstra's and Prim's algorithms. In practice, their complex implementation and poor cache behavior make binary heaps faster on real hardware for typical graph sizes.""",
    "excerpt": "Binary heap array representation, O(n) heapify, d-ary heaps, and Fibonacci heap trade-offs for graph algorithms.",
    "byline": "Algorithm Design",
    "length": 940,
  },

  # ── Data Structures: Hash Tables ────────────────────────────────────────
  {
    "url": "https://dsa.example.com/hash-table-collision-resolution",
    "title": "Hash Table Collision Resolution: Open Addressing, Robin Hood, and Cuckoo Hashing",
    "site_name": "Data Structures & Algorithms",
    "content": """Hash table collision resolution falls into two families: chaining (each bucket holds a list) and open addressing (probe for an empty slot in the table). Chaining is simple but introduces pointer indirection and heap allocation per element, hurting cache performance.

Open addressing stores all elements in the table itself. Linear probing clusters elements around collisions (primary clustering); quadratic probing reduces clustering but can miss slots. Double hashing uses a second hash function for step size, distributing probes more uniformly.

Robin Hood hashing is an open-addressing variant that reduces variance in probe lengths. On insertion, if the new element has a longer probe sequence than the current occupant, the new element takes the slot (steals from the rich). Displaced elements continue probing. Lookup stops when the probe distance of the found key exceeds the current probe distance.

Cuckoo hashing uses two hash functions and two tables. Each element has exactly two candidate positions. Insert: place at hash_1(key); if occupied, evict and re-insert at hash_2(evicted key); repeat. Lookup is always O(1) worst case (check exactly two positions). Used in network switch ASICs for exact-match packet lookup.""",
    "excerpt": "Hash collision resolution: open addressing, Robin Hood hashing, cuckoo hashing, and cache performance trade-offs.",
    "byline": "Data Structures Research",
    "length": 950,
  },

  # ── Data Structures: Graphs ──────────────────────────────────────────────
  {
    "url": "https://dsa.example.com/shortest-path-algorithms",
    "title": "Shortest Path Algorithms: Dijkstra, Bellman-Ford, A*, and When to Use Each",
    "site_name": "Data Structures & Algorithms",
    "content": """Dijkstra's algorithm finds single-source shortest paths in O((V+E) log V) with a min-heap. Invariant: once a vertex is extracted from the heap, its distance is final. Requires non-negative edge weights — a negative edge can create a shorter path to an already-settled vertex.

Bellman-Ford handles negative weights in O(VE), relaxing all edges V-1 times. A Vth round of relaxation detects negative cycles (any further relaxation indicates a cycle). Used in distance-vector routing protocols (RIP) and detecting arbitrage in currency exchange graphs.

A* extends Dijkstra with a heuristic h(v) estimating cost from v to the goal. The priority is f(v) = g(v) + h(v) where g(v) is cost from source. With an admissible heuristic (never overestimates), A* is optimal. Euclidean distance is admissible for geographic routing; Manhattan distance for grid maps.

Bidirectional Dijkstra meets in the middle, roughly halving the search space. Used in Google Maps for road network routing. Johnson's algorithm handles sparse graphs with negative weights: reweight edges to non-negative using Bellman-Ford, then run Dijkstra from all sources.""",
    "excerpt": "Dijkstra, Bellman-Ford, A*, and bidirectional search: algorithms, complexity, and selection criteria for shortest paths.",
    "byline": "Graph Algorithms",
    "length": 945,
  },
  {
    "url": "https://dsa.example.com/union-find-dsu",
    "title": "Union-Find (Disjoint Set Union): Path Compression, Union by Rank, and Applications",
    "site_name": "Data Structures & Algorithms",
    "content": """Union-Find (DSU) maintains a partition of elements into disjoint sets, supporting two operations: `find(x)` (find the representative of x's set) and `union(x, y)` (merge the sets containing x and y). Naive implementation is O(n) per operation; two optimizations make it nearly O(1).

Path compression flattens the tree during `find`: every node on the path to the root is made to point directly to the root. This amortizes future finds. Union by rank always attaches the shorter tree under the taller, preventing degenerate chains.

Together, path compression + union by rank achieve O(α(n)) per operation, where α is the inverse Ackermann function — effectively O(1) for all practical n. This is nearly optimal; DSU with only one optimization is O(log n) amortized.

Applications: Kruskal's MST algorithm (union edges in increasing weight order, skip if both endpoints in same set); connected components in undirected graphs; cycle detection; image segmentation (pixel connectivity); equivalence class computation in compilers.""",
    "excerpt": "Union-Find with path compression and union by rank achieving O(α(n)), plus applications in MST, connectivity, and cycle detection.",
    "byline": "Algorithm Analysis",
    "length": 920,
  },

  # ── Data Structures: Bloom Filter ───────────────────────────────────────
  {
    "url": "https://dsa.example.com/bloom-filter-variants",
    "title": "Bloom Filters: False Positive Rate, Counting Bloom Filters, and Cuckoo Filters",
    "site_name": "Data Structures & Algorithms",
    "content": """A Bloom filter is a space-efficient probabilistic set. Insert: hash with k hash functions, set k bits. Lookup: check if all k bits are set — if any is 0, definitely not present; if all are 1, probably present (false positive possible). False negatives are impossible.

False positive probability: (1 - e^(-kn/m))^k where n is elements, m is bits, k is hash functions. Optimal k = (m/n)*ln(2) ≈ 0.693*(m/n). With 10 bits per element and optimal k=7, false positive rate ≈ 1%. With 20 bits, ≈ 0.1%.

Standard Bloom filters don't support deletion (clearing a bit might affect other elements). Counting Bloom filters replace each bit with a counter (typically 4 bits), supporting deletion at the cost of 4x memory. Cuckoo filters use cuckoo hashing with fingerprints, achieving similar false positive rates as Bloom filters with O(1) deletion and higher space efficiency at low FPR.

Applications: LSM-tree storage engines (RocksDB, Cassandra) use Bloom filters to skip SSTables that definitely don't contain a key. Chrome's Safe Browsing checks URLs against a Bloom filter before a server lookup. CDNs track one-hit wonders to avoid caching rarely-accessed content.""",
    "excerpt": "Bloom filter false positive math, optimal parameters, counting and cuckoo filter variants, and applications in databases and CDNs.",
    "byline": "Probabilistic Data Structures",
    "length": 935,
  },

  # ── Data Structures: Segment Tree ───────────────────────────────────────
  {
    "url": "https://dsa.example.com/segment-tree-lazy-propagation",
    "title": "Segment Trees: Range Queries, Lazy Propagation, and Persistent Variants",
    "site_name": "Data Structures & Algorithms",
    "content": """A segment tree stores a function (sum, min, max, gcd) over segments of an array. The tree has 2n-1 nodes for an n-element array; leaves hold individual elements, internal nodes hold the combined result of their children. Build: O(n). Range query: O(log n). Point update: O(log n).

Lazy propagation defers range updates: instead of updating all leaves immediately, store a pending update at the highest applicable node. When traversing later, push the lazy tag down. This reduces range update complexity from O(n) to O(log n).

Persistent segment trees support queries on historical versions. Each update creates a new root node and shares unchanged subtrees with the previous version — only O(log n) new nodes per update. Used for queries like "kth smallest in array[l..r] at time t."

Merge sort tree (segment tree of sorted lists) answers "count elements in [l,r] ≤ k" in O(log² n) with O(n log n) memory. Fractional cascading reduces this to O(log n) per query. Used in offline range query problems in competitive programming.""",
    "excerpt": "Segment tree for range queries, lazy propagation for range updates, persistent segment trees, and merge sort tree.",
    "byline": "Competitive Programming",
    "length": 930,
  },

  # ── Data Structures: LRU Cache ──────────────────────────────────────────
  {
    "url": "https://dsa.example.com/lru-cache-implementation",
    "title": "LRU Cache Implementation: HashMap + Doubly-Linked List, and LFU Variant",
    "site_name": "Data Structures & Algorithms",
    "content": """An LRU (Least Recently Used) cache evicts the least recently accessed item when full. The canonical O(1) implementation combines a hash map (key → node) with a doubly-linked list (ordered by recency). Get: find in map, move node to list head. Put: insert at head, evict tail if over capacity.

In Python, `collections.OrderedDict` implements LRU trivially — `move_to_end()` is O(1). In Java, `LinkedHashMap` with `accessOrder=true` and an overridden `removeEldestEntry()` provides LRU semantics. C++ requires manual combination of `unordered_map` and `list`.

LFU (Least Frequently Used) evicts the item with the lowest access count, breaking ties by recency. O(1) LFU requires a more complex structure: a map from frequency to a doubly-linked list of nodes at that frequency, plus tracking the current minimum frequency.

Segmented LRU (SLRU) divides the cache into a probationary segment and a protected segment. New items enter probationary; frequently accessed items are promoted to protected; eviction targets probationary first. This handles scan resistance better than pure LRU (a large sequential scan won't flush the working set).""",
    "excerpt": "LRU cache with O(1) get/put using HashMap + doubly-linked list, LFU implementation, and segmented LRU variants.",
    "byline": "Data Structures Design",
    "length": 940,
  },

  # ── Data Structures: B-Tree ─────────────────────────────────────────────
  {
    "url": "https://dsa.example.com/btree-bplus-tree",
    "title": "B-Tree vs B+ Tree: Structure, Node Splitting, and Why B+ Trees Dominate Databases",
    "site_name": "Data Structures & Algorithms",
    "content": """B-Trees are balanced search trees where every node can have up to t-1 keys and t children. All leaves are at the same depth. Search, insert, delete are O(log_t n). With large t (matching disk page size), the tree is very shallow — a B-Tree with t=500 indexing 1 billion records has height ≈ 4.

B+ Trees differ in one key way: internal nodes store only keys (routing information), not values; all values are stored in leaves, which form a doubly-linked list. This has two advantages: internal nodes fit more keys (higher fanout, shallower tree), and sequential range scans traverse only the leaf linked list without ascending and descending the tree.

Node splitting on insertion: a full node splits at the median key, promoting the median to the parent. The parent may also split, propagating upward. Splits maintain the B-Tree invariant that all nodes are at least half full. Most database implementations pre-emptively split nodes on the way down to avoid upward propagation.

PostgreSQL's B-Tree implementation uses the high-key/downlink design: each non-rightmost page stores the highest key on the page as a fence key, enabling concurrent reads and splits without a root-to-leaf lock.""",
    "excerpt": "B-Tree vs B+ Tree structure, node splitting, range scan efficiency, and PostgreSQL's concurrent B-Tree implementation.",
    "byline": "Database Internals",
    "length": 950,
  },

  # ── C++: Smart Pointers ──────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/unique-ptr-internals",
    "title": "std::unique_ptr Internals: Zero-Cost Abstraction and Custom Deleters",
    "site_name": "Modern C++",
    "content": """std::unique_ptr enforces single ownership of a heap-allocated resource. When the unique_ptr goes out of scope, it calls the deleter (default: `delete`). It is non-copyable but movable — transfer of ownership via `std::move`. On modern compilers, unique_ptr has zero overhead compared to a raw pointer.

The internal layout: `unique_ptr<T, D>` stores a compressed pair of a pointer and deleter. The empty base optimization (EBO) ensures stateless deleters (like the default `std::default_delete<T>`) consume no additional bytes — the size of `unique_ptr<T>` equals `sizeof(T*)`.

Custom deleters enable unique_ptr to manage non-heap resources: file handles (`unique_ptr<FILE, decltype(&fclose)>`), POSIX file descriptors, Vulkan objects. A lambda deleter can be captured but adds size equal to the captured state.

`make_unique<T>(args...)` is preferred over `new T(args)` directly: it avoids repeated type names, is exception-safe (no partial construction if constructor throws with raw `new`), and prevents manual `delete`.""",
    "excerpt": "std::unique_ptr internals, zero-cost abstraction via EBO, custom deleters for non-heap resources, and make_unique.",
    "byline": "C++ Core Guidelines",
    "length": 910,
  },
  {
    "url": "https://cpp.example.com/shared-ptr-weak-ptr",
    "title": "std::shared_ptr and weak_ptr: Reference Counting, Cycles, and Performance Cost",
    "site_name": "Modern C++",
    "content": """std::shared_ptr implements shared ownership through reference counting. Each shared_ptr holds a pointer to the object and a pointer to a control block containing the reference count, weak reference count, and deleter. The reference count is an atomic integer, making copy/destruction thread-safe but not free.

The control block allocation: `new T` followed by `shared_ptr<T>(ptr)` performs two allocations. `make_shared<T>()` performs one allocation for both the object and control block, improving cache locality and reducing allocator overhead — prefer it.

`std::weak_ptr` observes a shared_ptr without extending its lifetime. It doesn't prevent destruction; `weak_ptr::lock()` returns a `shared_ptr` if the object still exists (by atomically incrementing the reference count if it's > 0). Used to break reference cycles: parent-child trees where both hold shared_ptr would never be destroyed.

Performance: atomic increment/decrement on copy/destroy is ~10ns — negligible for infrequent operations but measurable in tight loops. In hot paths, use raw pointers or `unique_ptr` with clear ownership, reserving `shared_ptr` for genuinely shared lifetime semantics.""",
    "excerpt": "shared_ptr reference counting, control block layout, make_shared vs new, weak_ptr for cycle breaking, and performance.",
    "byline": "C++ Performance",
    "length": 930,
  },
  {
    "url": "https://cpp.example.com/raii-resource-management",
    "title": "RAII in C++: Resource Acquisition Is Initialization and Exception Safety",
    "site_name": "Modern C++",
    "content": """RAII (Resource Acquisition Is Initialization) ties resource lifetime to object lifetime. The resource is acquired in the constructor and released in the destructor. Since C++ guarantees destructors are called when objects go out of scope — including during stack unwinding on exceptions — RAII makes resource leaks and double-frees structurally impossible.

The canonical examples: `std::lock_guard<std::mutex>` acquires the mutex in its constructor and releases in its destructor, regardless of how the scope is exited. `std::ifstream` opens the file on construction, closes on destruction. Smart pointers are RAII for heap memory.

RAII and exception safety: a function is exception-safe if it doesn't leak resources or leave data structures in invalid states when an exception is thrown. With RAII, every resource is wrapped in an object with a destructor — even if an exception propagates, all in-scope RAII objects are destroyed and resources released.

Scope-exit utilities (`boost::scope_exit`, `folly::ScopeGuard`, C++23 `std::scope_exit`) implement ad-hoc RAII for arbitrary cleanup code without defining a named class.""",
    "excerpt": "RAII pattern for exception-safe resource management in C++, lock_guard, scope-exit utilities, and strong exception guarantees.",
    "byline": "C++ Idioms",
    "length": 905,
  },

  # ── C++: Move Semantics ──────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/move-semantics-rvalue",
    "title": "Move Semantics and Rvalue References: Eliminating Unnecessary Copies",
    "site_name": "Modern C++",
    "content": """Move semantics, introduced in C++11, enable transferring resources from a temporary (rvalue) to another object without copying. A move constructor and move assignment operator steal the internals of the source object and leave it in a valid-but-unspecified state (typically a null/empty state).

Rvalue references (`T&&`) bind only to temporaries and xvalues. `std::move(x)` casts x to an rvalue reference, signaling "I'm done with x, take its guts." It doesn't move anything itself — the actual transfer happens in the move constructor/assignment.

Return value optimization (RVO/NRVO) often elides copies or moves entirely: the compiler constructs the return value directly in the caller's storage. This is guaranteed by C++17 for prvalues. Explicitly `std::move`-ing a return value can actually defeat NRVO.

The rule of five: if you define a custom destructor, copy constructor, or copy assignment operator, you likely need to define all five (destructor, copy constructor, copy assignment, move constructor, move assignment). The compiler-generated move operations are suppressed when you define a copy operation.""",
    "excerpt": "Move semantics, rvalue references, std::move, return value optimization (RVO), and the rule of five in C++11.",
    "byline": "C++ Language",
    "length": 920,
  },
  {
    "url": "https://cpp.example.com/perfect-forwarding",
    "title": "Perfect Forwarding in C++: std::forward, Universal References, and Factory Functions",
    "site_name": "Modern C++",
    "content": """Perfect forwarding preserves the value category (lvalue or rvalue) of function arguments when passing them to another function. Without it, an rvalue argument becomes an lvalue inside the function body (it has a name), and forwarding loses move semantics.

Universal references (Scott Meyers' term; the standard calls them forwarding references) are `T&&` parameters in a template context where T is deduced. They bind to both lvalues and rvalues through reference collapsing: `T& &&` → `T&`, `T&& &&` → `T&&`.

`std::forward<T>(arg)` conditionally casts arg: if T is an lvalue reference, cast to lvalue; if rvalue reference, cast to rvalue. The canonical factory pattern: `template<typename T, typename... Args> unique_ptr<T> make_unique(Args&&... args) { return unique_ptr<T>(new T(std::forward<Args>(args)...)); }`.

Pitfall: universal references only arise in deduced contexts. `void f(Widget&&)` is an rvalue reference, not a universal reference — Widget is not deduced. Over-using universal references with `std::forward` makes code harder to read; prefer overloads or concepts in C++20.""",
    "excerpt": "Perfect forwarding with std::forward, universal references vs rvalue references, reference collapsing, and factory functions.",
    "byline": "C++ Templates",
    "length": 925,
  },

  # ── C++: Templates & Generics ────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/template-metaprogramming",
    "title": "Template Metaprogramming: Type Traits, SFINAE, and constexpr if",
    "site_name": "Modern C++",
    "content": """Template metaprogramming (TMP) performs computation at compile time using template specialization and recursion. The classic example is compile-time factorial: `template<int N> struct Factorial { static const int value = N * Factorial<N-1>::value; }`. Verbose and largely superseded by `constexpr` functions.

Type traits (`<type_traits>`) inspect and transform types at compile time: `std::is_integral<T>`, `std::remove_reference<T>`, `std::enable_if<condition, T>`. The standard library uses them extensively to select algorithm implementations.

SFINAE (Substitution Failure Is Not An Error): when template argument substitution fails, the overload is discarded rather than causing a compilation error. This enables conditionally enabling/disabling function templates: `template<typename T, typename = std::enable_if_t<std::is_integral_v<T>>> void f(T)` accepts only integral types.

C++17 `if constexpr` replaces many SFINAE patterns: `if constexpr (std::is_integral_v<T>) { ... } else { ... }` — the non-matching branch is discarded at compile time without instantiation. C++20 Concepts provide a cleaner syntax: `template<std::integral T> void f(T)` is equivalent to the enable_if version but readable.""",
    "excerpt": "C++ template metaprogramming, type traits, SFINAE for conditional compilation, constexpr if, and C++20 concepts.",
    "byline": "Advanced C++",
    "length": 940,
  },
  {
    "url": "https://cpp.example.com/variadic-templates-parameter-packs",
    "title": "Variadic Templates and Parameter Packs: Type-Safe printf and Tuple Implementation",
    "site_name": "Modern C++",
    "content": """Variadic templates accept a variable number of template arguments via parameter packs (`typename... Args`). Expansion uses `...` on the pack: `f(args...)` expands to `f(arg0, arg1, arg2)`. The canonical use is type-safe variadic functions, replacing C's `va_args`.

A type-safe `print` function: `template<typename T, typename... Rest> void print(T first, Rest... rest) { std::cout << first; if constexpr (sizeof...(rest) > 0) print(rest...); }`. The `sizeof...(pack)` operator returns the count at compile time.

`std::tuple` is implemented with variadic templates and recursive inheritance: `Tuple<T, Rest...>` inherits from `Tuple<Rest...>`, each level storing one element. `std::get<N>` uses template recursion to index into the inheritance chain. Structured bindings (`auto [a, b] = tuple`) are syntactic sugar for `std::get`.

Fold expressions (C++17) eliminate the recursive helper function: `(std::cout << ... << args)` is a left fold that expands to `((std::cout << arg0) << arg1) << arg2`. Sum: `(0 + ... + args)`. Available with operators: +, *, |, &, ,, &&, ||.""",
    "excerpt": "Variadic templates, parameter pack expansion, type-safe variadic functions, tuple implementation, and C++17 fold expressions.",
    "byline": "C++ Language Features",
    "length": 930,
  },

  # ── C++: Concurrency ────────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/cpp-concurrency-mutex",
    "title": "C++ Concurrency: std::thread, std::mutex, and Condition Variables",
    "site_name": "Modern C++",
    "content": """C++11 introduced a standardized threading library. `std::thread` launches a function in a new OS thread. Ownership: a joinable thread must be `join()`ed or `detach()`ed before destruction (otherwise the destructor calls `std::terminate()`). Use `std::jthread` (C++20) for automatic joining in RAII style.

`std::mutex` protects shared data. Always use `std::lock_guard<std::mutex>` or `std::unique_lock<std::mutex>` (never lock/unlock manually). `lock_guard` is a simple RAII lock; `unique_lock` supports deferred locking, timed locking, and is required for use with condition variables.

`std::condition_variable` enables threads to wait for a condition. `wait(lock, predicate)` releases the lock and sleeps until notified AND predicate returns true — the predicate handles spurious wakeups. `notify_one()` wakes one waiting thread; `notify_all()` wakes all.

`std::atomic<T>` for single-variable synchronization without a mutex. `std::atomic<int>` provides `fetch_add`, `compare_exchange_weak`, `load(memory_order_acquire)`, and `store(memory_order_release)`. Prefer `std::atomic_flag` for a lock-free spin lock implementation.""",
    "excerpt": "C++ threading: std::thread, jthread, mutex, lock_guard, condition_variable, and std::atomic with memory ordering.",
    "byline": "Concurrent C++",
    "length": 935,
  },
  {
    "url": "https://cpp.example.com/cpp-async-futures",
    "title": "C++ Async and Futures: std::async, std::promise, and Coroutines Preview",
    "site_name": "Modern C++",
    "content": """std::async launches a callable asynchronously, returning a `std::future<T>`. Calling `future.get()` blocks until the result is ready. The launch policy controls execution: `std::launch::async` guarantees a new thread; `std::launch::deferred` evaluates lazily on `get()`. The default (unspecified) may not create a thread — always specify explicitly.

`std::promise<T>` / `std::future<T>` decouples result production from consumption. The producer calls `promise.set_value(v)`, unblocking the consumer's `future.get()`. `std::shared_future<T>` allows multiple threads to wait for the same result.

`std::packaged_task<F>` wraps a callable and associates it with a future, enabling deferred execution in a thread pool: package the task, submit to pool, retrieve future to wait for result.

C++20 coroutines (`co_await`, `co_yield`, `co_return`) provide stackless coroutines for async programming. The compiler transforms coroutine functions into state machines. `std::generator` (C++23) enables lazy sequences. Libraries like cppcoro provide task, generator, and async_generator types built on coroutines.""",
    "excerpt": "C++ async futures: std::async, promise/future, packaged_task, and a preview of C++20 coroutines for async programming.",
    "byline": "Modern C++ Async",
    "length": 920,
  },

  # ── C++: Memory Management ───────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/memory-layout-alignment",
    "title": "C++ Memory Layout: Alignment, Padding, and Cache-Friendly Data Structures",
    "site_name": "Modern C++",
    "content": """Struct layout in C++ is determined by alignment requirements. Each member is placed at an address that is a multiple of its alignment (typically its size). Padding bytes are inserted to satisfy alignment. A `double` after a `char` requires 7 padding bytes; reordering fields eliminates waste.

`alignof(T)` returns alignment requirement; `sizeof(T)` returns total size including padding. The struct alignment is the maximum alignment of its members. `alignas(N)` overrides alignment: `alignas(64) struct CacheLine { ... }` aligns to a cache line boundary, preventing false sharing.

False sharing: two threads writing different variables that happen to occupy the same cache line cause cache line invalidation on every write. Align hot, concurrently-written variables to separate cache lines using `alignas(64)` and padding.

Cache-friendly data layout (data-oriented design): arrays of structures (AoS) vs structures of arrays (SoA). AoS stores all fields of one object together (cache-friendly for per-object access); SoA stores each field in a separate array (cache-friendly for SIMD and processing one field across many objects). Game engines and physics simulations use SoA for performance.""",
    "excerpt": "C++ struct padding, alignment, alignas, false sharing prevention, and data-oriented design with AoS vs SoA layouts.",
    "byline": "Performance C++",
    "length": 940,
  },
  {
    "url": "https://cpp.example.com/allocators-memory-pools",
    "title": "Custom Allocators and Memory Pools in C++: Reducing Heap Fragmentation",
    "site_name": "Modern C++",
    "content": """The default `new`/`delete` allocator is general-purpose but slow for high-frequency, fixed-size allocations. Custom allocators trade generality for performance. C++'s allocator model allows injecting custom allocators into standard containers: `std::vector<T, MyAllocator<T>>`.

Pool allocators pre-allocate a large block and serve fixed-size chunks. Free list maintains a list of available chunks; allocate pops from the list (O(1)); deallocate pushes back (O(1)). No fragmentation for uniform sizes. Used in embedded systems and game engines.

Arena (region/bump) allocators allocate from a contiguous buffer by incrementing a pointer. Allocation is O(1) with no bookkeeping. Deallocation is O(1) for the entire arena (reset pointer to start) but individual deallocations are not supported. Ideal for request-scoped data: allocate freely, free everything at request end.

C++17 `std::pmr` (polymorphic memory resources) standardizes memory resource injection without template parameters: `std::pmr::vector<T>` accepts a `std::pmr::memory_resource*`. Standard resources include `monotonic_buffer_resource` (arena) and `synchronized_pool_resource` (thread-safe pool).""",
    "excerpt": "Custom allocators, pool allocators, arena allocators, and C++17 std::pmr for reducing heap fragmentation.",
    "byline": "Memory Systems",
    "length": 935,
  },

  # ── C++: Virtual Functions ───────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/vtable-virtual-dispatch",
    "title": "Virtual Dispatch in C++: vtable Layout, Virtual Inheritance, and Devirtualization",
    "site_name": "Modern C++",
    "content": """Virtual dispatch enables polymorphism: calling a virtual function through a base pointer invokes the derived class's implementation. Each class with virtual functions has a vtable — a static array of function pointers. Each object contains a hidden vptr pointing to its class's vtable, typically as the first field.

Calling a virtual function: dereference vptr, index into vtable, call the function pointer. This is an indirect call — one more level of indirection than a direct call. The cost: ~4-7 ns on modern hardware due to branch misprediction and I-cache pressure. Direct calls are ~1 ns.

Virtual inheritance (for diamond inheritance) adds another level: a vptr points to a virtual base table, adding overhead. Avoid multiple virtual inheritance in performance-critical code.

Devirtualization: the compiler can eliminate virtual dispatch when the dynamic type is known at compile time (object is stack-allocated or final class). `final` keyword hints that no further subclassing occurs, enabling the optimizer to devirtualize call sites. Profile-guided optimization (PGO) devirtualizes based on runtime type frequency.""",
    "excerpt": "C++ virtual dispatch, vtable layout, vptr overhead, virtual inheritance, and compiler devirtualization techniques.",
    "byline": "C++ Internals",
    "length": 925,
  },

  # ── C++: STL Containers ──────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/unordered-map-internals",
    "title": "std::unordered_map Internals: Bucket Array, Load Factor, and Performance Pitfalls",
    "site_name": "Modern C++",
    "content": """std::unordered_map is a hash map using separate chaining. The bucket array is a `vector<list<pair<K,V>>>`. Load factor = elements / buckets; when it exceeds `max_load_factor()` (default 1.0), rehashing doubles the bucket count and redistributes all elements — O(n) amortized O(1).

Performance pitfalls: (1) Rehashing invalidates all iterators and references — never hold iterators across insertions without reserving capacity first with `reserve(n)`. (2) String keys hash to O(|key|), making short string optimization (SSO) critical for short keys. (3) The default hash for integers on MSVC uses the identity function — sequential integer keys cluster into the same few buckets, degrading to O(n) lookup.

Custom hash functions improve performance for common types. For integer keys, a multiplicative hash or xor-shift hash distributes better. For strings, FNV-1a or xxHash outperform `std::hash<std::string>` in throughput.

`absl::flat_hash_map` (Abseil) and `robin_hood::unordered_map` use open addressing with linear probing — significantly better cache performance than separate chaining, often 3-5x faster for small, hot maps.""",
    "excerpt": "std::unordered_map internals, rehashing, iterator invalidation, bad hash functions, and faster alternatives.",
    "byline": "STL Performance",
    "length": 940,
  },

  # ── C++: Lambda ─────────────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/lambda-captures-generics",
    "title": "C++ Lambda Deep Dive: Capture Modes, Generic Lambdas, and Immediately Invoked",
    "site_name": "Modern C++",
    "content": """A C++ lambda is syntactic sugar for a compiler-generated anonymous struct with an overloaded `operator()`. Captures become member variables. `[=]` captures all locals by value; `[&]` by reference. Dangling references: `[&]` capturing a local that outlives the lambda causes undefined behavior.

Init captures (C++14): `[x = std::move(obj)]` captures a move-only type. `[self = shared_from_this()]` captures a shared_ptr in async callbacks, extending lifetime. Mutable lambdas (`[x]() mutable { x++; }`) allow modifying value-captured variables.

Generic lambdas (C++14): `auto f = [](auto x) { return x * 2; }` — each call with a different type instantiates a new `operator()` template. C++20 allows explicit template parameters: `[](std::vector<auto> v) { }`.

Immediately invoked lambda expressions (IILE): `auto val = [&]() -> int { /* complex init */ return result; }();` — useful for complex initialization of `const` variables. More readable than immediately-invoked function expressions.""",
    "excerpt": "C++ lambda captures, init captures for move-only types, generic lambdas, mutable lambdas, and immediately invoked patterns.",
    "byline": "C++ Functional",
    "length": 915,
  },

  # ── C++: constexpr ───────────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/constexpr-compile-time",
    "title": "constexpr in C++: Compile-Time Evaluation, consteval, and Constant Expressions",
    "site_name": "Modern C++",
    "content": """`constexpr` functions can be evaluated at compile time when called with constant arguments. C++11 constexpr was restrictive (single return statement). C++14 removed most restrictions: loops, local variables, and multiple statements are allowed. C++20 allows `constexpr` `new` / `delete`, `std::vector`, and `std::string`.

A `constexpr` function evaluated at compile time produces a compile-time constant usable in array sizes, template arguments, and non-type template parameters. If called with non-constant arguments, it evaluates at runtime like a regular function.

`consteval` (C++20) mandates compile-time evaluation — the function cannot be called at runtime. Useful for functions that must produce constants (e.g., compile-time hash tables). `constinit` ensures a variable is zero-initialized at compile time without implying immutability (unlike `constexpr` variables).

Compile-time lookup tables: `constexpr std::array<int, 256> table = []() consteval { std::array<int, 256> t{}; for (int i=0; i<256; i++) t[i] = f(i); return t; }();` — computed once at compile time, zero runtime cost.""",
    "excerpt": "C++ constexpr for compile-time evaluation, consteval for compile-time-only functions, constinit, and compile-time lookup tables.",
    "byline": "C++ Compile-Time",
    "length": 920,
  },

  # ── C++: C++20 Features ──────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/cpp20-concepts",
    "title": "C++20 Concepts: Constraining Templates and Improving Error Messages",
    "site_name": "Modern C++",
    "content": """Concepts name and constrain template requirements, replacing SFINAE with readable syntax. A concept is a predicate on types evaluated at compile time: `template<typename T> concept Integral = std::is_integral_v<T>`. Usage: `template<Integral T> T gcd(T a, T b)` — clearer than `enable_if`.

Abbreviated function templates: `void f(std::integral auto x)` is syntactic sugar for `template<std::integral T> void f(T x)`. `auto` parameters anywhere in a function signature introduce template parameters.

Requires expressions allow compound constraints: `requires { { expr } -> SomeConcept; }` checks that `expr` is valid and its type satisfies `SomeConcept`. The standard library defines concepts in `<concepts>`: `std::same_as`, `std::convertible_to`, `std::invocable`, `std::ranges::range`.

Error messages: with SFINAE, substitution failures produce incomprehensible error dumps. With concepts, violations produce a clear "T does not satisfy constraint Integral" message pointing to the failing requirement. This is the primary practical benefit for most code.""",
    "excerpt": "C++20 concepts for template constraints, abbreviated function templates, requires expressions, and improved error messages.",
    "byline": "C++20 Features",
    "length": 925,
  },
  {
    "url": "https://cpp.example.com/cpp20-ranges",
    "title": "C++20 Ranges: Views, Pipelines, and Lazy Evaluation",
    "site_name": "Modern C++",
    "content": """C++20 ranges extend the STL algorithm model with composable, lazy views. A range is anything with `begin()`/`end()`; a view is a lightweight, non-owning range with O(1) copy. Views compose via `|`: `vec | std::views::filter(even) | std::views::transform(square)` creates a lazy pipeline evaluated only when iterated.

Laziness: each element passes through the pipeline on demand — no intermediate collections. This enables processing of infinite ranges: `std::views::iota(0)` is an infinite range of integers; `views::take(10)` limits to 10 elements.

Range algorithms in `<algorithm>` accept range objects directly: `std::ranges::sort(vec)` instead of `std::sort(vec.begin(), vec.end())`. They also accept projections: `std::ranges::sort(people, {}, &Person::age)` sorts by age field without a custom comparator.

Sentinels replace the end iterator: any type satisfying `sentinel_for<Iter>` can serve as the end marker, enabling null-terminated C string ranges and other non-sized ranges. `std::ranges::subrange` pairs an iterator with a sentinel.""",
    "excerpt": "C++20 ranges: composable lazy views, pipeline syntax, infinite ranges, range algorithms with projections, and sentinels.",
    "byline": "C++20 Ranges Library",
    "length": 930,
  },

  # ── System Design: Load Balancing ─────────────────────────────────────────
  {
    "url": "https://systems.example.com/load-balancing-algorithms",
    "title": "Load Balancing Algorithms: Round-Robin, Least Connections, and Power of Two Choices",
    "site_name": "Systems Engineering",
    "content": """Load balancing distributes incoming requests across backend servers to maximize throughput and minimize latency. The choice of algorithm significantly affects performance under heterogeneous load.

Round-robin cycles through servers in order. Simple and CPU-efficient, but ignores server load — a slow server receiving the same request rate as a fast one becomes a bottleneck. Weighted round-robin assigns proportional request rates based on server capacity.

Least-connections routes to the server with the fewest active connections, approximating shortest queue. Accurate but requires tracking connection counts; under high request rates, the tracking becomes a bottleneck. Least-response-time extends this with latency weighting.

Power of Two Choices (P2C): pick two servers at random, send to the one with fewer connections. This achieves O(log log n) maximum load (vs O(log n / log log n) for random) while requiring only two choices — no global minimum scan. Used in NGINX, HAProxy's `leastconn` with random sampling.""",
    "excerpt": "Load balancing: round-robin, least connections, weighted variants, and Power of Two Choices algorithm with complexity analysis.",
    "byline": "Networking Infrastructure",
    "length": 905,
  },

  # ── System Design: Event Sourcing & CQRS ──────────────────────────────────
  {
    "url": "https://systems.example.com/event-sourcing-cqrs",
    "title": "Event Sourcing and CQRS: Append-Only Events as the Source of Truth",
    "site_name": "Systems Engineering",
    "content": """Event sourcing stores state as a sequence of events rather than current state. The current state is derived by replaying events from the beginning (or a snapshot). Benefits: complete audit trail, ability to replay history, temporal queries ("what was the balance on Tuesday?").

CQRS (Command Query Responsibility Segregation) separates the write model (commands → events) from the read model (projections of events optimized for queries). Read models are eventually consistent with the event store and can be rebuilt by replaying events.

Snapshots prevent excessive replay time: periodically store a snapshot of current state, replay only events after the snapshot. Snapshot frequency depends on write rate and acceptable startup latency.

Challenges: event schema evolution (old events must be readable with new code — use upcasting or versioned events); eventual consistency (read models lag behind writes, requiring careful UI design); complex queries (joins across multiple aggregates require denormalized projections). Event sourcing adds significant complexity — apply only when audit trail or temporal queries are genuine requirements.""",
    "excerpt": "Event sourcing as append-only store, CQRS for separate read/write models, snapshots, schema evolution, and when to avoid it.",
    "byline": "Domain-Driven Design",
    "length": 935,
  },

  # ── Data Structures: Skip List ───────────────────────────────────────────
  {
    "url": "https://dsa.example.com/skip-list-probabilistic",
    "title": "Skip Lists: Probabilistic Balancing and Concurrent Skip Lists",
    "site_name": "Data Structures & Algorithms",
    "content": """A skip list is a layered linked list where higher layers skip over more elements. The bottom layer is a complete sorted linked list; each element is promoted to higher layers with probability p (typically 0.5 or 0.25). Expected height is O(log n). Search traverses from the top layer down, skipping large ranges before descending.

Expected time complexity: O(log n) for search, insert, delete — same as balanced BSTs. But skip lists are simpler to implement and to modify for concurrent access. The insertion algorithm is local: find the position, insert in the bottom layer, promote with coin flips. No global rebalancing.

Concurrent skip lists: the lock-free variant (HBSL/SkipNet) uses CAS to mark nodes as logically deleted before physical removal. The reference `java.util.concurrent.ConcurrentSkipListMap` is a non-blocking, linearizable ordered map. Database systems (Redis ZSET, MemSQL) choose skip lists over trees for concurrent ordered access.

Cache performance: skip lists have worse cache behavior than B-Trees because nodes are individually heap-allocated. For in-memory databases, B-Trees with large node sizes outperform skip lists; for simpler concurrent use cases, skip lists win on implementation complexity.""",
    "excerpt": "Skip list probabilistic balancing, O(log n) complexity, lock-free concurrent skip lists, and comparison with B-Trees.",
    "byline": "Data Structures",
    "length": 920,
  },

  # ── System Design: Write-Ahead Log ────────────────────────────────────────
  {
    "url": "https://db.example.com/wal-write-ahead-log",
    "title": "Write-Ahead Logging: Durability, Recovery, and LSM-Tree WAL",
    "site_name": "Database Engineering",
    "content": """Write-Ahead Logging (WAL) ensures durability by writing changes to a log before applying them to data pages. On recovery after a crash, the database replays WAL records to restore committed transactions and undo uncommitted ones. The key invariant: a transaction is durable once its WAL record is flushed to disk (fsync'd), regardless of whether data pages are flushed.

PostgreSQL's WAL is used for: crash recovery, streaming replication (WAL records streamed to standbys), point-in-time recovery (PITR — replay WAL from a base backup to any point in time), and logical replication (parse WAL for row-level changes).

WAL write modes affect performance: synchronous commit (`synchronous_commit = on`) fsync's WAL on every commit — safe but slow. Asynchronous commit (`synchronous_commit = off`) skips fsync — up to `wal_writer_delay` of data loss risk but dramatically higher throughput.

LSM-Trees (RocksDB, Cassandra) use a WAL differently: writes go to WAL + in-memory memtable. When the memtable fills, it's flushed to an SSTable on disk. The WAL is only needed for recovery — once an SSTable is written, its WAL records can be garbage collected.""",
    "excerpt": "Write-Ahead Log for crash recovery, PostgreSQL WAL for replication and PITR, synchronous vs async commit, and LSM WAL.",
    "byline": "Database Storage",
    "length": 945,
  },

  # ── System Design: Backpressure ───────────────────────────────────────────
  {
    "url": "https://systems.example.com/backpressure-flow-control",
    "title": "Backpressure and Flow Control: Preventing Cascade Failures in Pipelines",
    "site_name": "Systems Engineering",
    "content": """Backpressure is a flow control mechanism where downstream stages signal upstream stages to slow down when they're overwhelmed. Without it, fast producers overwhelm slow consumers, causing unbounded queue growth, memory exhaustion, and cascade failures.

In reactive systems, backpressure propagates demand: a subscriber requests N items, and the publisher sends at most N. This is the core of Reactive Streams / Project Reactor / RxJava 2. Pull-based flow control prevents the "machine gun" producer pattern.

In TCP, the receive window limits how much data can be in flight. When the receiver's buffer fills, the window shrinks to zero, stalling the sender. Application-level protocols implement similar mechanisms: GRPC uses HTTP/2 flow control; Kafka consumers control read rate via `max.poll.records` and `fetch.max.bytes`.

In thread pools, backpressure manifests as bounded queues with rejection. `CallerRunsPolicy` in Java's `ThreadPoolExecutor` runs the task on the submitting thread when the queue is full — naturally throttling the producer by making it do work instead of submitting.""",
    "excerpt": "Backpressure for flow control in reactive systems, reactive streams demand model, TCP window, and caller-runs policy.",
    "byline": "Systems Reliability",
    "length": 910,
  },

  # ── System Design: Two-Phase Commit ───────────────────────────────────────
  {
    "url": "https://systems.example.com/two-phase-commit",
    "title": "Two-Phase Commit: Protocol, Failure Modes, and Why It's Rarely Used",
    "site_name": "Systems Engineering",
    "content": """Two-phase commit (2PC) achieves atomic commitment across multiple participants. Phase 1 (prepare): coordinator asks all participants to vote yes/no. Phase 2 (commit/abort): if all voted yes, coordinator sends commit; if any voted no, sends abort. Participants must durably log their vote before responding.

Failure modes: if the coordinator fails after participants voted yes but before sending commit, participants are blocked indefinitely — they've voted yes and can't unilaterally commit or abort (the blocking problem). Three-phase commit (3PC) adds a pre-commit phase to allow participants to abort safely during coordinator failure, but requires synchronous communication and is impractical in real networks.

Modern distributed databases avoid 2PC. Google Spanner uses TrueTime and Paxos consensus per shard, with 2PC only for cross-shard transactions — tightly bounded by TrueTime uncertainty. CockroachDB uses parallel commits: a transaction is atomic once its record is replicated, without a separate commit round-trip.

The Saga pattern, outbox pattern, and idempotent consumers provide eventual consistency without 2PC — preferred in microservice architectures where 2PC coupling is undesirable.""",
    "excerpt": "Two-phase commit protocol, blocking failure mode, three-phase commit, and modern alternatives like Spanner and Saga pattern.",
    "byline": "Distributed Transactions",
    "length": 930,
  },

  # ── Data Structures: Suffix Arrays ───────────────────────────────────────
  {
    "url": "https://dsa.example.com/suffix-array-construction",
    "title": "Suffix Arrays: SA-IS Construction, LCP Array, and String Search Applications",
    "site_name": "Data Structures & Algorithms",
    "content": """A suffix array is a sorted array of all suffixes of a string, represented as their starting indices. For string "banana", the suffixes sorted lexicographically give the suffix array [5,3,1,0,4,2] (indices of suffixes "a","ana","anana","banana","na","nana"). Search for any pattern P in O(|P| log n) using binary search.

SA-IS (Suffix Array Induced Sorting) constructs the suffix array in O(n) time and O(n) space, based on the observation that S-type and L-type suffixes can induce a sorted order. DC3/Skew algorithm also achieves O(n) via divide-and-conquer on every 3rd position.

The LCP (Longest Common Prefix) array stores the length of the longest common prefix between consecutive suffixes in sorted order. LCP[i] = length of LCP between SA[i-1] and SA[i]. Combined with the suffix array, the LCP array enables O(n log n) string query answering.

Applications: full-text search without a secondary index (grep, ripgrep use this internally); bioinformatics (DNA sequence alignment); data compression (Burrows-Wheeler Transform uses the suffix array). Suffix arrays are 3-5x more cache-friendly than suffix trees with equivalent query capability.""",
    "excerpt": "Suffix array SA-IS construction, LCP array, binary search for pattern matching, and applications in search and compression.",
    "byline": "String Algorithms",
    "length": 935,
  },

  # ── System Design: Replication ────────────────────────────────────────────
  {
    "url": "https://db.example.com/replication-strategies",
    "title": "Database Replication: Synchronous vs Asynchronous, Multi-Master, and Conflict Resolution",
    "site_name": "Database Engineering",
    "content": """Database replication copies data from a primary to one or more replicas for availability, read scaling, and disaster recovery. The fundamental trade-off is between consistency and latency.

Synchronous replication: primary waits for acknowledgment from at least one replica before confirming a write to the client. Guarantees no data loss on primary failure — the replica is always up-to-date. Cost: write latency increases by the primary-to-replica round trip. PostgreSQL's `synchronous_standby_names` enables this.

Asynchronous replication: primary acknowledges writes without waiting for replicas. Lower write latency, but a replica that's behind (replication lag) may miss recent writes if the primary fails and the replica is promoted. This causes data loss equal to the replication lag.

Multi-master (active-active) allows writes to any node. Conflicts arise when the same row is updated on two masters concurrently. Conflict resolution strategies: last-write-wins (by timestamp), merge (application-defined), or preventing conflicts by routing writes for a key to one master. CRDTs (Conflict-free Replicated Data Types) resolve conflicts mathematically for specific data types.""",
    "excerpt": "Database replication: synchronous vs asynchronous, multi-master conflicts, CRDTs, and PostgreSQL synchronous standby.",
    "byline": "High Availability",
    "length": 935,
  },

  # ── C++: Copy & Move Constructors ─────────────────────────────────────────
  {
    "url": "https://cpp.example.com/copy-constructor-rule-of-five",
    "title": "Rule of Five in C++: Copy, Move, Destructor, and When to Default vs Delete",
    "site_name": "Modern C++",
    "content": """The rule of five states: if you define any of the five special member functions (destructor, copy constructor, copy assignment, move constructor, move assignment), you should explicitly define or delete all five. This is because user-defining one suppresses compiler generation of others.

Copy constructor (`T(const T&)`): creates a new object as a copy. Deep copy for pointer members is necessary to avoid aliasing. Generated by default for trivially-copyable types; suppressed when a move constructor is user-defined.

Copy assignment (`T& operator=(const T&)`): copy-and-swap idiom is exception-safe and self-assignment-safe: take parameter by value (invokes copy constructor), swap internals, return *this. The old internals are destroyed by the temporary's destructor.

Rule of zero: if a class manages no resources (all members are RAII types), define none of the five — let the compiler generate them. This is the preferred design. The rule of five is for resource-managing classes (raw pointers, file handles, socket descriptors) before smart pointers are available.""",
    "excerpt": "C++ rule of five, copy constructor, copy-and-swap idiom, rule of zero, and when to =default vs =delete special members.",
    "byline": "C++ Object Model",
    "length": 920,
  },

  # ── System Design: Service Mesh ───────────────────────────────────────────
  {
    "url": "https://systems.example.com/service-mesh-sidecar",
    "title": "Service Mesh: Sidecar Pattern, mTLS, and Observability Without Code Changes",
    "site_name": "Systems Engineering",
    "content": """A service mesh intercepts all inter-service network traffic via sidecar proxies (typically Envoy) co-located with each service. The sidecar handles retries, circuit breaking, load balancing, mTLS, and distributed tracing — without changing application code.

The control plane (Istio, Linkerd) distributes configuration to the data plane (sidecars). Traffic policies (retry budgets, timeout, canary routing) are applied cluster-wide via CRDs. Istio's `VirtualService` enables weighted routing between service versions for canary deployments.

Mutual TLS (mTLS) authenticates both client and server, preventing lateral movement in a compromised cluster. The mesh issues short-lived certificates (SVID via SPIFFE) to each workload. Certificate rotation is automatic — no manual key management.

Cost: the sidecar adds ~7ms latency per hop and ~100MB RAM per pod. For high-throughput, latency-sensitive services, sidecars are prohibitive. eBPF-based meshes (Cilium) implement mesh features in the kernel, eliminating sidecar overhead while providing similar capabilities.""",
    "excerpt": "Service mesh sidecar pattern, Envoy data plane, Istio control plane, mTLS with SPIFFE, and eBPF alternatives.",
    "byline": "Platform Engineering",
    "length": 925,
  },

  # ── System Design: LSM Trees ─────────────────────────────────────────────
  {
    "url": "https://db.example.com/lsm-tree-compaction",
    "title": "LSM-Tree: Compaction Strategies, Write Amplification, and RocksDB Tuning",
    "site_name": "Database Engineering",
    "content": """Log-Structured Merge-Trees (LSM-Trees) convert random writes to sequential writes by buffering in a memtable and flushing to SSTables (immutable sorted files). Reads may check multiple SSTables, using Bloom filters to skip files that don't contain the key.

Compaction merges SSTables to reclaim space and maintain read performance. Leveled compaction (RocksDB default): each level has a size limit; L0 → L1 compaction merges overlapping key ranges, keeping L1 sorted with non-overlapping files. Read amplification is bounded (one SSTable per level). Write amplification is high (~30x).

Tiered/size-tiered compaction (Cassandra default): accumulate N similarly-sized SSTables, then compact them together. Write amplification is lower (~10x) but read amplification is higher — more SSTables to check per read. Suitable for write-heavy workloads.

RocksDB tuning: `write_buffer_size` (memtable size), `max_write_buffer_number` (number of memtables before flush stalls), `level0_slowdown_writes_trigger` / `level0_stop_writes_trigger` (L0 file count thresholds for write throttling). Bloom filter bits per key: 10 bits → 1% FPR is typically the right trade-off.""",
    "excerpt": "LSM-Tree structure, leveled vs tiered compaction, write/read amplification, and RocksDB tuning parameters.",
    "byline": "Storage Engine Design",
    "length": 950,
  },

  # ── C++: Type Traits ─────────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/type-traits-enable-if",
    "title": "Type Traits in C++: std::enable_if, std::conditional, and Detection Idiom",
    "site_name": "Modern C++",
    "content": """Type traits inspect and transform types at compile time. `<type_traits>` provides predicates (`is_integral<T>`, `is_pointer<T>`, `is_constructible<T, Args...>`) and transformations (`remove_const<T>`, `add_pointer<T>`, `common_type<T, U>`).

`std::enable_if<condition, T>`: if condition is true, defines member type `type = T`; otherwise no member type (substitution failure). Combined with SFINAE, enables/disables function template overloads. C++14 alias: `enable_if_t<condition, T>` drops `::type`.

`std::conditional<condition, T, F>::type` selects T if condition is true, F otherwise — the ternary operator for types. Used in implementing type-based dispatch without runtime branching.

The detection idiom (C++17 `std::void_t`): `template<typename T, typename = void> struct has_reserve : false_type {}; template<typename T> struct has_reserve<T, void_t<decltype(std::declval<T>().reserve(0))>> : true_type {};` — detects if T has a `reserve(size_t)` method. C++20 concepts provide a cleaner replacement.""",
    "excerpt": "std::enable_if for SFINAE, std::conditional for type selection, void_t detection idiom, and C++20 concept replacements.",
    "byline": "Advanced C++ Templates",
    "length": 915,
  },

  # ── System Design: Monitoring ─────────────────────────────────────────────
  {
    "url": "https://systems.example.com/observability-metrics-tracing",
    "title": "Observability: Metrics, Tracing, and Logs — The Three Pillars",
    "site_name": "Systems Engineering",
    "content": """Observability answers "what is the system doing right now?" Metrics quantify system state over time; traces follow a request across services; logs record discrete events. Together they enable debugging distributed systems without requiring reproduction.

Metrics (Prometheus model): time series of numeric values with labels. Counter (monotonically increasing), Gauge (arbitrary current value), Histogram (distribution across buckets), Summary (client-side quantiles). Alerting on rate of change (`rate(http_errors_total[5m]`) rather than raw values handles restarts cleanly.

Distributed tracing (OpenTelemetry): a trace represents a request's path across services, composed of spans. Each span has a `trace_id`, `span_id`, `parent_span_id`, start time, duration, and attributes. Sampling (1-10% of requests) reduces overhead while preserving tail latency visibility.

Structured logging (JSON): machine-parseable logs with consistent field names (`severity`, `message`, `trace_id`, `user_id`). Correlation: including `trace_id` in logs allows joining traces with logs for a specific request, enabling root cause analysis across the three pillars.""",
    "excerpt": "Observability with metrics (Prometheus), distributed tracing (OpenTelemetry), structured logging, and three-pillar correlation.",
    "byline": "Platform Reliability",
    "length": 920,
  },

  # ── System Design: API Design ─────────────────────────────────────────────
  {
    "url": "https://systems.example.com/rest-api-versioning",
    "title": "REST API Versioning Strategies: URL Path, Headers, and Sunset Policies",
    "site_name": "Systems Engineering",
    "content": """API versioning enables evolving a service contract without breaking existing clients. The three common strategies each have trade-offs.

URL path versioning (`/v1/users`, `/v2/users`) is the most common and most visible. Simple to test in browsers, cacheable, clearly separates versions. Downside: forces clients to update URLs on version bump; doesn't work well with hypermedia APIs (HATEOAS).

Header versioning (`Accept: application/vnd.api.v2+json` or `API-Version: 2`) keeps URLs stable and follows HTTP semantics. Harder to test without tooling; proxy caches may not respect custom headers unless Vary is set correctly.

Semantic versioning for APIs: major version = breaking change (new required field, removed endpoint), minor = additive (new optional field, new endpoint), patch = bug fix. Additive changes (new optional fields in request/response) are backwards-compatible and don't require a version bump.

Sunset policies: deprecated API versions should set `Sunset` and `Deprecation` response headers, informing clients of removal dates. 6-12 months notice is typical for internal APIs; 12-24 months for public APIs. Monitor version usage metrics to identify clients still on deprecated versions.""",
    "excerpt": "REST API versioning: URL path, header-based, semantic versioning for APIs, and sunset deprecation policies.",
    "byline": "API Governance",
    "length": 915,
  },

  # ── C++: STL Algorithms ──────────────────────────────────────────────────
  {
    "url": "https://cpp.example.com/stl-algorithms-complexity",
    "title": "STL Algorithm Complexity and When to Reach for Parallel Execution",
    "site_name": "Modern C++",
    "content": """C++ STL algorithms operate on iterators, enabling use with any container. Understanding complexity prevents performance surprises. `std::sort` is O(n log n) introsort (quicksort + heapsort fallback + insertion sort for small ranges). `std::stable_sort` is O(n log² n) or O(n log n) with extra memory.

`std::partial_sort(first, middle, last)` sorts only the first (middle-first) elements in O(n log k) — use when you need the k smallest elements without sorting everything. `std::nth_element` partitions around the nth element in O(n) — use to find the median without sorting.

C++17 parallel algorithms: `std::sort(std::execution::par, ...)` uses a parallel backend (TBB on Intel, MSVC's parallel STL). Not all algorithms benefit from parallelism — only O(n log n)+ algorithms with independent operations and large n. For small n, the thread-launch overhead dominates.

`std::transform_reduce` (parallel reduce): `transform_reduce(par, first, last, 0, std::plus{}, f)` maps f over range and reduces with addition — embarrassingly parallel. Implements mapreduce for in-process aggregation.""",
    "excerpt": "STL algorithm complexity, partial_sort vs nth_element, C++17 parallel execution policies, and transform_reduce.",
    "byline": "C++ Performance",
    "length": 920,
  },

  # ── System Design: Vector Databases ──────────────────────────────────────
  {
    "url": "https://db.example.com/vector-database-hnsw",
    "title": "Vector Databases: HNSW Index, Approximate Nearest Neighbors, and RAG Architecture",
    "site_name": "Database Engineering",
    "content": """Vector databases store high-dimensional embeddings and answer approximate nearest neighbor (ANN) queries: find the k vectors closest to a query vector by cosine similarity or Euclidean distance. Exact nearest neighbor search is O(n*d) — impractical for millions of 1536-dimensional OpenAI embeddings.

HNSW (Hierarchical Navigable Small World) is the dominant ANN index. It builds a layered graph: upper layers are sparse long-range connections; lower layers are dense short-range connections. Search: greedy traversal from a random upper-layer entry point, descending to denser layers near the query.

HNSW parameters: `M` (max connections per node, 16-64), `ef_construction` (beam width during index build, 100-200), `ef_search` (beam width during query, 50-200). Higher M and ef improve recall at the cost of memory and query time.

RAG (Retrieval-Augmented Generation) architecture: embed documents at index time, store in vector DB; embed the query at query time, retrieve top-k similar documents, pass to LLM as context. pgvector (PostgreSQL extension) provides an HNSW index, enabling RAG within an existing Postgres deployment without a separate vector database.""",
    "excerpt": "Vector databases, HNSW index structure, ANN query performance, HNSW parameter tuning, and RAG with pgvector.",
    "byline": "ML Infrastructure",
    "length": 940,
  },

]

# ── 3. Save articles ─────────────────────────────────────────────────────────
print(f"\n[START] Saving {len(ARTICLES)} articles...\n")
ok = fail = 0

for i, art in enumerate(ARTICLES, 1):
    try:
        res = requests.post(f"{API}/api/articles", json=art, headers=headers, timeout=10)
        if res.status_code in (200, 201):
            data = res.json()
            status = "NEW" if data.get("is_new") else "DUP"
            print(f"[{i:03d}] {status} — {art['title'][:60]}")
            ok += 1
        else:
            print(f"[{i:03d}] FAIL {res.status_code} — {art['title'][:60]}: {res.text[:80]}")
            fail += 1
    except Exception as e:
        print(f"[{i:03d}] ERROR — {art['title'][:60]}: {e}")
        fail += 1
    time.sleep(0.3)

print(f"\n[DONE] {ok} saved, {fail} failed out of {len(ARTICLES)} total.")
