# Batch Analysis CSV Export Design

## Scope

Add a batch-scoped CSV export without changing the existing upload CSV endpoint or database schema. Each row represents one uploaded image. Rejected upload items are also represented with status and error details, while analysis and review fields remain empty.

## Behavior

- Add `GET /api/upload-batches/<batch_id>/analysis.csv` for `ADMIN` and the doctor assigned to the case.
- Build the CSV from the current database state at download time.
- Select the newest analysis for each image, its newest analysis result, and its newest doctor review.
- Leave every doctor-review field empty when no review exists.
- Keep AI output explicitly separate from a doctor's clinical conclusion.
- Use stable UTF-8-with-BOM CSV headers suitable for spreadsheet applications.
- Neutralize spreadsheet formula prefixes in every exported text value.
- Do not expose internal filesystem paths, credentials, patient contact details, or other unnecessary sensitive data.

## Columns

Identification and upload: `batch_id`, `case_code`, `image_id`, `original_filename`, `image_status`, `image_error_message`, `uploaded_at`.

Analysis: `analysis_id`, `analysis_status`, `analysis_error_message`, `analysis_started_at`, `analysis_completed_at`, `model_name`, `inference_time_ms`, `ai_binary_result`, `ai_binary_probability`, `predicted_class`, `predicted_probability`, `probability_MEL`, `probability_NV`, `probability_BCC`, `probability_AK`, `probability_BKL`, `probability_DF`, `probability_VASC`, `probability_SCC`, `result_created_at`.

Measurements: `lesion_area_px`, `lesion_perimeter_px`, `lesion_ratio`, `bbox_x`, `bbox_y`, `bbox_width`, `bbox_height`.

Doctor review: `review_status`, `doctor_conclusion`, `clinical_note`, `recommendation`, `reviewer_name`, `review_updated_at`.

`ai_binary_result` uses `BENIGN` for `0`, `MALIGNANT` for `1`, and an empty value when no binary result exists.

## Interface

The analysis view gains an `Xuất CSV` action. It is enabled after a batch has been selected/uploaded and downloads the new endpoint for `currentBatchId`.

## Compatibility

The existing `GET /api/upload-batches/<batch_id>/csv` contract and stored upload-time CSV remain unchanged. No migration or dependency change is required.
