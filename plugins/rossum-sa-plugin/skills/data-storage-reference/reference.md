# Rossum Data Storage API Reference

Rossum's **Data Storage** service is a MongoDB-compatible data layer exposed as a REST API. It provides document-oriented storage with collections, indexes, and full support for MongoDB query patterns including `find`, `aggregate`, and `bulk_write`.

- **Base URL:** `/svc/data-storage`
- **Auth:** Bearer token (`Authorization: Bearer <token>`)
- **All endpoints use POST** (except healthz and operation status)
- **All request/response bodies are JSON**
- **Common error codes:** 400, 401, 403, 404, 422 -- all return `ErrorResponse {code, message}`

---

## Key Concepts

- **Collections** are scoped per organization (the org is inferred from the bearer token).
- **Documents** are arbitrary JSON objects. If `_id` is omitted on insert, a MongoDB `ObjectId` is generated.
- **Filters, queries, projections, sorts, updates, and pipelines** all use standard MongoDB syntax.
- **Async operations** return `202 Accepted` with an operation ID. Poll status via `/api/v1/operation_status/{operation_id}`.
- **`waitForFullWrite`** (boolean, default `false`) -- when `true`, write operations wait for full acknowledgement before responding.
- **Runtime limit** on `find` and `aggregate`: 120 seconds.

---

## Healthz

### `GET /api/healthz` -- Health Check
No auth required. Returns `HealthzResponse`.

**Response 200:**
| Field | Type | Description |
|---|---|---|
| code_version_hash | string | Current deployment hash |
| code_project_path | string | Project path |

---

## Status

### `GET /api/v1/operation_status/{operation_id}` -- Check Async Operation Status
Returns the status of an asynchronous operation (e.g. bulk_write, drop collection, create index).

**Path params:** `operation_id` (string, required)

**Response 200:** `OperationStatusResponse` containing an `Operation` object:
| Field | Type | Description |
|---|---|---|
| _id | string | Operation ID |
| user_id | string | User who initiated |
| status | enum | `CREATED`, `RUNNING`, `FINISHED`, `FAILED` |
| operation | string | Operation type |
| last_updated | EJSONDate | Last status change time |
| error_message | string? | Error details if FAILED |

---

## Collection Operations

All endpoints: `POST`, auth required.

### `POST /api/v1/collections/list` -- List Collections
**Request body (`ListCollectionsRequest`):**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| filter | object? | no | null | MongoDB filter for collection metadata |
| nameOnly | bool | no | true | Return only names (strings) or full metadata (objects) |

**Response 200:** `ListObjectsResponse` -- `result` is `string[]` (if nameOnly) or `object[]`.

---

### `POST /api/v1/collections/create` -- Create Collection
**Request body (`CreateCollectionRequest`):**
| Field | Type | Required | Description |
|---|---|---|---|
| collectionName | string | yes | Name of the collection |
| options | object | no | MongoDB collection options |

**Response 200:** `SuccessResponse`

---

### `POST /api/v1/collections/rename` -- Rename Collection
**Request body (`RenameCollectionRequest`):**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| collectionName | string | yes | -- | Current name |
| target | string | yes | -- | New name |
| dropTarget | bool | no | false | Drop the target collection if it already exists |

**Response 200:** `SuccessResponse`

---

### `POST /api/v1/collections/drop` -- Drop Collection (ASYNC)
Drops the collection and all its indexes. Returns 202.

**Request body (`DropCollectionRequest`):**
| Field | Type | Required |
|---|---|---|
| collectionName | string | yes |

**Response 202:** `AcceptResponse` -- poll via operation status endpoint.

---

## Data Operations (CRUD + Query)

All endpoints: `POST`, auth required. These are the most heavily used endpoints.

### `POST /api/v1/data/insert_one` -- Insert One Document
Implicitly creates the collection if it does not exist.

**Request body (`InsertOneRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| document | object | yes | -- |
| waitForFullWrite | bool | no | false |

**Response 200:** `InsertOneResponse` -- `result.inserted_id` contains the `_id` of the inserted document (auto-generated ObjectId if not provided).

---

### `POST /api/v1/data/insert_many` -- Insert Many Documents
Implicitly creates the collection if it does not exist.

**Request body (`InsertManyRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| documents | object[] | yes | -- |
| ordered | bool | no | false |
| waitForFullWrite | bool | no | false |

**Response 200:** `InsertManyResponse` -- `result.inserted_ids` is an array of `_id` values.

---

### `POST /api/v1/data/update_one` -- Update One Document
**Request body (`UpdateOneRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| filter | object | yes | -- |
| update | object or object[] | yes | -- |
| options | object | no | -- |
| waitForFullWrite | bool | no | false |

`update` accepts a MongoDB update document (e.g. `{"$set": {"field": "value"}}`) or an aggregation pipeline (array of stages).

**Response 200:** `UpdateResponse` -- `result` contains `matched_count`, `modified_count`, `upserted_id`.

---

### `POST /api/v1/data/update_many` -- Update Many Documents
Same schema as `update_one` (`UpdateManyRequest`), same response. Applies update to all matching documents.

---

### `POST /api/v1/data/delete_one` -- Delete One Document
**Request body (`DeleteRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| filter | object | yes | -- |
| options | object | no | -- |
| waitForFullWrite | bool | no | false |

**Response 200:** `DeleteResponse` -- `result.deleted_count` (integer).

---

### `POST /api/v1/data/delete_many` -- Delete Many Documents
Same request schema as `delete_one`. Deletes all matching documents.

---

### `POST /api/v1/data/replace_one` -- Replace One Document
**Request body (`ReplaceOneRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| filter | object | yes | -- |
| replacement | object | yes | -- |
| options | object | no | -- |
| waitForFullWrite | bool | no | false |

**Response 200:** `UpdateResponse`

---

### `POST /api/v1/data/find` -- Find Documents (IMPORTANT)
The primary query endpoint. Runtime limited to 120 seconds.

**Request body (`FindRequest`):**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| collectionName | string | yes | -- | Target collection |
| query | object | yes | -- | MongoDB query filter (e.g. `{"status": "active"}`, `{"$and": [...]}`) |
| projection | object? | no | null | Fields to include/exclude (e.g. `{"name": 1, "_id": 0}`) |
| skip | int | no | 0 | Number of documents to skip |
| limit | int | no | 0 | Max documents to return (0 = no limit) |
| sort | object? | no | null | Sort order (e.g. `{"created_at": -1}`) |

**Response 200:** `QueryResultResponse` -- `result` is an array of document objects.

**Example request:**
```json
{
  "collectionName": "invoices",
  "query": {"vendor_id": "V123", "status": {"$in": ["pending", "approved"]}},
  "projection": {"_id": 1, "amount": 1, "date": 1},
  "sort": {"date": -1},
  "limit": 50
}
```

---

### `POST /api/v1/data/aggregate` -- Aggregate (IMPORTANT)
Runs a MongoDB aggregation pipeline. Runtime limited to 120 seconds.

**Request body (`AggregateRequest`):**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| collectionName | string? | no | null | Target collection (null for collection-less aggregations) |
| pipeline | object[] | yes | -- | Array of aggregation stages (e.g. `$match`, `$group`, `$lookup`, `$project`, `$sort`, `$unwind`, `$limit`) |
| collation | object? | no | null | Collation rules |
| let | object? | no | null | Variables for use in pipeline |
| options | object | no | -- | Additional options |

**Response 200:** `QueryResultResponse` -- `result` is an array of document objects.

**Example request:**
```json
{
  "collectionName": "invoices",
  "pipeline": [
    {"$match": {"status": "approved"}},
    {"$group": {"_id": "$vendor_id", "total": {"$sum": "$amount"}}},
    {"$sort": {"total": -1}}
  ]
}
```

---

### `POST /api/v1/data/aggregate_async` -- Aggregate Async
Same request as `aggregate` but runs asynchronously. Returns 202.

**Response 202:** `AcceptResponse` -- poll via `/api/v1/operation_status/{operation_id}`.

---

### `POST /api/v1/data/bulk_write` -- Bulk Write (ASYNC, IMPORTANT)
Performs multiple write operations atomically. Returns 202.

**Request body (`BulkWriteRequest`):**
| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| collectionName | string | yes | -- | Target collection |
| operations | array | yes | -- | Array of operation objects (see below) |
| waitForFullWrite | bool | no | false | Wait for full write acknowledgement |
| options | object | no | -- | Additional options |

**Operation types** (each is a single-key object):

| Operation | Key | Required Fields | Optional Fields |
|---|---|---|---|
| Insert one | `insertOne` | `document` | -- |
| Update one | `updateOne` | `filter`, `update` | `upsert` (default false), `arrayFilters`, `collation`, `hint` |
| Update many | `updateMany` | `filter`, `update` | `upsert`, `arrayFilters`, `collation`, `hint` |
| Delete one | `deleteOne` | `filter` | `collation`, `hint` |
| Delete many | `deleteMany` | `filter` | `collation`, `hint` |
| Replace one | `replaceOne` | `filter`, `replacement` | `upsert` (default false), `collation`, `hint` |

**Example request:**
```json
{
  "collectionName": "invoices",
  "operations": [
    {"insertOne": {"document": {"vendor": "A", "amount": 100}}},
    {"updateOne": {"filter": {"_id": "abc"}, "update": {"$set": {"status": "paid"}}}},
    {"deleteMany": {"filter": {"status": "cancelled"}}}
  ]
}
```

**Response 202:** `AcceptResponse` -- poll via operation status endpoint.

---

## Index Operations

All endpoints: `POST`, auth required.

### `POST /api/v1/indexes/list` -- List Indexes
**Request body (`ListIndexesRequest`):**
| Field | Type | Required | Default |
|---|---|---|---|
| collectionName | string | yes | -- |
| nameOnly | bool | no | true |

**Response 200:** `ListObjectsResponse`

---

### `POST /api/v1/indexes/create` -- Create Index (ASYNC)
**Request body (`CreateIndexRequest`):**
| Field | Type | Required | Description |
|---|---|---|---|
| collectionName | string | yes | Target collection |
| indexName | string | yes | Name for the index |
| keys | object | yes | Index key specification (e.g. `{"field": 1}`, `{"a": 1, "b": -1}`) |
| options | object | no | Additional index options |

**Response 202:** `AcceptResponse`

---

### `POST /api/v1/indexes/drop` -- Drop Index (ASYNC)
**Request body (`DropIndexRequest`):**
| Field | Type | Required |
|---|---|---|
| collectionName | string | yes |
| indexName | string | yes |

**Response 202:** `AcceptResponse`

---

## Search Index Operations (Atlas Search)

All endpoints: `POST`, auth required. For MongoDB Atlas full-text search indexes.

### `POST /api/v1/search_indexes/list` -- List Search Indexes
Same request as regular index list (`ListIndexesRequest`).

**Response 200:** `ListObjectsResponse`

---

### `POST /api/v1/search_indexes/create` -- Create Search Index (ASYNC)
**Request body (`CreateSearchIndexRequest`):**
| Field | Type | Required | Description |
|---|---|---|---|
| collectionName | string | yes | Target collection |
| indexName | string | yes | Index name |
| mappings | object | yes | Field mappings definition |
| analyzer | string? | no | Default analyzer |
| analyzers | object[]? | no | Custom analyzer definitions |
| searchAnalyzer | string? | no | Search-time analyzer |
| synonyms | object[]? | no | Synonym mapping definitions |

**Response 202:** `AcceptResponse`

---

### `POST /api/v1/search_indexes/drop` -- Drop Search Index (ASYNC)
Same request as regular index drop (`DropIndexRequest`).

**Response 202:** `AcceptResponse`

---

## Response Schemas Summary

| Schema | Fields |
|---|---|
| `SuccessResponse` | `code` ("ok"), `message`, `result.success` (true) |
| `AcceptResponse` | `code` ("accept"), `message` (contains operation_id for polling) |
| `ErrorResponse` | `code` ("error"), `message` |
| `InsertOneResponse` | `code`, `message`, `result.inserted_id` |
| `InsertManyResponse` | `code`, `message`, `result.inserted_ids` (array) |
| `UpdateResponse` | `code`, `message`, `result.matched_count`, `result.modified_count`, `result.upserted_id`, `result.raw_result` |
| `DeleteResponse` | `code`, `message`, `result.deleted_count`, `result.raw_result` |
| `QueryResultResponse` | `code`, `message`, `result` (array of document objects) |
| `ListObjectsResponse` | `code`, `message`, `result` (string[] or object[]) |
| `OperationStatusResponse` | `code`, `message`, `result` (Operation object) |

---

## MongoDB Query Pattern Quick Reference

These patterns apply to `filter`, `query`, and `pipeline` fields throughout the API.

**Comparison:** `$eq`, `$ne`, `$gt`, `$gte`, `$lt`, `$lte`, `$in`, `$nin`
**Logical:** `$and`, `$or`, `$not`, `$nor`
**Element:** `$exists`, `$type`
**Array:** `$elemMatch`, `$all`, `$size`
**Update operators:** `$set`, `$unset`, `$inc`, `$push`, `$pull`, `$addToSet`, `$rename`
**Aggregation stages:** `$match`, `$group`, `$project`, `$sort`, `$limit`, `$skip`, `$unwind`, `$lookup`, `$addFields`, `$replaceRoot`, `$out`, `$merge`
