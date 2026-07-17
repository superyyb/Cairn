"""Seed remaining articles directly into the DB, bypassing the API rate limit."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.models.article, app.models.chat_session, app.models.oauth_account
import app.models.refresh_token, app.models.tag, app.models.tag_merge
from app.core.database import SessionLocal
from app.core.utils import hash_url
from app.models.article import Article
from app.models.user import User

EMAIL = "superyy0721@gmail.com"
USER_ID = 3

REMAINING = [
  {
    "url": "https://cpp.example.com/vtable-virtual-dispatch",
    "title": "Virtual Dispatch in C++: vtable Layout, Virtual Inheritance, and Devirtualization",
    "site_name": "Modern C++",
    "content": """Virtual dispatch enables polymorphism: calling a virtual function through a base pointer invokes the derived class's implementation. Each class with virtual functions has a vtable — a static array of function pointers. Each object contains a hidden vptr pointing to its class's vtable, typically as the first field.

Calling a virtual function: dereference vptr, index into vtable, call the function pointer. This is an indirect call — one more level of indirection than a direct call. The cost: ~4-7 ns on modern hardware due to branch misprediction and I-cache pressure. Direct calls are ~1 ns.

Virtual inheritance (for diamond inheritance) adds another level: a vptr points to a virtual base table, adding overhead. Avoid multiple virtual inheritance in performance-critical code.

Devirtualization: the compiler can eliminate virtual dispatch when the dynamic type is known at compile time (object is stack-allocated or final class). `final` keyword hints that no further subclassing occurs, enabling the optimizer to devirtualize call sites. Profile-guided optimization (PGO) devirtualizes based on runtime type frequency.""",
    "excerpt": "C++ virtual dispatch, vtable layout, vptr overhead, virtual inheritance, and compiler devirtualization techniques.",
    "byline": "C++ Internals", "lang": "en", "length": 925,
  },
  {
    "url": "https://cpp.example.com/unordered-map-internals",
    "title": "std::unordered_map Internals: Bucket Array, Load Factor, and Performance Pitfalls",
    "site_name": "Modern C++",
    "content": """std::unordered_map is a hash map using separate chaining. The bucket array is a vector of lists. Load factor = elements / buckets; when it exceeds max_load_factor (default 1.0), rehashing doubles the bucket count and redistributes all elements — O(n) amortized O(1).

Performance pitfalls: (1) Rehashing invalidates all iterators and references — never hold iterators across insertions without reserving capacity first with reserve(n). (2) String keys hash to O(|key|), making short string optimization (SSO) critical for short keys. (3) The default hash for integers on MSVC uses the identity function — sequential integer keys cluster into the same few buckets, degrading to O(n) lookup.

Custom hash functions improve performance for common types. For integer keys, a multiplicative hash or xor-shift hash distributes better. For strings, FNV-1a or xxHash outperform std::hash<std::string> in throughput.

absl::flat_hash_map (Abseil) and robin_hood::unordered_map use open addressing with linear probing — significantly better cache performance than separate chaining, often 3-5x faster for small, hot maps.""",
    "excerpt": "std::unordered_map internals, rehashing, iterator invalidation, bad hash functions, and faster alternatives.",
    "byline": "STL Performance", "lang": "en", "length": 940,
  },
  {
    "url": "https://cpp.example.com/lambda-captures-generics",
    "title": "C++ Lambda Deep Dive: Capture Modes, Generic Lambdas, and Immediately Invoked",
    "site_name": "Modern C++",
    "content": """A C++ lambda is syntactic sugar for a compiler-generated anonymous struct with an overloaded operator(). Captures become member variables. [=] captures all locals by value; [&] by reference. Dangling references: [&] capturing a local that outlives the lambda causes undefined behavior.

Init captures (C++14): [x = std::move(obj)] captures a move-only type. [self = shared_from_this()] captures a shared_ptr in async callbacks, extending lifetime. Mutable lambdas ([x]() mutable { x++; }) allow modifying value-captured variables.

Generic lambdas (C++14): auto f = [](auto x) { return x * 2; } — each call with a different type instantiates a new operator() template. C++20 allows explicit template parameters.

Immediately invoked lambda expressions (IILE): auto val = [&]() -> int { /* complex init */ return result; }(); — useful for complex initialization of const variables. More readable than immediately-invoked function expressions.""",
    "excerpt": "C++ lambda captures, init captures for move-only types, generic lambdas, mutable lambdas, and immediately invoked patterns.",
    "byline": "C++ Functional", "lang": "en", "length": 915,
  },
  {
    "url": "https://cpp.example.com/constexpr-compile-time",
    "title": "constexpr in C++: Compile-Time Evaluation, consteval, and Constant Expressions",
    "site_name": "Modern C++",
    "content": """constexpr functions can be evaluated at compile time when called with constant arguments. C++11 constexpr was restrictive (single return statement). C++14 removed most restrictions: loops, local variables, and multiple statements are allowed. C++20 allows constexpr new/delete, std::vector, and std::string.

A constexpr function evaluated at compile time produces a compile-time constant usable in array sizes, template arguments, and non-type template parameters. If called with non-constant arguments, it evaluates at runtime like a regular function.

consteval (C++20) mandates compile-time evaluation — the function cannot be called at runtime. Useful for functions that must produce constants (e.g., compile-time hash tables). constinit ensures a variable is zero-initialized at compile time without implying immutability (unlike constexpr variables).

Compile-time lookup tables: constexpr arrays computed once via immediately invoked lambdas — zero runtime cost.""",
    "excerpt": "C++ constexpr for compile-time evaluation, consteval for compile-time-only functions, constinit, and compile-time lookup tables.",
    "byline": "C++ Compile-Time", "lang": "en", "length": 920,
  },
  {
    "url": "https://cpp.example.com/cpp20-concepts",
    "title": "C++20 Concepts: Constraining Templates and Improving Error Messages",
    "site_name": "Modern C++",
    "content": """Concepts name and constrain template requirements, replacing SFINAE with readable syntax. A concept is a predicate on types evaluated at compile time: template<typename T> concept Integral = std::is_integral_v<T>. Usage: template<Integral T> T gcd(T a, T b) — clearer than enable_if.

Abbreviated function templates: void f(std::integral auto x) is syntactic sugar for template<std::integral T> void f(T x). auto parameters anywhere in a function signature introduce template parameters.

Requires expressions allow compound constraints: requires { { expr } -> SomeConcept; } checks that expr is valid and its type satisfies SomeConcept. The standard library defines concepts in <concepts>: std::same_as, std::convertible_to, std::invocable, std::ranges::range.

Error messages: with SFINAE, substitution failures produce incomprehensible error dumps. With concepts, violations produce a clear "T does not satisfy constraint Integral" message — the primary practical benefit for most code.""",
    "excerpt": "C++20 concepts for template constraints, abbreviated function templates, requires expressions, and improved error messages.",
    "byline": "C++20 Features", "lang": "en", "length": 925,
  },
  {
    "url": "https://cpp.example.com/cpp20-ranges",
    "title": "C++20 Ranges: Views, Pipelines, and Lazy Evaluation",
    "site_name": "Modern C++",
    "content": """C++20 ranges extend the STL algorithm model with composable, lazy views. A range is anything with begin()/end(); a view is a lightweight, non-owning range with O(1) copy. Views compose via |: vec | std::views::filter(even) | std::views::transform(square) creates a lazy pipeline evaluated only when iterated.

Laziness: each element passes through the pipeline on demand — no intermediate collections. This enables processing of infinite ranges: std::views::iota(0) is an infinite range of integers; views::take(10) limits to 10 elements.

Range algorithms in <algorithm> accept range objects directly: std::ranges::sort(vec) instead of std::sort(vec.begin(), vec.end()). They also accept projections: std::ranges::sort(people, {}, &Person::age) sorts by age field without a custom comparator.

Sentinels replace the end iterator: any type satisfying sentinel_for<Iter> can serve as the end marker, enabling null-terminated C string ranges and other non-sized ranges.""",
    "excerpt": "C++20 ranges: composable lazy views, pipeline syntax, infinite ranges, range algorithms with projections, and sentinels.",
    "byline": "C++20 Ranges Library", "lang": "en", "length": 930,
  },
  {
    "url": "https://systems.example.com/load-balancing-algorithms",
    "title": "Load Balancing Algorithms: Round-Robin, Least Connections, and Power of Two Choices",
    "site_name": "Systems Engineering",
    "content": """Load balancing distributes incoming requests across backend servers to maximize throughput and minimize latency. The choice of algorithm significantly affects performance under heterogeneous load.

Round-robin cycles through servers in order. Simple and CPU-efficient, but ignores server load — a slow server receiving the same request rate as a fast one becomes a bottleneck. Weighted round-robin assigns proportional request rates based on server capacity.

Least-connections routes to the server with the fewest active connections, approximating shortest queue. Accurate but requires tracking connection counts; under high request rates, the tracking becomes a bottleneck. Least-response-time extends this with latency weighting.

Power of Two Choices (P2C): pick two servers at random, send to the one with fewer connections. This achieves O(log log n) maximum load while requiring only two choices — no global minimum scan. Used in NGINX, HAProxy's leastconn with random sampling.""",
    "excerpt": "Load balancing: round-robin, least connections, weighted variants, and Power of Two Choices algorithm.",
    "byline": "Networking Infrastructure", "lang": "en", "length": 905,
  },
  {
    "url": "https://systems.example.com/event-sourcing-cqrs",
    "title": "Event Sourcing and CQRS: Append-Only Events as the Source of Truth",
    "site_name": "Systems Engineering",
    "content": """Event sourcing stores state as a sequence of events rather than current state. The current state is derived by replaying events. Benefits: complete audit trail, ability to replay history, temporal queries.

CQRS (Command Query Responsibility Segregation) separates the write model (commands → events) from the read model (projections of events optimized for queries). Read models are eventually consistent with the event store.

Snapshots prevent excessive replay time: periodically store a snapshot of current state, replay only events after the snapshot.

Challenges: event schema evolution (old events must be readable with new code — use upcasting or versioned events); eventual consistency; complex queries (joins across multiple aggregates require denormalized projections). Event sourcing adds significant complexity — apply only when audit trail or temporal queries are genuine requirements.""",
    "excerpt": "Event sourcing as append-only store, CQRS for separate read/write models, snapshots, schema evolution, and when to avoid it.",
    "byline": "Domain-Driven Design", "lang": "en", "length": 935,
  },
  {
    "url": "https://dsa.example.com/skip-list-probabilistic",
    "title": "Skip Lists: Probabilistic Balancing and Concurrent Skip Lists",
    "site_name": "Data Structures & Algorithms",
    "content": """A skip list is a layered linked list where higher layers skip over more elements. The bottom layer is a complete sorted linked list; each element is promoted to higher layers with probability p (typically 0.5 or 0.25). Expected height is O(log n). Search traverses from the top layer down, skipping large ranges before descending.

Expected time complexity: O(log n) for search, insert, delete — same as balanced BSTs. But skip lists are simpler to implement and to modify for concurrent access. The insertion algorithm is local: find the position, insert in the bottom layer, promote with coin flips. No global rebalancing.

Concurrent skip lists: the lock-free variant uses CAS to mark nodes as logically deleted before physical removal. java.util.concurrent.ConcurrentSkipListMap is a non-blocking, linearizable ordered map. Database systems (Redis ZSET, MemSQL) choose skip lists over trees for concurrent ordered access.

Cache performance: skip lists have worse cache behavior than B-Trees because nodes are individually heap-allocated. For simpler concurrent use cases, skip lists win on implementation complexity.""",
    "excerpt": "Skip list probabilistic balancing, O(log n) complexity, lock-free concurrent skip lists, and comparison with B-Trees.",
    "byline": "Data Structures", "lang": "en", "length": 920,
  },
  {
    "url": "https://db.example.com/wal-write-ahead-log",
    "title": "Write-Ahead Logging: Durability, Recovery, and LSM-Tree WAL",
    "site_name": "Database Engineering",
    "content": """Write-Ahead Logging (WAL) ensures durability by writing changes to a log before applying them to data pages. On recovery after a crash, the database replays WAL records to restore committed transactions and undo uncommitted ones.

PostgreSQL's WAL is used for: crash recovery, streaming replication (WAL records streamed to standbys), point-in-time recovery (PITR — replay WAL from a base backup to any point in time), and logical replication (parse WAL for row-level changes).

WAL write modes affect performance: synchronous commit (synchronous_commit = on) fsync's WAL on every commit — safe but slow. Asynchronous commit skips fsync — up to wal_writer_delay of data loss risk but dramatically higher throughput.

LSM-Trees (RocksDB, Cassandra) use a WAL differently: writes go to WAL + in-memory memtable. When the memtable fills, it's flushed to an SSTable on disk. The WAL is only needed for recovery — once an SSTable is written, its WAL records can be garbage collected.""",
    "excerpt": "Write-Ahead Log for crash recovery, PostgreSQL WAL for replication and PITR, synchronous vs async commit, and LSM WAL.",
    "byline": "Database Storage", "lang": "en", "length": 945,
  },
  {
    "url": "https://systems.example.com/backpressure-flow-control",
    "title": "Backpressure and Flow Control: Preventing Cascade Failures in Pipelines",
    "site_name": "Systems Engineering",
    "content": """Backpressure is a flow control mechanism where downstream stages signal upstream stages to slow down when they're overwhelmed. Without it, fast producers overwhelm slow consumers, causing unbounded queue growth, memory exhaustion, and cascade failures.

In reactive systems, backpressure propagates demand: a subscriber requests N items, and the publisher sends at most N. This is the core of Reactive Streams / Project Reactor / RxJava 2.

In TCP, the receive window limits how much data can be in flight. When the receiver's buffer fills, the window shrinks to zero, stalling the sender. Application-level protocols implement similar mechanisms: GRPC uses HTTP/2 flow control; Kafka consumers control read rate via max.poll.records.

In thread pools, backpressure manifests as bounded queues with rejection. CallerRunsPolicy in Java's ThreadPoolExecutor runs the task on the submitting thread when the queue is full — naturally throttling the producer by making it do work instead of submitting.""",
    "excerpt": "Backpressure for flow control in reactive systems, reactive streams demand model, TCP window, and caller-runs policy.",
    "byline": "Systems Reliability", "lang": "en", "length": 910,
  },
  {
    "url": "https://systems.example.com/two-phase-commit",
    "title": "Two-Phase Commit: Protocol, Failure Modes, and Why It's Rarely Used",
    "site_name": "Systems Engineering",
    "content": """Two-phase commit (2PC) achieves atomic commitment across multiple participants. Phase 1 (prepare): coordinator asks all participants to vote yes/no. Phase 2 (commit/abort): if all voted yes, coordinator sends commit; if any voted no, sends abort.

Failure modes: if the coordinator fails after participants voted yes but before sending commit, participants are blocked indefinitely — they've voted yes and can't unilaterally commit or abort (the blocking problem).

Modern distributed databases avoid 2PC. Google Spanner uses TrueTime and Paxos consensus per shard, with 2PC only for cross-shard transactions. CockroachDB uses parallel commits: a transaction is atomic once its record is replicated, without a separate commit round-trip.

The Saga pattern, outbox pattern, and idempotent consumers provide eventual consistency without 2PC — preferred in microservice architectures where 2PC coupling is undesirable.""",
    "excerpt": "Two-phase commit protocol, blocking failure mode, three-phase commit, and modern alternatives like Spanner and Saga pattern.",
    "byline": "Distributed Transactions", "lang": "en", "length": 930,
  },
  {
    "url": "https://dsa.example.com/suffix-array-construction",
    "title": "Suffix Arrays: SA-IS Construction, LCP Array, and String Search Applications",
    "site_name": "Data Structures & Algorithms",
    "content": """A suffix array is a sorted array of all suffixes of a string, represented as their starting indices. Search for any pattern P in O(|P| log n) using binary search on the suffix array.

SA-IS (Suffix Array Induced Sorting) constructs the suffix array in O(n) time and O(n) space, based on the observation that S-type and L-type suffixes can induce a sorted order. DC3/Skew algorithm also achieves O(n) via divide-and-conquer.

The LCP (Longest Common Prefix) array stores the length of the longest common prefix between consecutive suffixes in sorted order. Combined with the suffix array, the LCP array enables efficient string query answering.

Applications: full-text search without a secondary index (grep, ripgrep use this internally); bioinformatics (DNA sequence alignment); data compression (Burrows-Wheeler Transform uses the suffix array). Suffix arrays are 3-5x more cache-friendly than suffix trees with equivalent query capability.""",
    "excerpt": "Suffix array SA-IS construction, LCP array, binary search for pattern matching, and applications in search and compression.",
    "byline": "String Algorithms", "lang": "en", "length": 935,
  },
  {
    "url": "https://db.example.com/replication-strategies",
    "title": "Database Replication: Synchronous vs Asynchronous, Multi-Master, and Conflict Resolution",
    "site_name": "Database Engineering",
    "content": """Database replication copies data from a primary to one or more replicas for availability, read scaling, and disaster recovery. The fundamental trade-off is between consistency and latency.

Synchronous replication: primary waits for acknowledgment from at least one replica before confirming a write to the client. Guarantees no data loss on primary failure. Cost: write latency increases by the primary-to-replica round trip. PostgreSQL's synchronous_standby_names enables this.

Asynchronous replication: primary acknowledges writes without waiting for replicas. Lower write latency, but a replica that's behind may miss recent writes if the primary fails — data loss equal to the replication lag.

Multi-master (active-active) allows writes to any node. Conflicts arise when the same row is updated on two masters concurrently. Conflict resolution strategies: last-write-wins (by timestamp), merge (application-defined). CRDTs (Conflict-free Replicated Data Types) resolve conflicts mathematically for specific data types.""",
    "excerpt": "Database replication: synchronous vs asynchronous, multi-master conflicts, CRDTs, and PostgreSQL synchronous standby.",
    "byline": "High Availability", "lang": "en", "length": 935,
  },
  {
    "url": "https://cpp.example.com/copy-constructor-rule-of-five",
    "title": "Rule of Five in C++: Copy, Move, Destructor, and When to Default vs Delete",
    "site_name": "Modern C++",
    "content": """The rule of five states: if you define any of the five special member functions (destructor, copy constructor, copy assignment, move constructor, move assignment), you should explicitly define or delete all five.

Copy constructor (T(const T&)): creates a new object as a copy. Deep copy for pointer members is necessary to avoid aliasing. Generated by default for trivially-copyable types; suppressed when a move constructor is user-defined.

Copy assignment (T& operator=(const T&)): copy-and-swap idiom is exception-safe and self-assignment-safe: take parameter by value (invokes copy constructor), swap internals, return *this.

Rule of zero: if a class manages no resources (all members are RAII types), define none of the five — let the compiler generate them. This is the preferred design. The rule of five is for resource-managing classes (raw pointers, file handles, socket descriptors) before smart pointers are available.""",
    "excerpt": "C++ rule of five, copy constructor, copy-and-swap idiom, rule of zero, and when to =default vs =delete special members.",
    "byline": "C++ Object Model", "lang": "en", "length": 920,
  },
  {
    "url": "https://systems.example.com/service-mesh-sidecar",
    "title": "Service Mesh: Sidecar Pattern, mTLS, and Observability Without Code Changes",
    "site_name": "Systems Engineering",
    "content": """A service mesh intercepts all inter-service network traffic via sidecar proxies (typically Envoy) co-located with each service. The sidecar handles retries, circuit breaking, load balancing, mTLS, and distributed tracing — without changing application code.

The control plane (Istio, Linkerd) distributes configuration to the data plane (sidecars). Traffic policies (retry budgets, timeout, canary routing) are applied cluster-wide via CRDs. Istio's VirtualService enables weighted routing between service versions for canary deployments.

Mutual TLS (mTLS) authenticates both client and server, preventing lateral movement in a compromised cluster. The mesh issues short-lived certificates (SVID via SPIFFE) to each workload.

Cost: the sidecar adds ~7ms latency per hop and ~100MB RAM per pod. For high-throughput, latency-sensitive services, sidecars are prohibitive. eBPF-based meshes (Cilium) implement mesh features in the kernel, eliminating sidecar overhead.""",
    "excerpt": "Service mesh sidecar pattern, Envoy data plane, Istio control plane, mTLS with SPIFFE, and eBPF alternatives.",
    "byline": "Platform Engineering", "lang": "en", "length": 925,
  },
  {
    "url": "https://db.example.com/lsm-tree-compaction",
    "title": "LSM-Tree: Compaction Strategies, Write Amplification, and RocksDB Tuning",
    "site_name": "Database Engineering",
    "content": """Log-Structured Merge-Trees (LSM-Trees) convert random writes to sequential writes by buffering in a memtable and flushing to SSTables (immutable sorted files). Reads may check multiple SSTables, using Bloom filters to skip files that don't contain the key.

Compaction merges SSTables to reclaim space and maintain read performance. Leveled compaction (RocksDB default): each level has a size limit; L0 → L1 compaction merges overlapping key ranges, keeping L1 sorted with non-overlapping files. Read amplification is bounded. Write amplification is high (~30x).

Tiered/size-tiered compaction (Cassandra default): accumulate N similarly-sized SSTables, then compact them together. Write amplification is lower (~10x) but read amplification is higher. Suitable for write-heavy workloads.

RocksDB tuning: write_buffer_size (memtable size), max_write_buffer_number (number of memtables before flush stalls), level0_slowdown_writes_trigger / level0_stop_writes_trigger (L0 file count thresholds for write throttling).""",
    "excerpt": "LSM-Tree structure, leveled vs tiered compaction, write/read amplification, and RocksDB tuning parameters.",
    "byline": "Storage Engine Design", "lang": "en", "length": 950,
  },
  {
    "url": "https://cpp.example.com/type-traits-enable-if",
    "title": "Type Traits in C++: std::enable_if, std::conditional, and Detection Idiom",
    "site_name": "Modern C++",
    "content": """Type traits inspect and transform types at compile time. <type_traits> provides predicates (is_integral<T>, is_pointer<T>, is_constructible<T, Args...>) and transformations (remove_const<T>, add_pointer<T>, common_type<T, U>).

std::enable_if<condition, T>: if condition is true, defines member type `type = T`; otherwise no member type (substitution failure). Combined with SFINAE, enables/disables function template overloads.

std::conditional<condition, T, F>::type selects T if condition is true, F otherwise — the ternary operator for types.

The detection idiom (C++17 std::void_t) detects if T has a specific member function: has_reserve<T> is true if T has a reserve(size_t) method. C++20 concepts provide a cleaner replacement for these patterns.""",
    "excerpt": "std::enable_if for SFINAE, std::conditional for type selection, void_t detection idiom, and C++20 concept replacements.",
    "byline": "Advanced C++ Templates", "lang": "en", "length": 915,
  },
  {
    "url": "https://systems.example.com/observability-metrics-tracing",
    "title": "Observability: Metrics, Tracing, and Logs — The Three Pillars",
    "site_name": "Systems Engineering",
    "content": """Observability answers "what is the system doing right now?" Metrics quantify system state over time; traces follow a request across services; logs record discrete events. Together they enable debugging distributed systems without requiring reproduction.

Metrics (Prometheus model): time series of numeric values with labels. Counter (monotonically increasing), Gauge (arbitrary current value), Histogram (distribution across buckets). Alerting on rate of change rather than raw values handles restarts cleanly.

Distributed tracing (OpenTelemetry): a trace represents a request's path across services, composed of spans. Each span has a trace_id, span_id, parent_span_id, start time, duration, and attributes. Sampling (1-10% of requests) reduces overhead while preserving tail latency visibility.

Structured logging (JSON): machine-parseable logs with consistent field names. Correlation: including trace_id in logs allows joining traces with logs for a specific request, enabling root cause analysis across the three pillars.""",
    "excerpt": "Observability with metrics (Prometheus), distributed tracing (OpenTelemetry), structured logging, and three-pillar correlation.",
    "byline": "Platform Reliability", "lang": "en", "length": 920,
  },
  {
    "url": "https://systems.example.com/rest-api-versioning",
    "title": "REST API Versioning Strategies: URL Path, Headers, and Sunset Policies",
    "site_name": "Systems Engineering",
    "content": """API versioning enables evolving a service contract without breaking existing clients. The three common strategies each have trade-offs.

URL path versioning (/v1/users, /v2/users) is the most common and most visible. Simple to test in browsers, cacheable, clearly separates versions.

Header versioning (Accept: application/vnd.api.v2+json or API-Version: 2) keeps URLs stable and follows HTTP semantics. Harder to test without tooling.

Semantic versioning for APIs: major version = breaking change (new required field, removed endpoint), minor = additive (new optional field, new endpoint), patch = bug fix.

Sunset policies: deprecated API versions should set Sunset and Deprecation response headers, informing clients of removal dates. 6-12 months notice is typical for internal APIs; 12-24 months for public APIs.""",
    "excerpt": "REST API versioning: URL path, header-based, semantic versioning for APIs, and sunset deprecation policies.",
    "byline": "API Governance", "lang": "en", "length": 915,
  },
  {
    "url": "https://cpp.example.com/stl-algorithms-complexity",
    "title": "STL Algorithm Complexity and When to Reach for Parallel Execution",
    "site_name": "Modern C++",
    "content": """C++ STL algorithms operate on iterators, enabling use with any container. std::sort is O(n log n) introsort (quicksort + heapsort fallback + insertion sort for small ranges). std::stable_sort is O(n log² n) or O(n log n) with extra memory.

std::partial_sort(first, middle, last) sorts only the first (middle-first) elements in O(n log k) — use when you need the k smallest elements without sorting everything. std::nth_element partitions around the nth element in O(n) — use to find the median without sorting.

C++17 parallel algorithms: std::sort(std::execution::par, ...) uses a parallel backend (TBB on Intel, MSVC's parallel STL). Not all algorithms benefit from parallelism — only O(n log n)+ algorithms with independent operations and large n.

std::transform_reduce (parallel reduce): maps f over range and reduces with a binary operation — embarrassingly parallel. Implements mapreduce for in-process aggregation.""",
    "excerpt": "STL algorithm complexity, partial_sort vs nth_element, C++17 parallel execution policies, and transform_reduce.",
    "byline": "C++ Performance", "lang": "en", "length": 920,
  },
  {
    "url": "https://db.example.com/vector-database-hnsw",
    "title": "Vector Databases: HNSW Index, Approximate Nearest Neighbors, and RAG Architecture",
    "site_name": "Database Engineering",
    "content": """Vector databases store high-dimensional embeddings and answer approximate nearest neighbor (ANN) queries: find the k vectors closest to a query vector by cosine similarity or Euclidean distance. Exact nearest neighbor search is O(n*d) — impractical for millions of 1536-dimensional OpenAI embeddings.

HNSW (Hierarchical Navigable Small World) is the dominant ANN index. It builds a layered graph: upper layers are sparse long-range connections; lower layers are dense short-range connections. Search: greedy traversal from a random upper-layer entry point, descending to denser layers near the query.

HNSW parameters: M (max connections per node, 16-64), ef_construction (beam width during index build, 100-200), ef_search (beam width during query, 50-200). Higher M and ef improve recall at the cost of memory and query time.

RAG (Retrieval-Augmented Generation) architecture: embed documents at index time, store in vector DB; embed the query at query time, retrieve top-k similar documents, pass to LLM as context. pgvector (PostgreSQL extension) provides an HNSW index, enabling RAG within an existing Postgres deployment.""",
    "excerpt": "Vector databases, HNSW index structure, ANN query performance, HNSW parameter tuning, and RAG with pgvector.",
    "byline": "ML Infrastructure", "lang": "en", "length": 940,
  },
]

db = SessionLocal()
ok = skip = 0

for art in REMAINING:
    url_str = str(art["url"])
    url_hash = hash_url(url_str)
    existing = db.query(Article).filter(
        Article.user_id == USER_ID,
        Article.url_hash == url_hash,
    ).first()
    if existing:
        print(f"[DUP] {art['title'][:60]}")
        skip += 1
        continue
    new_art = Article(
        user_id=USER_ID,
        url=url_str,
        url_hash=url_hash,
        title=art["title"],
        content=art.get("content"),
        excerpt=art.get("excerpt"),
        byline=art.get("byline"),
        site_name=art.get("site_name"),
        lang=art.get("lang", "en"),
        length=art.get("length"),
    )
    db.add(new_art)
    db.commit()
    print(f"[ OK] {art['title'][:60]}")
    ok += 1

db.close()
print(f"\nDone: {ok} new, {skip} skipped.")
