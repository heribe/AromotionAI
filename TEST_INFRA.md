# AromotionAI - E2E Testing Infrastructure & Plan (TEST_INFRA.md)

This document defines the End-to-End (E2E) testing framework, architecture, and the detailed 4-tier test plan for the AromotionAI backend.

---

## 1. Test Philosophy

The E2E testing strategy for AromotionAI is designed around reliability, independence, and requirement-driven validation.

### 1.1 Opaque-Box & Requirement-Driven Testing
- **API-Targeted**: All E2E tests target the public FastAPI REST endpoints and Server-Sent Events (SSE) progress streams.
- **Implementation Independence**: Tests are completely decoupled from internal designs (e.g., database schemas, ORM choices, class structures, or specific helper functions). They interact with the system solely as an external client (using HTTP requests and event streams).
- **Behavioral Assertions**: Assertions are based on business requirements, status transition correctness, contract compliance, and correctness of returned data models.

### 1.2 Verification Methodologies
- **Category-Partition Testing**: Input spaces (e.g., blogger URLs, analysis configurations, custom configurations) are partitioned into distinct equivalence classes to ensure logical coverage.
- **Boundary Value Analysis (BVA)**: Focuses on boundary conditions, such as extreme values in custom configuration fields, empty arrays, edge percentages in tag distributions, and expired states.
- **Pairwise Combinatorial Testing**: Systematically combines different independent variables (e.g., platform + analysis level + active AI model) to discover defects caused by feature interactions.
- **Real-World Workloads**: Simulates typical end-user journeys and administrator operations from start to finish.

### 1.3 Dual-Mode Execution Setup
To support both fast, deterministic CI pipelines and robust production verification, the suite supports two execution modes controlled via environment variables:

1. **Mock Mode (Default)**:
   - Enabled via: `AROMOTION_TEST_MODE=mock`
   - Intercepts external integration calls (e.g., Playwright/curl_cffi calls to Douyin APIs, external LLM provider chat completions).
   - Returns deterministic, mock data conforming strictly to schema contracts (e.g., predetermined blogger profiles, synthetic comment lists, and predefined JSON completions representing the Iceberg Model reasoning).
   - Used for normal unit, integration, and E2E test runs.

2. **Live Mode**:
   - Enabled via: `AROMOTION_TEST_MODE=live`
   - Bypasses mocks and sends actual requests to external social platforms and live AI providers.
   - Requires live cookies uploaded/configured (read from environment variables or local secret files, e.g., `LIVE_DOUYIN_COOKIE`) and valid AI API keys (e.g., `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`).
   - Used for scheduled regression testing, post-deployment smoke tests, and verification of external crawler bypass capabilities.

---

## 2. Feature Inventory

The backend functionality is organized into **7 core features (F1 to F7)** derived from the backend requirements:

| Feature | Name | Description / Scope | Primary Endpoints |
| :--- | :--- | :--- | :--- |
| **F1** | Cookie Management | Upload, status checking, validation, and deletion of platform cookies. | `POST /api/v1/cookies/upload`<br>`GET /api/v1/cookies/status`<br>`DELETE /api/v1/cookies/{platform}` |
| **F2** | Analysis Task Creation | Creating blogger analysis tasks; URL parsing, preset vs custom configuration. | `POST /api/v1/analysis/create` |
| **F3** | Task Progress Tracking | Querying detailed task status and subscribing to live progress updates via SSE. | `GET /api/v1/analysis/{task_id}`<br>`GET /api/v1/analysis/{task_id}/progress` |
| **F4** | Reports & Tags | Retrieving the structured four-dimension report and fetching aggregated tags. | `GET /api/v1/analysis/{task_id}/report`<br>`GET /api/v1/analysis/{task_id}/tags`<br>`DELETE /api/v1/analysis/{task_id}` |
| **F5** | Fragrance Recommendation | Generating iceberg analysis and multi-plan fragrance recommendations. | `POST /api/v1/fragrance/generate` |
| **F6** | Interactive Chat | Multi-turn chat for fragrance plan tuning with SSE streaming replies. | `POST /api/v1/fragrance/{session_id}/chat`<br>`POST /api/v1/fragrance/{session_id}/regenerate`<br>`GET /api/v1/fragrance/{session_id}`<br>`GET /api/v1/fragrance/{session_id}/history` |
| **F7** | System Config | Querying analysis preset configurations and managing AI model routing/keys. | `GET /api/v1/config/analysis-levels`<br>`GET /api/v1/config/ai-providers`<br>`PUT /api/v1/config/ai-providers/{provider_name}` |

---

## 3. Detailed 4-Tier Test Suite Specification

### 3.1 Tier 1: Feature Coverage (35 Test Cases)
This tier covers happy paths and standard operations. Each feature is covered by at least 5 test cases.

#### Feature F1: Cookie Management
1. **`test_f1_upload_valid_cookie`**
   - *Description*: Upload a valid JSON format cookie file for "douyin".
   - *Endpoint/Method*: `POST /api/v1/cookies/upload` (multipart/form-data)
   - *Expected Status*: `200 OK` or `201 Created`
   - *Assertions*: Response contains code `0`, platform `"douyin"`, and `is_valid: true`.
2. **`test_f1_get_status_empty`**
   - *Description*: Retrieve cookie status when no cookies have been uploaded yet.
   - *Endpoint/Method*: `GET /api/v1/cookies/status`
   - *Expected Status*: `200 OK`
   - *Assertions*: Response lists empty array or all platforms listed with `uploaded_at: null` and `is_valid: false`.
3. **`test_f1_get_status_after_upload`**
   - *Description*: Retrieve cookie status after uploading a cookie.
   - *Endpoint/Method*: `GET /api/v1/cookies/status`
   - *Expected Status*: `200 OK`
   - *Assertions*: Platform `"douyin"` contains valid upload metadata and `is_valid: true`.
4. **`test_f1_overwrite_cookie`**
   - *Description*: Upload a cookie for an existing platform to overwrite it.
   - *Endpoint/Method*: `POST /api/v1/cookies/upload`
   - *Expected Status*: `200 OK`
   - *Assertions*: Overwritten timestamp is updated and the record reflects the new upload.
5. **`test_f1_delete_cookie`**
   - *Description*: Delete an uploaded cookie.
   - *Endpoint/Method*: `DELETE /api/v1/cookies/douyin`
   - *Expected Status*: `200 OK` or `204 No Content`
   - *Assertions*: Subsequent status checks show the cookie is removed or marked inactive.

#### Feature F2: Analysis Task Creation
6. **`test_f2_create_task_standard`**
   - *Description*: Create a task using standard presets.
   - *Endpoint/Method*: `POST /api/v1/analysis/create`
   - *Payload*: `{"blogger_url": "https://www.douyin.com/user/MS4wLjABAAA...", "platform": "douyin", "analysis_level": "standard"}`
   - *Expected Status*: `200 OK` or `201 Created`
   - *Assertions*: Returns a valid `task_id` UUID and status is `"pending"`.
7. **`test_f2_create_task_custom`**
   - *Description*: Create a task with a fully populated `custom_config` payload.
   - *Endpoint/Method*: `POST /api/v1/analysis/create`
   - *Payload*: Containing valid config blocks for `post_selection`, `comment`, `commenter_analysis`, and `visual_analysis`.
   - *Expected Status*: `200 OK`
   - *Assertions*: Returns `task_id` and config matches the custom parameters in database mock/logs.
8. **`test_f2_create_task_deep_preset`**
   - *Description*: Create a task using the "deep" preset.
   - *Endpoint/Method*: `POST /api/v1/analysis/create`
   - *Payload*: `{"blogger_url": "https://www.douyin.com/user/...", "platform": "douyin", "analysis_level": "deep"}`
   - *Expected Status*: `200 OK`
   - *Assertions*: Task initialized with high-depth settings.
9. **`test_f2_parse_url_formats`**
   - *Description*: Verify that different valid Douyin URL formats are parsed successfully.
   - *Endpoint/Method*: `POST /api/v1/analysis/create`
   - *Expected Status*: `200 OK`
   - *Assertions*: Works for desktop links, share codes, and short URLs.
10. **`test_f2_platform_auto_detection`**
    - *Description*: Auto-detect platform from URL domain name when "platform" is omitted or set to auto.
    - *Endpoint/Method*: `POST /api/v1/analysis/create`
    - *Expected Status*: `200 OK`
    - *Assertions*: Tasks created with correct parsed platform value.

#### Feature F3: Task Progress Tracking
11. **`test_f3_get_task_details`**
    - *Description*: Retrieve basic task attributes and status.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Contains `blogger_url`, `status` (`pending`/`collecting`/`analyzing`/`completed`), and `progress` integer.
12. **`test_f3_subscribe_progress_stream`**
    - *Description*: Read from Server-Sent Events stream for task progress.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}/progress`
    - *Expected Status*: `200 OK` (with `text/event-stream` header)
    - *Assertions*: Stream emits valid event structures: `event: progress`, `event: step_complete`, and `event: complete`.
13. **`test_f3_progress_increments`**
    - *Description*: Verify that progress percentages strictly increment over time.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}/progress`
    - *Expected Status*: `200 OK`
    - *Assertions*: Emitted progress percentage goes from 0/5 to 100 without going backwards.
14. **`test_f3_list_tasks`**
    - *Description*: Query the history list of analysis tasks.
    - *Endpoint/Method*: `GET /api/v1/analysis/list?page=1&page_size=10`
    - *Expected Status*: `200 OK`
    - *Assertions*: Contains `total`, pagination metadata, and list items.
15. **`test_f3_cancel_task`**
    - *Description*: Cancel a running task.
    - *Endpoint/Method*: `POST /api/v1/analysis/{task_id}/cancel` (or mapped cancellation endpoint)
    - *Expected Status*: `200 OK`
    - *Assertions*: Task status transitions to `failed` or `cancelled`.

#### Feature F4: Reports & Tags
16. **`test_f4_get_profile_report`**
    - *Description*: Retrieve the completed four-dimension user profile report.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}/report`
    - *Expected Status*: `200 OK`
    - *Assertions*: Contains `blogger_info`, `report` with 4 dimensions (`climate_consumption`, `fragrance_consumption`, `fashion_fragrance_map`, `lifestyle_scenario`), and `full_report_markdown`.
17. **`test_f4_report_markdown_generation`**
    - *Description*: Verify that `full_report_markdown` is non-empty and formatted correctly.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}/report`
    - *Expected Status*: `200 OK`
    - *Assertions*: Markdown string starts with headers (`#` or `##`) and matches the content structure of the JSON dimensions.
18. **`test_f4_get_aggregated_tags`**
    - *Description*: Fetch the tags formatted for the tag selection workspace.
    - *Endpoint/Method*: `GET /api/v1/analysis/{task_id}/tags`
    - *Expected Status*: `200 OK`
    - *Assertions*: Response returns list of dimensions with `is_default_selected` and metadata properties.
19. **`test_f4_delete_completed_task`**
    - *Description*: Delete a task and clean up its database records and media files.
    - *Endpoint/Method*: `DELETE /api/v1/analysis/{task_id}`
    - *Expected Status*: `200 OK` or `204 No Content`
    - *Assertions*: Subsequent GET request for the task returns `404 Not Found`.
20. **`test_f4_verify_media_cleanup_on_delete`**
    - *Description*: Ensure that physical directories of media are wiped upon task deletion.
    - *Endpoint/Method*: `DELETE /api/v1/analysis/{task_id}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Invalidation of media file existence.

#### Feature F5: Fragrance Recommendation
21. **`test_f5_generate_fragrance`**
    - *Description*: Generate fragrance recommendation plans using selected tags.
    - *Endpoint/Method*: `POST /api/v1/fragrance/generate`
    - *Payload*: Contains `task_id`, `selected_tags` map, and `plan_count: 3`.
    - *Expected Status*: `200 OK`
    - *Assertions*: Returns a valid `session_id`, `status: "completed"`, and recommendations list.
22. **`test_f5_plan_count_validation`**
    - *Description*: Request 2 plans and verify the exact count returned.
    - *Endpoint/Method*: `POST /api/v1/fragrance/generate`
    - *Payload*: `{"task_id": "...", "selected_tags": {...}, "plan_count": 2}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Length of `recommendations` list in response is exactly 2.
23. **`test_f5_iceberg_structure_verification`**
    - *Description*: Verify the three layers of Iceberg analysis are present and fully generated.
    - *Endpoint/Method*: `POST /api/v1/fragrance/generate`
    - *Expected Status*: `200 OK`
    - *Assertions*: Contains `iceberg_analysis` with non-empty string properties `surface`, `middle`, and `deep`.
24. **`test_f5_notes_fields_verification`**
    - *Description*: Verify that fragrance notes have names, descriptions, and logical reasons mapping back to tags.
    - *Endpoint/Method*: `POST /api/v1/fragrance/generate`
    - *Expected Status*: `200 OK`
    - *Assertions*: Every note in `top_notes`, `middle_notes`, and `base_notes` has `name`, `description`, and `reason` populated.
25. **`test_f5_story_and_reason_generation`**
    - *Description*: Verify recommendation reasons and fragrance stories are returned.
    - *Endpoint/Method*: `POST /api/v1/fragrance/generate`
    - *Expected Status*: `200 OK`
    - *Assertions*: Both `recommendation_reason` and `fragrance_story` are long, non-trivial narrative texts.

#### Feature F6: Interactive Chat
26. **`test_f6_post_chat_message`**
    - *Description*: Send a standard feedback chat message to fine-tune recommendation plans.
    - *Endpoint/Method*: `POST /api/v1/fragrance/{session_id}/chat`
    - *Payload*: `{"message": "Make the base notes for plan 1 more woody."}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Returns assistant `reply` text and optionally updated plans.
27. **`test_f6_retrieve_chat_history`**
    - *Description*: Retrieve the list of conversation turns.
    - *Endpoint/Method*: `GET /api/v1/fragrance/{session_id}/history`
    - *Expected Status*: `200 OK`
    - *Assertions*: History list includes system-generated initial prompt turn, user message, and assistant reply.
28. **`test_f6_get_session_details`**
    - *Description*: Retrieve the latest fragrance session state.
    - *Endpoint/Method*: `GET /api/v1/fragrance/{session_id}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Returns session metadata, selected tags, and latest recommendations.
29. **`test_f6_chat_streaming_response`**
    - *Description*: Verify that chat reply can be streamed via SSE.
    - *Endpoint/Method*: `POST /api/v1/fragrance/{session_id}/chat` (with header `Accept: text/event-stream`)
    - *Expected Status*: `200 OK`
    - *Assertions*: Chunks contain text tokens and final JSON payload with updated plans.
30. **`test_f6_regenerate_session`**
    - *Description*: Wipe history and regenerate all recommendations with new tag choices.
    - *Endpoint/Method*: `POST /api/v1/fragrance/{session_id}/regenerate`
    - *Expected Status*: `200 OK`
    - *Assertions*: Chat history is cleared, new plans are saved, and initial recommendations match new inputs.

#### Feature F7: System Config
31. **`test_f7_get_presets`**
    - *Description*: Fetch the default configuration presets for standard, deep, and light analysis levels.
    - *Endpoint/Method*: `GET /api/v1/config/analysis-levels`
    - *Expected Status*: `200 OK`
    - *Assertions*: Response lists presets, and each preset defines post and comment extraction parameters.
32. **`test_f7_get_ai_providers`**
    - *Description*: Fetch registered AI providers and their status.
    - *Endpoint/Method*: `GET /api/v1/config/ai-providers`
    - *Expected Status*: `200 OK`
    - *Assertions*: Returns list of providers with status details and assigned tasks (e.g. `fragrance_chat`).
33. **`test_f7_update_ai_routing`**
    - *Description*: Change the active model provider for a reasoning task slot.
    - *Endpoint/Method*: `PUT /api/v1/config/ai-providers/openai`
    - *Payload*: `{"slot": "fragrance_reasoning", "model": "gpt-4o"}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Status verification reflects that the slot routing has been updated.
34. **`test_f7_get_sys_health`**
    - *Description*: Verify status page returns correct runtime telemetry.
    - *Endpoint/Method*: `GET /api/v1/config/status` (or health check endpoint)
    - *Expected Status*: `200 OK`
    - *Assertions*: Contains database status, storage availability, and current task queue size.
35. **`test_f7_modify_api_keys`**
    - *Description*: Safely update a provider's configuration.
    - *Endpoint/Method*: `PUT /api/v1/config/ai-providers/deepseek`
    - *Payload*: `{"api_key": "sk-newkey123...", "endpoint": "https://api.deepseek.com/v1"}`
    - *Expected Status*: `200 OK`
    - *Assertions*: Configuration is updated, subsequent tests use updated endpoint (in Live mode).

---

### 3.2 Tier 2: Boundary & Corner Cases (35 Test Cases)
Focuses on validation failures, error recovery, invalid inputs, nonexistent resources, and expired configurations.

#### Feature F1: Cookie Management
36. **`test_f1_upload_invalid_file_format`**
    - *Description*: Upload a `.txt` file or corrupt JSON for cookie.
    - *Endpoint/Method*: `POST /api/v1/cookies/upload`
    - *Expected Status*: `400 Bad Request` or `422 Unprocessable Entity`
    - *Assertions*: Error message contains invalid format indicator.
37. **`test_f1_upload_empty_file`**
    - *Description*: Upload an empty file.
    - *Endpoint/Method*: `POST /api/v1/cookies/upload`
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Rejects empty upload.
38. **`test_f1_query_nonexistent_platform`**
    - *Description*: Request cookie details for an unsupported platform.
    - *Endpoint/Method*: `GET /api/v1/cookies/status?platform=unknown`
    - *Expected Status*: `400 Bad Request` or `422 Unprocessable Entity`
    - *Assertions*: Rejects request with appropriate validation message.
39. **`test_f1_delete_missing_cookie`**
    - *Description*: Try to delete a cookie that was never uploaded.
    - *Endpoint/Method*: `DELETE /api/v1/cookies/xiaohongshu`
    - *Expected Status*: `404 Not Found` (or a successful `200` stating cookie does not exist to ensure idempotency)
    - *Assertions*: Handles the case gracefully without exceptions.
40. **`test_f1_expired_cookie_detection`**
    - *Description*: Trigger validation on an expired cookie structure.
    - *Endpoint/Method*: `POST /api/v1/cookies/validate/douyin`
    - *Expected Status*: `200 OK`
    - *Assertions*: Response reports `is_valid: false` and logs warning.

#### Feature F2: Analysis Task Creation
41. **`test_f2_create_task_invalid_blogger_url`**
    - *Description*: Submit a malformed URL.
    - *Payload*: `{"blogger_url": "not-a-url", "platform": "douyin", "analysis_level": "standard"}`
    - *Expected Status*: `400 Bad Request` or `422 Unprocessable Entity`
    - *Assertions*: Returns details identifying parsing errors.
42. **`test_f2_create_task_unsupported_platform`**
    - *Description*: Send a valid URL from an unsupported platform.
    - *Payload*: `{"blogger_url": "https://instagram.com/p/...", "platform": "instagram", "analysis_level": "standard"}`
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Reports platform not supported.
43. **`test_f2_create_task_missing_cookie`**
    - *Description*: Create analysis task when no cookie is uploaded for the target platform.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Returns error message indicating platform cookie is required.
44. **`test_f2_create_task_custom_missing_config`**
    - *Description*: Request `analysis_level: "custom"` but pass `custom_config: null`.
    - *Expected Status*: `400 Bad Request` or `422 Unprocessable Entity`
    - *Assertions*: Validation fails indicating custom configuration block is required.
45. **`test_f2_create_task_out_of_bounds_parameters`**
    - *Description*: Send custom configuration values outside limits (e.g. `top_count: 500` or negative values).
    - *Expected Status*: `422 Unprocessable Entity`
    - *Assertions*: Returns detailed errors pointing to validation constraints.

#### Feature F3: Task Progress Tracking
46. **`test_f3_get_nonexistent_task`**
    - *Description*: Request task details with invalid UUID.
    - *Endpoint/Method*: `GET /api/v1/analysis/00000000-0000-0000-0000-000000000000`
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Error message reports resource does not exist.
47. **`test_f3_progress_stream_nonexistent_task`**
    - *Description*: Subscribe to SSE progress for nonexistent task UUID.
    - *Endpoint/Method*: `GET /api/v1/analysis/00000000-0000-0000-0000-000000000000/progress`
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Terminated immediately with 404 response.
48. **`test_f3_double_cancellation`**
    - *Description*: Attempt to cancel a task that has already been cancelled.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Server returns error message stating task is already terminated.
49. **`test_f3_cancel_completed_task`**
    - *Description*: Attempt to cancel a task that has finished successfully.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Rejects cancellation on completed task.
50. **`test_f3_task_failure_propagation`**
    - *Description*: Simulate external API network failure during task run; check if it transitions to failed.
    - *Expected Status*: `200 OK` (initial creation)
    - *Assertions*: Progress stream emits `event: error` with details, status is marked `failed`.

#### Feature F4: Reports & Tags
51. **`test_f4_get_report_pending_task`**
    - *Description*: Query report for a task that is still in `"pending"` or `"collecting"` state.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Error states report is not generated yet.
52. **`test_f4_get_tags_failed_task`**
    - *Description*: Query tags for a task that status is `"failed"`.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Informs client that tags are unavailable for failed tasks.
53. **`test_f4_get_report_nonexistent_task`**
    - *Description*: Request report using random UUID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns not found message.
54. **`test_f4_get_tags_nonexistent_task`**
    - *Description*: Request tags using random UUID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns not found message.
55. **`test_f4_delete_task_mid_run`**
    - *Description*: Attempt to delete a task that is currently in status `"analyzing"`.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Task must be cancelled or completed before deleting; server prevents data corruption.

#### Feature F5: Fragrance Recommendation
56. **`test_f5_generate_nonexistent_task`**
    - *Description*: Request recommendations with a random `task_id` UUID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns appropriate missing resource error.
57. **`test_f5_generate_failed_task`**
    - *Description*: Request recommendations based on a failed task.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Rejects generation due to missing analysis profile.
58. **`test_f5_generate_empty_tags`**
    - *Description*: Send an empty `selected_tags` map.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Rejects generation since at least one tag is required.
59. **`test_f5_generate_invalid_tags_structure`**
    - *Description*: Send malformed tags dictionary (e.g. wrong key types).
    - *Expected Status*: `422 Unprocessable Entity`
    - *Assertions*: Fails schema validation.
60. **`test_f5_generate_invalid_plan_count`**
    - *Description*: Request `plan_count` of 0 or greater than 10.
    - *Expected Status*: `422 Unprocessable Entity`
    - *Assertions*: Triggers parameter range validation.

#### Feature F6: Interactive Chat
61. **`test_f6_chat_nonexistent_session`**
    - *Description*: Send message to nonexistent session ID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns missing session error.
62. **`test_f6_chat_empty_message`**
    - *Description*: Send empty string or white-spaces as message.
    - *Expected Status*: `400 Bad Request`
    - *Assertions*: Rejects empty prompt input.
63. **`test_f6_chat_malformed_json_reply`**
    - *Description*: AI returns bad JSON structure in mock simulation.
    - *Expected Status*: `502 Bad Gateway` or `200 OK` with error description.
    - *Assertions*: Handles parsing failure gracefully; returns error and preserves last state.
64. **`test_f6_get_nonexistent_session`**
    - *Description*: Retrieve session info using random UUID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns not found error.
65. **`test_f6_get_nonexistent_session_history`**
    - *Description*: Retrieve history with invalid session ID.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns not found error.

#### Feature F7: System Config
66. **`test_f7_update_nonexistent_provider`**
    - *Description*: Try to modify routing of a provider that is not registered.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Rejects update.
67. **`test_f7_update_config_invalid_fields`**
    - *Description*: Send invalid types in AI provider details.
    - *Expected Status*: `422 Unprocessable Entity`
    - *Assertions*: Fails schema validation.
68. **`test_f7_unauthorized_config_access`**
    - *Description*: Access config update without authentication header (if authentication required).
    - *Expected Status*: `401 Unauthorized` or `403 Forbidden`
    - *Assertions*: Rejects request.
69. **`test_f7_get_presets_unsupported_level`**
    - *Description*: Request details of non-existent preset.
    - *Expected Status*: `404 Not Found`
    - *Assertions*: Returns not found error.
70. **`test_f7_concurrent_routing_updates`**
    - *Description*: Send rapid overlapping config updates.
    - *Expected Status*: `200 OK`
    - *Assertions*: System resolves configuration locks without deadlocks or corruption.

---

### 3.3 Tier 3: Cross-Feature Combinations (7 Test Cases)
Validates interactions between different components and states.

1. **`test_t3_cookie_deletion_mid_task`**
   - *Scenario*: While an analysis task is executing (`status == "collecting"`), delete the active cookie for that platform via `DELETE /api/v1/cookies/{platform}`.
   - *Expected Behavior*: The task manager catches the cookie deletion event, terminates the collection worker, and updates the task status to `failed` with error message containing `CookieExpiredError` or cookie missing.
2. **`test_t3_task_deletion_impact_on_sse`**
   - *Scenario*: Establish an SSE connection subscribing to `/api/v1/analysis/{task_id}/progress`. While progress events are flowing, delete the task using `DELETE /api/v1/analysis/{task_id}`.
   - *Expected Behavior*: The backend cancels the active task coroutine, closes the SSE streaming connection immediately, and deletes all database records related to the task.
3. **`test_t3_tag_selection_to_recommendation_flow`**
   - *Scenario*: Create and wait for a task to complete. Retrieve the generated tags. Take a subset of those tags, modify them (add custom tag, toggle exclusivity), and send them to `POST /api/v1/fragrance/generate`.
   - *Expected Behavior*: The recommendation engine generates plans, returns a valid `session_id`, and correctly associates the new recommendation session with the original `task_id`.
4. **`test_t3_chat_history_updates_on_recalculations`**
   - *Scenario*: Create a fragrance session. Ask the assistant to make modifications (which updates recommendations). Then trigger a full regeneration using different tag configurations.
   - *Expected Behavior*: The GET history endpoint shows the original recommendations, the user's feedback turn, and the final state is updated with clean history reflecting the regenerated plans.
5. **`test_t3_ai_config_updates_modifying_model_targets`**
   - *Scenario*: Update the active AI provider routing for `fragrance_reasoning` from mock to live (or switch mock configurations). Immediately call `/api/v1/fragrance/generate`.
   - *Expected Behavior*: The system retrieves recommendations using the newly assigned provider config, verifying that configuration changes dynamically affect downstream reasoning engines without server restarts.
6. **`test_t3_task_cascade_deletion`**
   - *Scenario*: Create a full workspace: an analysis task, its report, tags, a fragrance session, and multiple chat messages. Perform `DELETE /api/v1/analysis/{task_id}`.
   - *Expected Behavior*: Cascade rules trigger. Querying report, tags, session, or chat history with respective IDs returns `404 Not Found`. All related media on the filesystem is deleted.
7. **`test_t3_multiple_concurrent_tasks_single_cookie`**
   - *Scenario*: Upload one cookie. Create three tasks concurrently for different blogger URLs on the same platform.
   - *Expected Behavior*: The backend queues or runs the tasks concurrently using the same cookie without lock contention, and all tasks complete or report progress accurately.

---

### 3.4 Tier 4: Real-World Scenarios (5 Workloads)
Simulates end-to-end multi-step flows representing complete production workflows.

#### Scenario 1: Complete Happy Path (End-to-End User Journey)
- **Step 1**: Upload a valid Douyin cookie. Check status to ensure it is active.
- **Step 2**: Submit a task for a Douyin blogger. Get `task_id`.
- **Step 3**: Open SSE connection. Read events until a `complete` event containing the report ID is received.
- **Step 4**: Fetch the profile report JSON and verify dimensions. Fetch tags for the UI workspace.
- **Step 5**: Select tags (accepting default selects and making 2 manual overrides) and submit to generate 3 fragrance plans.
- **Step 6**: Send feedback: "Make plan 1 more suitable for night wear". Verify response and verify plan 1 base notes update.
- **Step 7**: Fetch chat history and verify the sequence of messages.

#### Scenario 2: Cookie Lifecycle & Graceful Task Interruption
- **Step 1**: Upload cookie. Start an analysis task.
- **Step 2**: Simulate cookie expiration or overwrite it with an invalid cookie file mid-run.
- **Step 3**: The SSE stream reports a collection failure and task status changes to `failed` with diagnostic logs.
- **Step 4**: Upload a fresh, valid cookie.
- **Step 5**: Retry task creation for the same blogger.
- **Step 6**: The task completes successfully. Verify that reports and tags are generated.
- **Step 7**: Clean up by deleting the cookie and checking status returns invalid/inactive.

#### Scenario 3: Advanced Custom Task Configuration Tuning
- **Step 1**: Create a task with customized boundaries:
  - `top_count`: 10
  - `recent_count`: 5
  - `sort_by`: "comments"
  - `commenter_analysis.max_count`: 20
  - `video_frame_analysis`: true
  - `frames_per_video`: 3
- **Step 2**: Monitor task execution via SSE and verify steps.
- **Step 3**: Retrieve report and check that the analyzed posts list length is exactly 15 (10 top + 5 recent).
- **Step 4**: Ensure visual frame extraction logs show 3 frames analyzed per video.
- **Step 5**: Generate recommendation and verify the generated output reflects custom pricing/consumption variables.

#### Scenario 4: Multi-turn Fragrance Recipe Dialogue
- **Step 1**: Create recommendation session based on active tags.
- **Step 2**: **Turn 1**: Send message: "I want to change the top notes of plan 1 to include Grapefruit."
  - *Verification*: `updated_plans` contains plan 1 with "Grapefruit" in top notes, marked `changed: true`.
- **Step 3**: **Turn 2**: Send message: "Explain the emotional benefits of grapefruit."
  - *Verification*: Assistant replies with descriptive text explaining the emotional benefits. `updated_plans` is null (no changes to formulas).
- **Step 4**: **Turn 3**: Send message: "Add Cedarwood to base notes of plan 1 and increase plan count to 4." (Note: plan count change must be handled gracefully or rejected if session structure is locked, let's verify formulas update).
  - *Verification*: Base notes of plan 1 update with Cedarwood.
- **Step 5**: Fetch complete history and verify all message IDs, roles, and updated plans structures correspond to the turns.

#### Scenario 5: Admin Model Swapping & Integration
- **Step 1**: Query current active configurations for AI providers.
- **Step 2**: Change active provider for `analysis_task` to `deepseek` and `fragrance_reasoning` to `openai`.
- **Step 3**: Create an analysis task. In Mock Mode, verify that the task runner uses DeepSeek mock handlers (checked via mocked output tags or custom status logs).
- **Step 4**: Generate recommendations. In Mock Mode, verify OpenAI mock handler was invoked.
- **Step 5**: Change the provider configuration back to defaults (e.g. `glm`).
- **Step 6**: Run a final verification task to ensure routing has successfully reverted.

---

## 4. Test Architecture & Code Layout

### 4.1 Test Runner & Dependencies
The E2E test suite is executed using `pytest` inside the Python virtual environment managed by `uv`.

- **Framework**: `pytest`
- **Asynchronous support**: `pytest-asyncio` (for testing async endpoints and SSE streams)
- **HTTP Client**: `httpx` (for making non-blocking REST requests and streaming SSE)
- **SSE Parsing**: Custom chunk parser or `ssestream` library.

### 4.2 Test Directory Layout
All E2E tests are stored under the `backend/tests/e2e/` directory:

```text
backend/
└── tests/
    └── e2e/
        ├── conftest.py                   # Pytest fixtures (client, mock server configs, database helpers)
        ├── test_f1_cookies.py            # Coverage for Cookie Management APIs
        ├── test_f2_analysis_create.py    # Coverage for Task Creation and input validation
        ├── test_f3_progress.py           # Coverage for task progress & SSE events
        ├── test_f4_reports.py            # Coverage for profile reports and tag retrieval
        ├── test_f5_fragrance.py          # Coverage for fragrance plan generation
        ├── test_f6_chat.py               # Coverage for chat conversation adjustments
        ├── test_f7_config.py             # Coverage for system config and model routes
        ├── test_tier3_combinations.py    # Combinatorial tests
        ├── test_tier4_scenarios.py       # Real-world scenario workflows
        └── mock_data/                    # Static mock files for collector & LLM API responses
            ├── blogger_profile.json
            ├── comments_list.json
            ├── iceberg_analysis.json
            └── fragrance_recommendation.json
```

### 4.3 Git Worktree & Relative Path Discipline
To preserve monorepo worktree compatibility, E2E tests must never hardcode absolute paths or assume the name of the root directory.
Tests must dynamically resolve paths relative to the test files:

```python
from pathlib import Path

# Dynamically locate project root
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "backend" / "data"
```

### 4.4 Mock Interception Strategy
In `Mock Mode`, the tests configure standard mocks for the backend services. The `conftest.py` file registers:
- Mock `PlatformCollector` classes that bypass HTTP calls and load local files from `mock_data/`.
- Mock `BaseAIProvider` classes that intercept OpenAI/DeepSeek/GLM HTTP client calls and return structured mock text/JSON.

### 4.5 SSE Stream Testing Pattern
Testing Server-Sent Events requires reading the response iteratively. A helper function in `conftest.py` handles parsing:

```python
import httpx
import json

async def read_sse_stream(client: httpx.AsyncClient, url: str):
    events = []
    async with client.stream("GET", url) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        current_event = {}
        async for line in response.aiter_lines():
            line = line.strip()
            if not line:
                if current_event:
                    events.append(current_event)
                    current_event = {}
                continue
            if line.startswith("event:"):
                current_event["type"] = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_str = line[len("data:"):].strip()
                current_event["data"] = json.loads(data_str)
    return events
```
