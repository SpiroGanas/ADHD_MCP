# Intended Use Statement

**Version:** draft 0.1 (2026-11-26). Not reviewed by a clinician or by counsel.

## What the software is for

ADHD_MCP reads a patient's health record through FHIR and tells a licensed health care professional whether a referral for **formal adult ADHD screening** may be worth considering, together with the specific record entries that support the suggestion.

## What the software is not

- It does **not diagnose** ADHD or any other condition.
- It does **not** assess suicide risk. It surfaces existing self-harm signals from the record so the clinician can act on them first; it is not a substitute for a suicide risk evaluation.
- It does **not** write to the health record, place orders, or contact patients.
- It is **not** validated for clinical use. Its rules are a starting heuristic drawn from published literature.

## Intended users

Licensed health care professionals, directly or through an AI assistant they supervise. It is not intended for patients, family members or the public.

## Intended setting

Development, research and evaluation with synthetic data. Any use with real patient data requires the deploying organization's own clinical, privacy, security and regulatory review.

## How results must be presented

- The recommendation is always worded as a suggestion to consider referral for screening.
- The supporting evidence is always shown, so the professional can review the basis independently and need not rely on the recommendation.
- A positive safety gate is always presented before any ADHD recommendation.
- Missing or withheld data is always disclosed.

## Regulatory note

The design aims to stay within the criteria for clinical decision support software that is not a medical device: it is for professionals, it presents recommendations, and it shows its basis. This has not been confirmed by regulatory counsel. Patient-facing output, automated order placement, or scores whose basis a clinician cannot inspect would change that position and are out of scope.

## Standard notice

The following text, or an approved revision of it, accompanies every recommendation and is returned by `get_server_info`:

> This is a suggestion to consider referral for formal screening. It is not a diagnosis. Review the listed evidence and use clinical judgment.
